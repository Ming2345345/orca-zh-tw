# Orca 繁體中文（台灣）術語表

這份術語表是翻譯與校對 `locales/zh-TW.json` 的依據。新增或修改字串時，先查這裡；表上沒有的詞，保留英文並列進文末「待確認」。

- 基準：Orca 1.4.224 的 `en.json`（15,749 條，其中 16 條為語言包不可覆寫的保護字串）
- 「出現」＝英文原文含該詞的字串數；「目前用法」＝本語言包現況的分布，用來找出不一致的地方
- 狀態：✅ 已定案　⚠️ 需要決定（見下一節）

## 需要決定的項目

統計時發現下列詞在現有翻譯裡有兩種以上說法，請選定一種，之後全檔統一。

| # | 英文 | 目前用法（條數） | 建議 | 理由 |
|---|---|---|---|---|
| 1 | runtime | 執行環境 102／執行階段 14 | **執行環境** | Orca 的 runtime 指某台主機上的 Orca 服務，比較接近「環境」；「執行階段」容易被讀成時間點 |
| 2 | usage | 用量 105／使用情況 48 | 方案、額度：**用量**；CPU、磁碟等資源：**使用量** | 「使用情況」太籠統，狀態列空間也有限 |
| 3 | base branch | 基底 branch／基礎 branch | **基底 branch** | 與 Git 的 base 慣用譯法一致 |
| 4 | setup script | 設定腳本／設定指令碼 | **設定腳本** | 台灣開發者口語多說「腳本」；若偏好微軟風格則選「指令碼」 |
| 5 | context（LLM） | 上下文 48／內容 21／情境 4／脈絡 2 | LLM 的 context：**上下文**；頁面內容：**內容** | 兩種語意分開處理，其餘說法併入 |
| 6 | upstream | upstream 21／上游 5 | **upstream** | branch 已保留英文，upstream 跟著保留比較一致 |
| 7 | relay | Relay 28／中繼 10 | 待查：若「Orca Relay」是產品名稱則保留 **Relay**，否則用 **中繼** | 需要看實際畫面確認 |
| 8 | daemon | daemon 14／常駐程式 5 | **常駐程式** 或保留 **daemon** 二選一 | 目前混用，只要統一即可 |
| 9 | skill | 技能 288 | 維持 **技能**，或改成保留 **skill** | agent、session 都保留英文，skill 是否比照？「技能」已全面使用，改動成本高 |
| 10 | 保留英文的大小寫 | agent 598／Agent 8；shell 29／Shell 17 | 句中一律小寫；單獨作為標題、按鈕時首字大寫 | 目前大小寫不一 |
| 11 | mobile | 手機 53／行動 20 | 指 Orca 行動 App：**行動版**；指實體設備：**手機** | 依語意分開，兩者都正確 |

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
| connection／connect | 連線 | 104／102 | 104／90 | 不用「連接」 |
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

## 待確認

- `relay` 是否為產品名稱（見決定項目 #7）
- 全檔有 15 條中文字之間多了空格，例如「切換 聊天介面」「無法清理 雲端 VM 執行環境。」，多半是插值被展開後殘留的空格，修正時要對照英文原文確認
