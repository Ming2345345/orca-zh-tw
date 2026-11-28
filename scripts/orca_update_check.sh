#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新、沒有還開著的同步 PR、也沒有補翻還在跑時才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；1 = 不需要；2 = 查不到必要資訊。1、2 都會略過這次排程，不花 agent 額度。
set -u
# precheck 的環境不一定載入使用者的 shell 設定，補上 orca、agy、gh、jq 的位置。
# 補在後面：已經在 PATH 裡的指令優先（測試靠這點換成假的 gh、orca）。
export PATH="$PATH:/Applications/Orca.app/Contents/Resources/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

REPO="${ORCA_ZH_TW_REPO:-$HOME/Desktop/orca-zh-tw}"
APP="${ORCA_APP:-/Applications/Orca.app}"
AUTOMATION_ID="${ORCA_ZH_TW_AUTOMATION_ID:-3f122394-4962-42b7-a928-5a1048a50ed9}"
# 補翻 run 狀態卡在執行中超過這麼久就當成異常，不再擋（Orca 沒把狀態改成結束時的保險）。
RUN_TIMEOUT_HOURS="${ORCA_ZH_TW_RUN_TIMEOUT_HOURS:-3}"
PICK_MODEL="${ORCA_ZH_TW_PICK_MODEL:-$(dirname "$0")/pick_agy_model.sh}"
# 自動化紀錄最多翻這麼多頁（每頁 100 筆，一頁約 0.3 秒），避免異常時無限翻頁。
MAX_RUN_PAGES=200
. "$(dirname "$0")/sync_lib.sh"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# 已安裝版本不比 origin/main 的語言包新就 exit 1（相同 = 已同步；較舊 = Orca 降版，不補翻）。
check_version() {
  synced=$(main_version "$REPO") || exit 2
  if [ "$installed" = "$synced" ]; then echo "已同步：Orca $installed"; exit 1; fi
  version_gt "$installed" "$synced" || { echo "Orca $installed 比語言包 $synced 舊，略過"; exit 1; }
}

[[ "$RUN_TIMEOUT_HOURS" =~ ^[0-9]+(\.[0-9]+)?$ && "$RUN_TIMEOUT_HOURS" =~ [1-9] ]] || {
  echo "ORCA_ZH_TW_RUN_TIMEOUT_HOURS 必須是正數：「${RUN_TIMEOUT_HOURS}」"; exit 2; }

installed=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null) || {
  echo "讀不到 Orca 版本：$APP"; exit 2; }
is_version "$installed" || { echo "Orca 版本格式不對：「${installed}」"; exit 2; }
check_version

# 任何版本的同步 PR 還開著就先等：新補翻以 main 為基準，會把那個 PR 的字串再翻一次。
# 看 PR 而不看分支：PR 關閉或合併後殘留的分支不該擋住補翻。gh 失敗時 exit 2，不能當成「沒有 PR」。
open_prs=$(open_sync_prs) || { echo "略過這次排程"; exit 2; }
if [ -n "$open_prs" ]; then
  echo "同步 PR 還開著：${open_prs}（Orca $installed 待合併或關閉後再補翻）"; exit 1
fi

