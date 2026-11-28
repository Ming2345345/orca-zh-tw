#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新、沒有還開著的同步 PR、也沒有補翻還在跑時才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；1 = 不需要；2 = 查不到必要資訊。1、2 都會略過這次排程，不花 agent 額度。
set -u
# precheck 的環境不一定載入使用者的 shell 設定，補上 orca、agy、gh、jq 的位置。
# 補在後面：已經在 PATH 裡的指令優先（測試靠這點換成假的 gh、orca）。
export PATH="$PATH:/Applications/Orca.app/Contents/Resources/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

REPO="${ORCA_ZH_TW_REPO:-$HOME/Desktop/orca-zh-tw}"
APP="${ORCA_APP:-/Applications/Orca.app}"
GH_REPO="${ORCA_ZH_TW_GH_REPO:-Ming2345345/orca-zh-tw}"
AUTOMATION_ID="${ORCA_ZH_TW_AUTOMATION_ID:-3f122394-4962-42b7-a928-5a1048a50ed9}"
# 補翻 run 狀態卡在執行中超過這麼久就當成異常，不再擋（Orca 沒把狀態改成結束時的保險）。
RUN_TIMEOUT_HOURS="${ORCA_ZH_TW_RUN_TIMEOUT_HOURS:-3}"
PICK_MODEL="${ORCA_ZH_TW_PICK_MODEL:-$(dirname "$0")/pick_agy_model.sh}"
# 開著的 PR 最多列這麼多筆；列滿代表可能漏查，當成查詢失敗。
PR_LIMIT=500
# 自動化紀錄最多翻這麼多頁（每頁 100 筆），避免異常時無限翻頁。
MAX_RUN_PAGES=20

# gh、orca 的錯誤訊息另外收，不和 stdout 混在一起（例如 gh 的版本更新提示會印到 stderr）。
err_file=$(mktemp)
trap 'rm -f "$err_file"' EXIT

