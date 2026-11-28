#!/bin/bash
# 發布前最後檢查：push 同步分支、開 PR 之前執行，用法 ./scripts/publish_guard.sh <版本>。
# 回傳 0 = 可以發布；3 = 已經有人發布（origin/main 已是這個版本或更新，或已有開著的同步 PR），不要發布；
# 2 = 查不到必要資訊，不要發布。
set -u
. "$(dirname "$0")/sync_lib.sh"
version="${1:?用法：publish_guard.sh <版本>}"
is_version "$version" || { echo "版本格式不對：「${version}」"; exit 2; }

synced=$(main_version .) || exit 2
if ! version_gt "$version" "$synced"; then
  echo "origin/main 已經是 Orca ${synced}，不需要再發布 $version"; exit 3
fi
prs=$(open_sync_prs) || exit 2
if [ -n "$prs" ]; then
  echo "已經有開著的同步 PR：${prs}，不再發布"; exit 3
fi
echo "可以發布 Orca $version"