# 補翻的 agent 可能還在跑（還沒開 PR），避免同時派出兩個 agent。手動 run 不跑 precheck，
# 所以可能同時有好幾個 run，要看全部紀錄裡仍在執行的，不能只看最新一筆，也不能依建立時間提早停止。
# 執行中的狀態：pending、dispatching、dispatched；其他（completed、dispatch_failed、skipped_*）都已結束。
# 這次 run 自己在 precheck 時是 dispatching，但還沒有 launchedAt／dispatchedAt，不會擋到自己。
# 每頁回應可能很大（含 agent 輸出），一律經 stdin 交給 jq，只留下狀態、時間、編號。
runs="$work/runs.tsv"
: >"$runs"
cursor=""
for ((page = 1; ; page++)); do
  ((page <= MAX_RUN_PAGES)) || { echo "自動化紀錄超過 $MAX_RUN_PAGES 頁，略過這次排程"; exit 2; }
  args=(automations runs --id "$AUTOMATION_ID" --limit 100 --json)
  [ -n "$cursor" ] && args+=(--cursor "$cursor")
  if ! orca "${args[@]}" >"$work/page.json" 2>"$work/err"; then
    # orca 失敗時錯誤訊息在 stdout 的 JSON（.error.message），stderr 可能是空的。
    msg=$(jq -r '.error.message // empty' <"$work/page.json" 2>/dev/null)
    echo "無法讀取自動化紀錄，略過這次排程：${msg:-$(cat "$work/err")}"; exit 2
  fi
  # 驗證：恰好一個 JSON 值、ok:true、runs 是陣列。第一行印下一頁的 cursor，之後每行一筆執行中的 run。
  jq -sr 'if length == 1 and .[0].ok == true and (.[0].result.runs | type) == "array"
              and ((.[0].result.nextCursor // "") | type) == "string"
          then .[0].result | (.nextCursor // ""),
               (.runs[] | select(.status == "pending" or .status == "dispatching" or .status == "dispatched")
                        | (.dispatchedAt // .launchedAt) as $at | select($at | type == "number")
                        | "\($at | floor)\t\(.runNumber)\t\(.status)")
          else error("回應不是單一的 ok:true JSON，或缺少 runs 陣列") end' \
    <"$work/page.json" >"$work/page.tsv" 2>"$work/err" || {
    echo "自動化紀錄的回應無效，略過這次排程：$(cat "$work/err")"; exit 2; }
  next=$(head -n 1 "$work/page.tsv")
  tail -n +2 "$work/page.tsv" >>"$runs"
  [ -z "$next" ] && break
  [ "$next" = "$cursor" ] && { echo "自動化紀錄的 cursor 沒有前進，略過這次排程"; exit 2; }
  cursor="$next"
done

now_ms=$(($(date +%s) * 1000))
cutoff_ms=$(awk -v now="$now_ms" -v h="$RUN_TIMEOUT_HOURS" 'BEGIN { printf "%.0f", now - h * 3600000 }')
fresh="" stale=""
while IFS=$'\t' read -r at number status; do
  if ((at >= cutoff_ms)); then
    age=$(awk -v now="$now_ms" -v at="$at" 'BEGIN { printf "%.1f", (now - at) / 3600000 }')
    fresh="${fresh:+${fresh}、}run ${number}（${status}，已 $age 小時）"
  else
    stale="${stale:+${stale}、}run $number"
  fi
done <"$runs"
[ -n "$stale" ] && echo "$stale 超過 $RUN_TIMEOUT_HOURS 小時仍未結束，視為異常，不再等待"
[ -n "$fresh" ] && { echo "補翻仍在執行：${fresh}，略過"; exit 1; }

# 查詢期間同步 PR 可能剛好合併，重讀一次遠端 main 再決定。
check_version
echo "需要更新：語言包 $synced → Orca $installed"

# 選 Gemini 模型：High 沒容量就改 Medium。
# Orca 在 precheck 之前就讀好自動化設定，這裡改 --model 只會影響之後的 run。
# 所以模型要換時：改設定、略過這次排程、立刻手動啟動一次（手動 run 不跑 precheck，不會無限循環）。
want=$("$PICK_MODEL") || { echo "選模型失敗，沿用目前設定"; exit 0; }
current=$(orca automations show "$AUTOMATION_ID" --json 2>/dev/null \
  | jq -r '.result.automation.launchSetup.extraAgentArgs // ""')
if [ "$current" = "--model $want" ]; then
  echo "模型：$want"
  exit 0
fi
if ! orca automations edit "$AUTOMATION_ID" --extra-agent-args="--model $want" --json >/dev/null 2>&1; then
  echo "無法把模型改成 ${want}，沿用目前設定（${current}）"
  exit 0
fi
# 背景延遲啟動，避免和這次 precheck 搶同一個自動化排程通道。
nohup sh -c "sleep 15; orca automations run '$AUTOMATION_ID' --json" >/dev/null 2>&1 &
echo "模型改為 ${want}，略過這次排程並改用手動 run 重新啟動"
exit 1
