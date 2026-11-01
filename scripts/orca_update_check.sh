#!/bin/bash
# Orca 自動化的 precheck：本機 Orca 版本比語言包新、沒有待審的補翻分支、最近也沒有補翻在跑時，才回傳 0。
# 回傳 0 = 需要更新（自動化會叫醒 agent）；其他 = 略過這次排程，不花 agent 額度。
set -u

REPO="${ORCA_ZH_TW_REPO:-$HOME/Desktop/orca-zh-tw}"
APP="${ORCA_APP:-/Applications/Orca.app}"
ORCA_CLI="${ORCA_CLI:-$APP/Contents/Resources/bin/orca}"
AUTOMATION_ID="${ORCA_ZH_TW_AUTOMATION_ID:-3f122394-4962-42b7-a928-5a1048a50ed9}"
# Orca 等一次補翻最多 6 小時，超過就當成失敗；在這段時間內不重複派工。
ACTIVE_RUN_HOURS="${ACTIVE_RUN_HOURS:-6}"

installed=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null) || {
  echo "讀不到 Orca 版本：$APP"; exit 2; }

git -C "$REPO" fetch -q --prune origin || { echo "無法 fetch origin"; exit 2; }
synced=$(git -C "$REPO" show origin/main:locales/orca-version.txt 2>/dev/null | tr -d '[:space:]')

if [ "$installed" = "$synced" ]; then
  echo "已同步：Orca $installed"; exit 1
fi

# 任何版本的補翻 PR 還沒合併時都先等：新補翻以 main 為基準，會把那個 PR 的字串再翻一次。
# 已合併進 main 但沒刪掉的分支不算。
pending=$(git -C "$REPO" for-each-ref --format='%(refname:lstrip=3)' 'refs/remotes/origin/auto/orca-v*' |
  while read -r branch; do
    git -C "$REPO" merge-base --is-ancestor "origin/$branch" origin/main || echo "$branch"
  done)
if [ -n "$pending" ]; then
  echo "等待審查：$(echo "$pending" | paste -sd ' ' -)（Orca $installed 待合併後再補翻）"; exit 1
fi

# 每小時檢查時，上一次補翻可能還在跑（還沒推分支），避免同時派出兩個 agent。
runs=$("$ORCA_CLI" automations runs --id "$AUTOMATION_ID" --json 2>/dev/null) || {
  echo "無法讀取自動化紀錄：$ORCA_CLI"; exit 2; }
recent=$(ACTIVE_RUN_HOURS="$ACTIVE_RUN_HOURS" python3 -c '
import json, os, sys, time
cutoff = (time.time() - float(os.environ["ACTIVE_RUN_HOURS"]) * 3600) * 1000
runs = json.load(sys.stdin)["result"]["runs"]
print(next((r["runNumber"] for r in runs if (r.get("dispatchedAt") or 0) > cutoff), ""))
' <<<"$runs") || { echo "無法解析自動化紀錄"; exit 2; }
if [ -n "$recent" ]; then
  echo "run $recent 在 ${ACTIVE_RUN_HOURS} 小時內已派工，略過"; exit 1
fi

echo "需要更新：語言包 $synced → Orca $installed"
exit 0
