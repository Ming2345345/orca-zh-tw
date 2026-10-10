#!/bin/bash
# 準備一次語言包更新：Orca 原始碼切到本機安裝的版本，建立 auto/orca-v<版本> 分支，產生待翻譯批次。
# 在 orca-zh-tw 的工作目錄（或 worktree）根目錄執行。可用第一個參數指定版本。
set -euo pipefail

ORCA_SRC="${ORCA_SRC:-$HOME/Desktop/orca}"
APP="${ORCA_APP:-/Applications/Orca.app}"
version="${1:-$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString)}"
tag="v$version"

git -C "$ORCA_SRC" fetch -q --tags origin
git -C "$ORCA_SRC" -c advice.detachedHead=false checkout -q "$tag"

EN="$ORCA_SRC/src/renderer/src/i18n/locales/en.json"
CHROME="$ORCA_SRC/src/shared/plugins/plugin-translatable-chrome.ts"

git fetch -q origin
git checkout -q -B "auto/orca-$tag" origin/main
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
EN=$EN
CHROME=$CHROME
EOF
echo "分支：auto/orca-$tag"
ls pending/batch-*.json 2>/dev/null | sed 's/^/批次：/' || echo "沒有需要翻譯的字串"
