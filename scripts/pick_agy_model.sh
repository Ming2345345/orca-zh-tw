#!/bin/bash
# 決定這次自動化用哪個 Gemini 模型：先對 High 送一個很小的請求，
# 成功就印出 High 的 ID；沒容量（503）、逾時或其他失敗就印出 Medium 的 ID。
# 只把模型 ID 印到 stdout，說明訊息印到 stderr。
set -u

HIGH="gemini-3.8-flash-high"
MEDIUM="gemini-3.8-flash-medium"
PROBE_TIMEOUT="${ORCA_ZH_TW_PROBE_TIMEOUT:-45s}"

probe_dir=$(mktemp -d)
trap 'rm -rf "$probe_dir"' EXIT

result=$(cd "$probe_dir" && agy --model "$HIGH" -p "只回覆 OK" \
  --print-timeout "$PROBE_TIMEOUT" --output-format json 2>/dev/null)

if printf '%s' "$result" | grep -q '"status":"SUCCESS"'; then
  echo "Gemini High 可用" >&2
  echo "$HIGH"
else
  echo "Gemini High 沒容量或無回應，改用 Medium" >&2
  echo "$MEDIUM"
fi
