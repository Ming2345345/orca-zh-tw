#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新，而且還沒有對應的待審分支時才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；其他 = 略過這次排程，不花 agent 額度。
set -u
# precheck 的環境不一定載入使用者的 shell 設定，補上 orca、agy、jq 的位置。
export PATH="/Applications/Orca.app/Contents/Resources/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO="${ORCA_ZH_TW_REPO:-$HOME/Desktop/orca-zh-tw}"
APP="${ORCA_APP:-/Applications/Orca.app}"

installed=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null) || {
  echo "讀不到 Orca 版本：$APP"; exit 2; }

git -C "$REPO" fetch -q origin || { echo "無法 fetch origin"; exit 2; }
synced=$(git -C "$REPO" show origin/main:locales/orca-version.txt 2>/dev/null | tr -d '[:space:]')

if [ "$installed" = "$synced" ]; then
  echo "已同步：Orca $installed"; exit 1
fi
if git -C "$REPO" ls-remote --exit-code --heads origin "auto/orca-v$installed" >/dev/null 2>&1; then
  echo "auto/orca-v$installed 已在等待審查，略過"; exit 1
fi
echo "需要更新：語言包 $synced → Orca $installed"

# 選 Gemini 模型：High 沒容量就改 Medium。
# Orca 在 precheck 之前就讀好自動化設定，這裡改 --model 只會影響之後的 run。
# 所以模型要換時：改設定、略過這次排程、立刻手動啟動一次（手動 run 不跑 precheck，不會無限循環）。
AUTOMATION_ID="${ORCA_ZH_TW_AUTOMATION_ID:-3f122394-4962-42b7-a928-5a1048a50ed9}"
want=$("$(dirname "$0")/pick_agy_model.sh") || { echo "選模型失敗，沿用目前設定"; exit 0; }
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
