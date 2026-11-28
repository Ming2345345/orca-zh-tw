#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新、沒有還開著的同步 PR、上一次補翻也已結束時才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；其他 = 略過這次排程，不花 agent 額度。
set -u
# precheck 的環境不一定載入使用者的 shell 設定，補上 orca、agy、gh、jq 的位置。
# 補在後面：已經在 PATH 裡的指令優先（測試靠這點換成假的 gh、orca）。
export PATH="$PATH:/Applications/Orca.app/Contents/Resources/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

REPO="${ORCA_ZH_TW_REPO:-$HOME/Desktop/orca-zh-tw}"
APP="${ORCA_APP:-/Applications/Orca.app}"
GH_REPO="${ORCA_ZH_TW_GH_REPO:-Ming2345345/orca-zh-tw}"
AUTOMATION_ID="${ORCA_ZH_TW_AUTOMATION_ID:-3f122394-4962-42b7-a928-5a1048a50ed9}"
# 上一次 run 狀態卡在執行中超過這麼久就當成異常，不再擋（Orca 沒把狀態改成結束時的保險）。
RUN_TIMEOUT_HOURS="${ORCA_ZH_TW_RUN_TIMEOUT_HOURS:-3}"
PICK_MODEL="${ORCA_ZH_TW_PICK_MODEL:-$(dirname "$0")/pick_agy_model.sh}"
# gh、orca 的錯誤訊息另外收，不和 stdout 混在一起（例如 gh 的版本更新提示會印到 stderr）。
err_file=$(mktemp)
trap 'rm -f "$err_file"' EXIT

installed=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null) || {
  echo "讀不到 Orca 版本：$APP"; exit 2; }

git -C "$REPO" fetch -q origin || { echo "無法 fetch origin"; exit 2; }
synced=$(git -C "$REPO" show origin/main:locales/orca-version.txt 2>/dev/null | tr -d '[:space:]')

if [ "$installed" = "$synced" ]; then
  echo "已同步：Orca $installed"; exit 1
fi

# 任何版本的同步 PR 還開著就先等：新補翻以 main 為基準，會把那個 PR 的字串再翻一次。
# 看 PR 而不看分支：PR 關閉或合併後殘留的分支不該擋住補翻。
# gh 失敗時不能當成「沒有 PR」，否則會重複派工。
open_prs=$(gh pr list -R "$GH_REPO" --state open --search 'head:auto/orca-v' \
  --json number,headRefName \
  --jq '[.[] | select(.headRefName | startswith("auto/orca-v")) | "#\(.number) \(.headRefName)"] | join("、")' 2>"$err_file") || {
  echo "無法查詢 $GH_REPO 的 PR，略過這次排程：$(cat "$err_file")"; exit 2; }
if [ -n "$open_prs" ]; then
  echo "同步 PR 還開著：$open_prs（Orca $installed 待合併或關閉後再補翻）"; exit 1
fi

# 上一次補翻的 agent 可能還在跑（還沒開 PR），避免同時派出兩個 agent。
# 這次 run 自己在 precheck 時還沒有 dispatchedAt，所以只看派過工的 run 裡最新的一個。
# 執行中的狀態：pending、dispatching、dispatched；其他（completed、dispatch_failed、skipped_*）都已結束。
runs=$(orca automations runs --id "$AUTOMATION_ID" --limit 20 --json 2>"$err_file") || {
  echo "無法讀取自動化紀錄，略過這次排程：$(cat "$err_file")"; exit 2; }
active=$(jq -r --argjson now "$(date +%s)" --argjson hours "$RUN_TIMEOUT_HOURS" '
  [.result.runs[] | select(.dispatchedAt != null)] | max_by(.dispatchedAt) // empty
  | select(.status == "pending" or .status == "dispatching" or .status == "dispatched")
  | (($now * 1000 - .dispatchedAt) / 3600000) as $age
  | if $age < $hours then "run \(.runNumber) 仍在執行（\(.status)，已 \($age * 10 | floor / 10) 小時）"
    else "stale" end' <<<"$runs") || {
  echo "無法解析自動化紀錄，略過這次排程"; exit 2; }
if [ "$active" = "stale" ]; then
  echo "上一次 run 超過 $RUN_TIMEOUT_HOURS 小時仍未結束，視為異常，不再等待"
elif [ -n "$active" ]; then
  echo "$active，略過"; exit 1
fi
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
