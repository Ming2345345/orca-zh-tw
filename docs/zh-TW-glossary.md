# Orca 繁體中文（台灣）術語表

這份術語表是翻譯與校對 `locales/zh-TW.json` 的依據。新增或修改字串時，先查這裡；表上沒有的詞，保留英文並列進文末「待確認」。

- 基準：Orca 1.4.224 的 `en.json`（15,749 條，其中 180 條是語言包不可覆寫的外掛安全文案）
- 「出現」＝英文原文含該詞的字串數；「目前用法」＝定案前本語言包的分布
- 定案日期：2026-10-10（#13 串接同日補定）。修改用詞時，同步更新這份文件與 `scripts/apply_glossary.py`

## 定案規則

下列詞原本在譯文裡有兩種以上說法，2026-10-10 定案後已用 `scripts/apply_glossary.py` 全檔統一。

| # | 英文 | 定案 | 說明 |
|---|---|---|---|
| 1 | runtime | **執行環境** | Orca 的 runtime 指某台主機上的 Orca 服務；不用「執行階段」 |
| 2 | usage | 方案、額度、token：**用量**；CPU、記憶體、磁碟：**使用量** | 不用「使用情況」 |
| 3 | base branch | **基底 branch** | 不用「基礎 branch」 |
| 4 | script | **腳本** | setup script → 設定腳本；不用「指令碼」 |
| 5 | context | LLM 的 context：**上下文**；頁面、終端機擷取的內容：**內容**；context menu：**右鍵選單** | 不用「脈絡」「情境」「內容選單」 |
| 6 | upstream | **upstream** | 與 branch 一致，保留英文 |
| 7 | relay | 雲端配對服務 Orca Relay：**Orca Relay／Relay**（產品名稱）；SSH 主機上的 remote relay：**中繼** | 兩者是不同的東西 |
| 8 | daemon | **daemon** | 保留英文，不用「常駐程式」 |
| 9 | skill | 介面標籤：**技能**；介紹技能的說明文字第一次出現時寫 **技能（skill）** | 按鈕、選單、標題不並列英文，避免太長被截斷 |
| 10 | 保留英文的大小寫 | 句中一律小寫；字串開頭且英文原文大寫時首字大寫 | 例外：Issue、Cookie、產品名稱（Orca Relay、Artifact 分享等英文原文句中也大寫者）維持大寫 |
| 11 | mobile | Orca 的行動 App 與其設定頁：**行動版**；實體設備：**手機**；mobile emulator：**手機模擬器** | 不用「手機版」「手機應用程式」指 Orca 行動版 |
| 12 | share | **分享** | 不用「共享」 |
| 13 | connect（外部服務） | 串接整合服務、審查服務供應商、任務來源等：**串接**；網路連線：**連線**；實體硬體：**連接** | 「連線整合服務」語感不順；「連結」保留給 link |

## 保留英文

台灣開發者慣用英文、翻了反而難懂的詞。中文句子裡前後加半形空格。

| 英文 | 出現 | 目前用法 | 狀態 | 備註 |
|---|---|---|---|---|
| agent | 609 | agent 606 | ✅ | 不譯「代理」「智慧體」；proxy 才譯「代理」 |
| worktree | 268 | worktree 268 | ✅ | |
| session | 284 | session 282 | ✅ | terminal session → 終端機 session |
| branch | 196 | branch 195 | ✅ | default branch → 預設 branch |
| commit | 125 | commit 124 | ✅ | commit message → commit 訊息 |
| repository／repo | 94＋81 | repo | ✅ | 一律寫 repo |
| pull request | 111 | PR 111 | ✅ | merge request → MR |
| Issue | 235 | Issue 227 | ✅ | 指 GitHub／Linear／Jira 的 issue；一般「問題」不在此列 |
| diff | 66 | diff 66 | ✅ | |
| prompt（LLM） | 98 | prompt 80 | ✅ | 系統權限視窗的 prompt → 提示；Command Prompt → 命令提示字元 |
| token | 113 | token 113 | ✅ | access token → 存取 token；API key → API 金鑰 |
| plugin | 56 | plugin 56 | ✅ | |
| artifact | 67 | artifact 67 | ✅ | |
| hook | 14 | hook 14 | ✅ | |
| clone／checkout／rebase／stage／stash | 25／25／8／12／3 | 全為英文 | ✅ | Git 操作一律保留 |
| CLI／API／SSH／VM／WSL | — | 英文 | ✅ | 縮寫不譯 |
| Cookie | 47 | Cookie／cookie | ✅ | 統一首字大寫 |
| 品牌、產品名稱 | — | 英文 | ✅ | Orca、GitHub、GitLab、Linear、Jira、Claude、Codex、Markdown 等 |

## 翻成中文

