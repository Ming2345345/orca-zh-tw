# 補翻流程共用的函式：orca_update_check.sh、prepare_update.sh、publish_guard.sh 以 source 載入。
# 同步 PR 的定義：GH_REPO 裡、同一個 repo 的 auto/orca-v* 分支、base 是 main、還開著。

GH_REPO="${ORCA_ZH_TW_GH_REPO:-Ming2345345/orca-zh-tw}"
# 開著的 PR 最多列這麼多筆；列滿代表可能漏查，當成查詢失敗。
PR_LIMIT=500

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

# main_version <repo 路徑>：fetch 後印出 origin/main 的語言包版本；失敗時把原因印到 stderr 並回傳非 0。
main_version() {
  local raw v
  git -C "$1" fetch -q origin || { echo "無法 fetch origin" >&2; return 1; }
  raw=$(git -C "$1" show origin/main:locales/orca-version.txt 2>/dev/null) || {
    echo "讀不到 origin/main 的 locales/orca-version.txt" >&2; return 1; }
  v=$(printf '%s' "$raw" | tr -d '[:space:]')
  is_version "$v" || { echo "語言包版本格式不對：「${v}」" >&2; return 1; }
  echo "$v"
}

# open_sync_prs：印出開著的同步 PR（「#編號 分支」以「、」分隔，沒有就印空字串）。
# gh 失敗或回應無效時把原因印到 stderr 並回傳非 0，呼叫端不能把失敗當成「沒有 PR」。
# 不用 --search：GitHub 搜尋有筆數上限，事後篩選補不回漏掉的 PR。
open_sync_prs() {
  local err prs
  err=$(mktemp)
  prs=$(gh pr list -R "$GH_REPO" --state open --base main --limit "$PR_LIMIT" \
    --json number,headRefName,baseRefName,isCrossRepository 2>"$err") || {
    echo "無法查詢 $GH_REPO 的 PR：$(cat "$err")" >&2; rm -f "$err"; return 1; }
  rm -f "$err"
  jq -er --argjson limit "$PR_LIMIT" '
    if type != "array" then error("gh 回應不是陣列")
    elif length >= $limit then error("開著的 PR 達到 \($limit) 筆，可能漏查")
    else [.[] | select(.isCrossRepository == false and .baseRefName == "main"
                       and (.headRefName | startswith("auto/orca-v")))
          | "#\(.number) \(.headRefName)"] | join("、") end' <<<"$prs" || {
    echo "無法解析 $GH_REPO 的 PR 清單" >&2; return 1; }
}
