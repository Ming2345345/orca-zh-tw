# Orca 自動化「orca-zh-tw 補翻」提示詞

自動化的提示詞存在 Orca 內部，這份是版本控管用的副本。修改後請同步貼回 Orca 的自動化設定。

---

你在 orca-zh-tw（Orca 的繁體中文（台灣）語言包）的一個新 worktree 裡。本機 Orca 已更新，請把語言包同步到新版並開 PR 給使用者審查。全程用繁體中文（台灣）回報。

先讀：docs/zh-TW-glossary.md（術語，必須遵守）、docs/translate-pending.md（翻譯規則）、docs/review-pending.md（審查規則）。

1. 準備：執行 `./scripts/prepare_update.sh`，再 `source pending/update.env`（取得 VERSION、BRANCH、EN、CHROME）。它會建立分支 `$BRANCH`（`auto/orca-v<版本>-<時間>-<隨機碼>`，每次都不同，所以同版本的 PR 被關掉後可以直接重試）並在 pending/ 產生 batch-*.json（可能沒有任何批次）。**結束碼 3 表示 origin/main 已經是這個版本或更新：直接結束，回報「已同步，不需要更新」，不要 commit、push 或開 PR。**
2. 翻譯（平行）：你是協調者，盡量把翻譯分給 worker 同時做，自己不翻（只有一組時自己翻）。
   - 分組：`python3 scripts/assign_batches.py --max-workers 4`，輸出 `{"workers": [[批次檔...], ...]}`。空陣列表示沒有要翻的，直接到第 3 步。
   - 只有一組：自己依 docs/translate-worker.md 的規則翻完那幾個批次。
   - 多組：先 `WORKER_MODEL=$(./scripts/pick_agy_model.sh)`（High 沒容量就回傳 Medium），然後每組派一位 worker：
     ```
     orca orchestration run-create --objective "翻譯 $BRANCH" --json
     orca orchestration worker-start --worktree current --agent antigravity --model "$WORKER_MODEL" --task-title "翻譯 v$VERSION 第 N 組" --spec "依 docs/translate-worker.md 翻譯這些批次：<該組批次檔，以空白分隔>。只改這些檔案的 zh，完成後以 worker_done 回報。" --timeout-ms 5400000 --json
     ```
     每次 worker-start 間隔約 20 秒，避免同時擠爆容量。
   - 等待：用 `orca orchestration check --wait --timeout-ms 600000` 收 `worker_done`，直到每一組都回報。每組回報後，你自己再對該組每個批次跑一次 `python3 scripts/check_glossary.py --batch <批次>` 確認結束碼 0，然後 `worker-release` 釋放。
   - 失敗處理：worker 回報失敗、90 分鐘內沒回報，或你的複查不通過時，先 `worker-stop` 那位，把它沒完成的批次改派給新的 worker（同一組最多重派 1 次）；重派後仍失敗，就自己把剩下的翻完。完全無法完成時視為失敗，第 6 步改用 draft PR。
   - 彙整所有 worker 回報的待確認清單，放進 PR 內容。
3. 合併：`python3 scripts/sync_catalog.py apply --en "$EN" --chrome "$CHROME" --prune` 加上每個批次的 `--in <批次>`。必須「略過 0」；有略過就修正該條再重跑。
4. 檢查：
   - `python3 scripts/apply_glossary.py "$EN"`（統一大小寫）
   - `python3 scripts/check_glossary.py --pack --en "$EN"` 必須 0 違規
   - `python3 scripts/validate.py "$EN" "$CHROME"` 必須「通過」
   - `python3 -m unittest discover -s tests` 必須 OK
5. **審查**：把分支交給另一位 agent 審查，不得由你自己審。審查者依 docs/review-pending.md 審查 `git diff origin/main -- locales/zh-TW.json`。審查者的選擇順序：
   - 先用 Antigravity 的 Claude（`--agent antigravity --model claude-sonnet-4-6`）。
   - 若 worker 無法啟動、回報額度用完／rate limit，或 30 分鐘內沒有 `worker_done`，先 `worker-release` 釋放它，再改用 Codex（`--agent codex`，不指定 model，用 Codex 自己的設定）重新指派同一份審查。
   啟動審查者的指令：
   ```
   orca orchestration run-create --objective "審查 $BRANCH" --json
   orca orchestration worker-start --worktree current --agent antigravity --model claude-sonnet-4-6 --task-title "審查 v$VERSION" --spec "依 docs/review-pending.md 審查 git diff origin/main -- locales/zh-TW.json，只回報有問題的 key 與建議，不要修改檔案" --timeout-ms 1800000 --json
   # 備援：orca orchestration worker-start --worktree current --agent codex --task-title "審查 v$VERSION（Codex 備援）" --spec "<同上>" --timeout-ms 1800000 --json
   orca orchestration worker-read --dispatch <dispatch_id> --source auto
   ```
   worker 以 `worker_done` 回報；用 `orca orchestration check` 收訊息，審查完用 `worker-release` 釋放。審查者只讀不改，修正由你套用後重跑第 4 步。取得審查報告（實際審查者與模型、審查條目數、修正清單、待確認、檢查結果）。若兩位審查者都無法完成，視為失敗，第 6 步改用 draft PR。
6. 發布到分支：
   - 先執行 `./scripts/publish_guard.sh "$VERSION"`：重讀 origin/main 的版本和開著的同步 PR。**結束碼 3 表示別的 run 已經發布了（main 已是這個版本或更新，或已有開著的同步 PR）：不要 commit、push 或開 PR，直接結束並回報它印出的原因。** 結束碼 2 表示查不到資訊：同樣不要發布，回報錯誤訊息。只有結束碼 0 才繼續。
   - `echo "$VERSION" > locales/orca-version.txt`
   - orca-plugin.json 的 version 升 minor（例如 1.2.0 → 1.3.0）
   - commit 訊息：`feat: 同步 Orca v$VERSION（新增 N、變更 M、清除孤兒 K）`，結尾加一行 `Co-Authored-By: Antigravity (Orca automation)`；有採用審查建議時再加一行 `Co-Authored-By: <實際審查者，例如 Antigravity Claude Sonnet 4.6 或 Codex> (reviewer)`
   - `git push -u origin "$BRANCH"`
   - `gh pr create --repo Ming2345345/orca-zh-tw --base main --head "$BRANCH" --title "同步 Orca v$VERSION" --body <內容>`，內容列出：新增／變更／孤兒數、四項檢查結果、**審查報告（審查者、審查條目數、修正清單）**、待確認清單（沒有就寫「無」）。

規則：
- 絕不 push 到 main、絕不合併 PR、不要改 ~/Desktop/orca 的檔案（prepare_update.sh 切 tag 除外）。
- 第 2–5 步有任何一項無法通過時，仍然 commit、push 分支，但改用 `gh pr create --draft`，並在 PR 內容最前面寫清楚哪一項失敗、錯誤訊息是什麼。
- 不確定的譯法保留英文，列入 PR 的待確認清單，不要猜。