| 英文 | 譯法 | 出現 | 目前一致率 | 備註 |
|---|---|---|---|---|
| workspace | 工作區 | 631 | 629/631 | floating workspace → 浮動工作區 |
| terminal | 終端機 | 445 | 444/445 | 不用「終端」 |
| host | 主機 | 397 | 368/397 | 剩下多為 `{{host}}` 插值，不是誤譯 |
| project | 專案 | 382 | 373/382 | |
| file／folder | 檔案／資料夾 | 390／186 | 377／179 | 不用「文件」「目錄」 |
| command | 指令 | 275 | 264/275 | 「命令」只用在「命令提示字元」 |
| copy | 複製 | 268 | 238/268 | 名詞「副本」視語意而定 |
| link | 連結 | 247 | 246/247 | |
| default | 預設 | 232 | 232/232 | |
| update | 更新 | 222 | 221/222 | |
| browser | 瀏覽器 | 202 | 201/202 | |
| remote／local | 遠端／本機 | 199／195 | 197／189 | 不用「本地」 |
| settings | 設定 | 183 | 181/183 | |
| server | 伺服器 | 177 | 172/177 | |
| path | 路徑 | 175 | 130/175 | |
| review | 審查 | 169 | 143/169 | code review → 程式碼審查 |
| install | 安裝 | 159 | 156/159 | |
| tab | 分頁 | 155 | 150/155 | 不用「標籤」 |
| delete／remove | 刪除／移除 | 151／144 | 151／135 | remove 是從清單拿掉，delete 是真的刪掉，兩者不混用 |
| automation | 自動化 | 151 | 151/151 | |
| account | 帳號 | 139 | 138/139 | 不用「帳戶」 |
| refresh | 重新整理 | 138 | 137/138 | 不用「刷新」 |
| access | 存取 | 125 | 119/125 | |
| retry | 重試 | 122 | 121/122 | try again → 再試一次 |
| app | 應用程式 | 115 | 108/115 | |
| device | 裝置 | 110 | 105/110 | 不用「設備」 |
| chat | 聊天 | 108 | 104/108 | |
| connection／connect | 連線 | 104／102 | 104／90 | 外部服務用「串接」、實體硬體用「連接」，見定案規則 #13 |
| changes | 變更 | 99 | 98/99 | |
| merge | 合併 | 97 | 74/97 | |
| computer | 電腦 | 93 | 74/93 | computer use → 電腦操作 |
| sidebar | 側邊欄 | 91 | 89/91 | |
| pane | 窗格 | 88 | 85/88 | |
| sign in／log in | 登入 | 87 | 87/87 | |
| import | 匯入 | 86 | 86/86 | |
| provider | 供應商 | 75 | 49 + 插值 22 | AI provider → AI 供應商 |
| environment／environment variables | 環境／環境變數 | 67／20 | 65／20 | |
| emulator | 模擬器 | 66 | 66/66 | |
| cloud | 雲端 | 65 | 37/65 | |
| message | 訊息 | 59 | 59/59 | 不用「消息」 |
| notification | 通知 | 57 | 56/57 | |
| model | 模型 | 54 | 51/54 | |
| pairing | 配對 | 50 | 47/50 | |
| profile | 設定檔 | 48 | 47/48 | |
| source control | 原始檔控制 | 45 | 44/45 | 與 VS Code 繁中版一致 |
| status bar | 狀態列 | 31 | 31/31 | |
| quick command | 快速指令 | 24 | 24/24 | |
| orchestration | 編排 | 22 | 22/22 | |

## 格式規則

1. 只翻譯字串值。key、`{{插值}}`、HTML 標籤、快捷鍵符號（⌘、⇧）、反引號裡的程式碼一律不動。
2. 插值的雙大括號不可改成單大括號，也不可刪除。
3. 中文與英文、數字之間加半形空格；中文與標點之間不加。
4. 中文內文用全形標點（，。：；「」）；引號用「」，不用 “”。
5. 不確定的地方保留英文，並列進文末「待確認」。

## 工具

`<orca>` 是 Orca 原始碼的路徑，en.json 與 plugin-translatable-chrome.ts 要取自同一版。

| 腳本 | 用途 |
|---|---|
| `scripts/sync_catalog.py` | Orca 改版時找出新增與變更的英文字串，切成待翻譯批次；翻完後合併回語言包並更新 `locales/en-baseline.json` |
| `scripts/check_glossary.py` | 依本術語表檢查禁用譯法、大陸用語、格式與大小寫 |
| `scripts/validate.py` | 依 Orca 語言包載入規則檢查（條目數、深度、長度、保護路徑、佔位符） |
| `scripts/apply_glossary.py` | 修改術語表後，批次統一既有譯文 |

Orca 改版時的流程（翻譯步驟見 `docs/translate-pending.md`）：

```bash
EN=<orca>/src/renderer/src/i18n/locales/en.json
CHROME=<orca>/src/shared/plugins/plugin-translatable-chrome.ts
python3 scripts/sync_catalog.py diff --en $EN --chrome $CHROME --out pending/batch.json --batch-size 250 --label "Orca vX.Y.Z"
# 每個批次交給一個 agent 翻譯，各自跑 check_glossary.py --batch
python3 scripts/sync_catalog.py apply --en $EN --in pending/batch-001.json ...   # 協調者統一合併
python3 scripts/check_glossary.py --pack --en $EN
python3 scripts/validate.py $EN $CHROME
```

## 待確認

- `components.workspace.cleanup.browse.facet.context`（Local context）目前譯「本機脈絡」，需看實際畫面確認是不是 LLM 的 context
- `auto.components.right.sidebar.ChecksPanel.dda5924a40`（hosted review context）目前譯「託管審查情境」，語意不是 LLM 的 context，暫不更動
