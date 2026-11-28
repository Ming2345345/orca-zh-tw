#!/bin/bash
# 準備一次語言包更新：Orca 原始碼切到本機安裝的版本，建立同步分支，產生待翻譯批次。
# 在 orca-zh-tw 的工作目錄（或 worktree）根目錄執行。可用第一個參數指定版本。
# 分支名稱 auto/orca-v<版本>-<時間>-<隨機碼> 每次都不同：同版本的 PR 被關掉後重試時，
# 不會撞到舊 worktree 佔用的分支，也不會被舊的遠端分支擋住 push。
# origin/main 已經是這個版本或更新時以結束碼 3 結束，不動 Orca 原始碼、不建分支。
set -euo pipefail

ORCA_SRC="${ORCA_SRC:-$HOME/Desktop/orca}"
APP="${ORCA_APP:-/Applications/Orca.app}"
. "$(dirname "$0")/sync_lib.sh"
version="${1:-$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString)}"
is_version "$version" || { echo "版本格式不對：「${version}」" >&2; exit 2; }
tag="v$version"

synced=$(main_version .) || exit 2
if ! version_gt "$version" "$synced"; then
  echo "origin/main 已經是 Orca ${synced}（不比 $version 舊），不需要更新"
  exit 3
fi

git -C "$ORCA_SRC" fetch -q --tags origin
git -C "$ORCA_SRC" -c advice.detachedHead=false checkout -q "$tag"

EN="$ORCA_SRC/src/renderer/src/i18n/locales/en.json"
CHROME="$ORCA_SRC/src/shared/plugins/languages/plugin-translatable-chrome.ts"
if [ ! -f "$CHROME" ]; then
  CHROME="$ORCA_SRC/src/shared/plugins/plugin-translatable-chrome.ts"
fi

branch="auto/orca-$tag-$(date +%Y%m%d-%H%M%S)-$(printf '%04x%04x' $RANDOM $RANDOM)"
# 用 -b 而不是 -B：萬一撞名就失敗，不要覆寫既有分支。
git checkout -q -b "$branch" origin/main
mkdir -p pending
rm -f pending/batch-*.json pending/batch-*.report.md

python3 scripts/sync_catalog.py diff --en "$EN" --chrome "$CHROME" \
  --out pending/batch.json --batch-size 120 --label "Orca $tag"
# 沒有字串時 diff 仍會寫出一個空批次，刪掉以免 agent 誤以為有工作。
python3 - <<'PY'
import json, pathlib
for path in pathlib.Path("pending").glob("batch-*.json"):
    if not json.loads(path.read_text())["entries"]:
        path.unlink()
PY

cat > pending/update.env <<EOF
VERSION=$version
BRANCH=$branch
EN=$EN
CHROME=$CHROME
EOF
echo "分支：$branch"
ls pending/batch-*.json 2>/dev/null | sed 's/^/批次：/' || echo "沒有需要翻譯的字串"
