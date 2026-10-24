# Orca 自動化「orca-zh-tw 補翻」提示詞

自動化的提示詞存在 Orca 內部，這份是版本控管用的副本。修改後請同步貼回 Orca 的自動化設定。

---

你在 orca-zh-tw（Orca 的繁體中文（台灣）語言包）的一個新 worktree 裡。本機 Orca 已更新，請把語言包同步到新版並開 PR 給使用者審查。全程用繁體中文（台灣）回報。

先讀：docs/zh-TW-glossary.md（術語，必須遵守）、docs/translate-pending.md（翻譯規則）、docs/review-pending.md（審查規則）。

1. 準備：執行 `./scripts/prepare_update.sh`，再 `source pending/update.env`（取得 VERSION、EN、CHROME）。它會建立分支 auto/orca-v$VERSION 並在 pending/ 產生 batch-*.json（可能沒有任何批次）。
2. 翻譯：逐一處理 pending/batch-*.json。只填 `zh`，`changed` 條目從 `previous_zh` 改起。每次約 40 條，寫入檔案並存檔後再做下一段（ensure_ascii=False、indent=2、檔尾換行）；不要用一個超長的單行指令，需要輔助程式就寫在 /tmp。每個批次都要讓這兩項通過：
   - `python3 scripts/check_glossary.py --batch <批次>` 結束碼 0
   - 佔位符（{{...}} 與 {name}）與 `en` 完全相同
3. 合併：`python3 scripts/sync_catalog.py apply --en "$EN" --chrome "$CHROME" --prune` 加上每個批次的 `--in <批次>`。必須「略過 0」；有略過就修正該條再重跑。
4. 檢查：
   - `python3 scripts/apply_glossary.py "$EN"`（統一大小寫）
   - `python3 scripts/check_glossary.py --pack --en "$EN"` 必須 0 違規
   - `python3 scripts/validate.py "$EN" "$CHROME"` 必須「通過」
   - `python3 -m unittest discover -s tests` 必須 OK
5. **審查（新增）**：把分支交給另一位 agent（Claude）審查，不得由你自己審。依 docs/review-pending.md 審查 `git diff origin/main -- locales/zh-TW.json`，審查者可直接修正明確錯誤並重跑第 4 步四項檢查。審查者逐條檢查應交給便宜的模型（如 haiku subagent）執行，主模型只彙整與判斷爭議。取得審查報告（審查條目數、修正清單、待確認、檢查結果）。若無法指派審查者或審查未完成，視為失敗，第 6 步改用 draft PR。
6. 發布到分支：
   - `echo "$VERSION" > locales/orca-version.txt`
   - orca-plugin.json 的 version 升 minor（例如 1.2.0 → 1.3.0）
   - commit 訊息：`feat: 同步 Orca v$VERSION（新增 N、變更 M、清除孤兒 K）`，結尾加一行 `Co-Authored-By: Antigravity (Orca automation)`；審查者有修正時再加一行 `Co-Authored-By: Claude (reviewer)`
   - `git push -u origin auto/orca-v$VERSION`
   - `gh pr create --repo Ming2345345/orca-zh-tw --base main --head auto/orca-v$VERSION --title "同步 Orca v$VERSION" --body <內容>`，內容列出：新增／變更／孤兒數、四項檢查結果、**審查報告（審查者、審查條目數、修正清單）**、待確認清單（沒有就寫「無」）。

規則：
- 絕不 push 到 main、絕不合併 PR、不要改 ~/Desktop/orca 的檔案（prepare_update.sh 切 tag 除外）。
- 第 2–5 步有任何一項無法通過時，仍然 commit、push 分支，但改用 `gh pr create --draft`，並在 PR 內容最前面寫清楚哪一項失敗、錯誤訊息是什麼。
- 不確定的譯法保留英文，列入 PR 的待確認清單，不要猜。
