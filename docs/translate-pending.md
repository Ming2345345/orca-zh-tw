# 翻譯待處理批次

以下指令都在專案根目錄執行。先指定同一版本的英文目錄及分派給你的批次檔案；將 `pending/batch-001.json` 換成實際路徑：

```bash
EN='/Users/ming/Desktop/orca/src/renderer/src/i18n/locales/en.json'
BATCH='pending/batch-001.json'
cat docs/zh-TW-glossary.md
```

1. **先讀術語表。** 以 `docs/zh-TW-glossary.md` 為準，確認保留英文的詞、中文譯法、大小寫例外及格式規則。
2. 開啟批次，逐條閱讀 `entries` 的 `en`、`status` 及既有譯文。只填寫或修改 `zh`，不得改動 `key`、`en`、`status`、`previous_en`、`previous_zh`、`en_source` 或條目順序。
3. `new` 條目依 `en` 翻譯；`changed` 條目先從 `previous_zh` 出發，對照 `previous_en` 與目前 `en` 的差異，再調整成符合新英文的譯文。不要直接沿用已不符合原文的舊譯。
4. 保留目前 `en` 中所有插值與佔位符（例如 `{{name}}`）、HTML 標籤、快捷鍵符號（例如 ⌘、⇧）及反引號程式碼，文字與符號須逐字相同。`changed` 條目若原文改了插值，應以新 `en` 為準。
5. 按鈕、選單及標題要簡短。中文與英文、數字之間加半形空格，中文字之間不加空格，使用全形中文標點。不要自行縮寫或改動產品名稱。
6. 不確定的詞先保留英文，列進交付報告末尾的「待確認」，附 `key`、原文及疑問，不要猜測。完全尚未翻譯的條目保留空字串 `zh`。
7. 以 UTF-8 儲存，維持 JSON 兩格縮排、中文不轉成 Unicode 跳脫序列（`ensure_ascii=False`、`indent=2`），檔尾保留換行。
8. 執行下列檢查，修正每一項違規後重新執行，直到結束碼為 0。檢查器只檢查非空 `zh`；零違規不代表整份批次都已翻譯，交付前另行確認未完成條目。

```bash
python3 scripts/check_glossary.py --batch "$BATCH"
# 需要機器可讀結果時：
python3 scripts/check_glossary.py --batch "$BATCH" --json
```

每項違規會列出 key、規則及摘錄；摘要包含總數與各規則數量。結束碼 1 表示有違規，2 表示輸入或使用方式有誤。規則以可機械判斷的禁用詞為主；一般 context、relay、技能介紹等語意仍須依術語表人工確認。proxy 與 agent 同句時「代理」可能指 proxy，檢查器不報這個詞，仍須人工辨別；「智慧體」不適用此例外。程式碼、插值與 HTML 標籤內容不做術語替換，檢查器也不驗證它們是否被刪改。

**不要自己合併。** 可能有好幾個 agent 同時在翻不同批次，`locales/zh-TW.json` 只由協調者統一合併，避免互相覆蓋。翻譯 agent 交付的只有填好 `zh` 的批次檔。

協調者收齊批次後，用同一版英文目錄依序執行：

```bash
python3 scripts/sync_catalog.py apply --en "$EN" --in pending/batch-001.json --in pending/batch-002.json
python3 scripts/check_glossary.py --pack --en "$EN"
python3 scripts/validate.py "$EN" \
  '/Users/ming/Desktop/orca/src/shared/plugins/plugin-translatable-chrome.ts'
```

`apply` 會略過英文已變更、插值不一致或超過 8,192 字元的條目，並逐條列出原因；被略過的條目要退回給翻譯 agent 重做。

交付報告應記錄批次路徑、完成與未完成條目數、檢查結果，並在最後列出「待確認」（沒有則寫「無」）。全包檢查若發現其他批次的既有問題，記錄 key 及規則並回報，不要擅自擴大修改範圍。

## 審查關卡

`apply` 與全包檢查通過後，**開 PR 之前**必須交給另一位 agent 審查，流程見 `docs/review-pending.md`。翻譯 agent 不得審查自己翻的批次。審查報告要放進 PR 描述。
