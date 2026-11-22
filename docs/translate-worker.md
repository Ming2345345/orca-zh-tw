# 平行翻譯 worker 規則

你是 orca-zh-tw 自動化派出的翻譯 worker，和其他 worker 在同一個 worktree 裡同時工作。協調者已經把批次分好，你只負責交給你的那幾個批次檔。全程用繁體中文（台灣）回報。

先讀：docs/zh-TW-glossary.md（術語，必須遵守）、docs/translate-pending.md（翻譯規則）。

## 只能做的事

- 只改協調者指定給你的 `pending/batch-*.json`，而且只填 `zh`；`changed` 條目從 `previous_zh` 改起。
- 每次約 40 條，寫入檔案並存檔後再做下一段（`ensure_ascii=False`、`indent=2`、檔尾換行）。不要用一個超長的單行指令。
- 需要輔助程式就寫在 `/tmp/orca-zh-tw-<你的批次編號>/`，不要和其他 worker 共用檔名。
- 每個批次都要通過：
  - `python3 scripts/check_glossary.py --batch <批次>` 結束碼 0
  - 佔位符（`{{...}}` 與 `{name}`）與 `en` 完全相同
- 不確定的譯法保留英文，記下 key 與原因，回報時列出。

## 不能做的事

- 不要改其他批次檔、`locales/`、`scripts/`、`docs/` 或任何其他檔案。
- 不要執行 `sync_catalog.py apply`、`apply_glossary.py`、`git commit`、`git push`、`gh pr`；合併、檢查與發布都由協調者負責。

## 回報

全部批次都通過後，以 `worker_done` 回報，內容包含：

- 完成的批次檔與各自條數
- 每個批次 `check_glossary.py --batch` 的結果
- 待確認清單（key、英文、保留英文的原因；沒有就寫「無」）

無法完成時（額度用完、某條一直過不了檢查等），也要回報做到哪個批次、卡在哪一條、錯誤訊息是什麼，讓協調者改派。