is_version() { [[ "$1" =~ ^[0-9]+(\.[0-9]+)*$ ]]; }
# version_gt A B：A 比 B 新時回傳 0。逐段比數字，缺的段當 0。
version_gt() {
  local IFS=. i a b
  local -a x=($1) y=($2)
  for ((i = 0; i < ${#x[@]} || i < ${#y[@]}; i++)); do
    a=$((10#${x[i]:-0})) b=$((10#${y[i]:-0}))
    ((a > b)) && return 0
    ((a < b)) && return 1
  done
  return 1
}
# 讀遠端 main 的語言包版本；讀不到或格式不對就 exit 2。
read_synced() {
  git -C "$REPO" fetch -q origin || { echo "無法 fetch origin"; exit 2; }
  local raw
  raw=$(git -C "$REPO" show origin/main:locales/orca-version.txt 2>/dev/null) || {
    echo "讀不到 origin/main 的 locales/orca-version.txt"; exit 2; }
  synced=$(printf '%s' "$raw" | tr -d '[:space:]')
  is_version "$synced" || { echo "語言包版本格式不對：「$synced」"; exit 2; }
}
# 已安裝版本不比語言包新就 exit 1（相同 = 已同步；較舊 = Orca 降版，不補翻）。
require_newer() {
  if [ "$installed" = "$synced" ]; then echo "已同步：Orca $installed"; exit 1; fi
  if ! version_gt "$installed" "$synced"; then
    echo "Orca $installed 比語言包 $synced 舊，略過"; exit 1
  fi
}

[[ "$RUN_TIMEOUT_HOURS" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "$RUN_TIMEOUT_HOURS" =~ [1-9] ]] || {
  echo "ORCA_ZH_TW_RUN_TIMEOUT_HOURS 必須是正數：「$RUN_TIMEOUT_HOURS」"; exit 2; }

installed=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null) || {
  echo "讀不到 Orca 版本：$APP"; exit 2; }
is_version "$installed" || { echo "Orca 版本格式不對：「$installed」"; exit 2; }

read_synced
require_newer

# 任何版本的同步 PR 還開著就先等：新補翻以 main 為基準，會把那個 PR 的字串再翻一次。
# 看 PR 而不看分支：PR 關閉或合併後殘留的分支不該擋住補翻。
# 同步 PR 的定義和發布步驟一致：同一個 repo 的 auto/orca-v* 分支，base 是 main。
# 不用 --search：搜尋有筆數上限，後置篩選補不回漏掉的 PR。
# gh 失敗時不能當成「沒有 PR」，否則會重複派工。
prs=$(gh pr list -R "$GH_REPO" --state open --base main --limit "$PR_LIMIT" \
  --json number,headRefName,baseRefName,isCrossRepository 2>"$err_file") || {
  echo "無法查詢 $GH_REPO 的 PR，略過這次排程：$(cat "$err_file")"; exit 2; }
open_prs=$(jq -er --argjson limit "$PR_LIMIT" '
  if type != "array" then error("gh 回應不是陣列")
  elif length >= $limit then error("開著的 PR 達到 \($limit) 筆，可能漏查")
  else [.[] | select(.isCrossRepository == false and .baseRefName == "main"
                     and (.headRefName | startswith("auto/orca-v")))
        | "#\(.number) \(.headRefName)"] | join("、") end' <<<"$prs" 2>"$err_file") || {
  echo "無法解析 $GH_REPO 的 PR 清單，略過這次排程：$(cat "$err_file")"; exit 2; }
if [ -n "$open_prs" ]; then
  echo "同步 PR 還開著：$open_prs（Orca $installed 待合併或關閉後再補翻）"; exit 1
fi

# 補翻的 agent 可能還在跑（還沒開 PR），避免同時派出兩個 agent。手動 run 不跑 precheck，
# 所以可能同時有好幾個 run，要看全部仍在執行的，不能只看最新一筆。
# 執行中的狀態：pending、dispatching、dispatched；其他（completed、dispatch_failed、skipped_*）都已結束。
# 這次 run 自己在 precheck 時是 dispatching，但還沒有 launchedAt／dispatchedAt，不會擋到自己。
# 紀錄由新到舊（依 createdAt）分頁，翻到比逾時門檻再早一小時的就停。
now_ms=$(($(date +%s) * 1000))
cutoff_ms=$(jq -n --argjson now "$now_ms" --argjson h "$RUN_TIMEOUT_HOURS" '$now - $h * 3600000 | floor')
all_runs='[]'
cursor=""
for ((page = 1; ; page++)); do
  if ((page > MAX_RUN_PAGES)); then
    echo "自動化紀錄超過 $MAX_RUN_PAGES 頁仍未翻完，略過這次排程"; exit 2
  fi
  args=(automations runs --id "$AUTOMATION_ID" --limit 100 --json)
  [ -n "$cursor" ] && args+=(--cursor "$cursor")
  # orca 失敗時錯誤訊息在 stdout 的 JSON（.error.message），stderr 可能是空的。
  if ! resp=$(orca "${args[@]}" 2>"$err_file"); then
    msg=$(jq -r '.error.message // empty' <<<"$resp" 2>/dev/null)
    echo "無法讀取自動化紀錄，略過這次排程：${msg:-$(cat "$err_file")}"; exit 2
  fi
  page_info=$(jq -ec '
    if .ok == true and (.result.runs | type) == "array"
       and ((.result.nextCursor // "") | type) == "string"
    then {runs: .result.runs, next: (.result.nextCursor // ""),
          oldest: ([.result.runs[].createdAt | numbers] | min)}
    else error("回應不是 ok:true 或缺少 runs 陣列") end' <<<"$resp" 2>"$err_file") || {
    echo "自動化紀錄的回應無效，略過這次排程：$(cat "$err_file")"; exit 2; }
  all_runs=$(jq -c --argjson page "$page_info" '. + $page.runs' <<<"$all_runs")
  cursor=$(jq -r '.next' <<<"$page_info")
  oldest=$(jq -r '.oldest // empty' <<<"$page_info")
  [ -z "$cursor" ] && break
  [ -n "$oldest" ] && ((oldest < cutoff_ms - 3600000)) && break
done

active=$(jq -r --argjson now "$now_ms" --argjson cutoff "$cutoff_ms" '
  [.[] | select(.status == "pending" or .status == "dispatching" or .status == "dispatched")
       | (.dispatchedAt // .launchedAt) as $at | select($at != null)
       | {n: .runNumber, s: .status, at: $at}]
  | {fresh: [.[] | select(.at >= $cutoff)], stale: [.[] | select(.at < $cutoff)]}
  | (.fresh | sort_by(-.at)
       | map("run \(.n)（\(.s)，已 \((($now - .at) / 360000 | floor) / 10) 小時）") | join("、")),
    (.stale | map("run \(.n)") | join("、"))' <<<"$all_runs") || {
  echo "無法解析自動化紀錄，略過這次排程"; exit 2; }
fresh=$(sed -n 1p <<<"$active")
stale=$(sed -n 2p <<<"$active")
if [ -n "$stale" ]; then
  echo "$stale 超過 $RUN_TIMEOUT_HOURS 小時仍未結束，視為異常，不再等待"
fi
if [ -n "$fresh" ]; then
  echo "補翻仍在執行：$fresh，略過"; exit 1
fi

# 查詢期間同步 PR 可能剛好合併，重讀一次遠端 main 再決定。
read_synced
require_newer
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
  echo "無法把模型改成 $want，沿用目前設定（$current）"
  exit 0
fi
# 背景延遲啟動，避免和這次 precheck 搶同一個自動化排程通道。
nohup sh -c "sleep 15; orca automations run '$AUTOMATION_ID' --json" >/dev/null 2>&1 &
echo "模型改為 $want，略過這次排程並改用手動 run 重新啟動"
exit 1
