#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新，而且還沒有對應的待審分支時才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；其他 = 略過這次排程，不花 agent 額度。
set -u

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
exit 0
