# Orca 繁體中文（台灣）語言包

[Orca](https://github.com/stablyai/orca) 的繁體中文（台灣）介面翻譯，以 Orca plugin 語言包的形式提供。

A Traditional Chinese (Taiwan) UI translation for Orca, shipped as a plugin language pack. Developer terms such as agent, worktree, commit, and branch stay in English.

## 安裝

兩種方式擇一：

**A. 直接以 Git URL 安裝（固定版本）**

1. 開啟 Orca 的 **設定 → Plugins → 安裝 plugin**，切到 **Git URL**。
2. 輸入（`#` 後面是版本 tag，最新版本見 [Releases](https://github.com/mark22013333/orca-zh-tw/releases)）：
   ```
   https://github.com/mark22013333/orca-zh-tw.git#v1.0.0
   ```
3. 安裝後在權限確認視窗啟用。

**B. 加入 marketplace 來源（之後可在 Orca 內更新）**

1. 開啟 **設定 → Plugins → 管理來源**，新增來源：
   - Git URL：`https://github.com/mark22013333/orca-zh-tw.git`
   - Git ref：`main`
2. 在 marketplace 找到 **繁體中文（台灣）** 並安裝、啟用。

安裝後到 **設定 → 外觀 → 語言**，選擇 `zh-TW — mark22013333.zh-tw`。

## 用詞原則

台灣開發者慣用的技術詞保留英文，一般介面用語使用台灣中文。

| 保留英文 | 使用中文 |
|---|---|
| agent、worktree、session、repo、PR、MR、commit、branch、diff、hook、token、prompt、rebase、checkout、stage、stash、artifact、callback、plugin、clone、rollback、Issue | 終端機、工作區、遠端、分頁、設定、檔案、資料夾、埠、代理（僅指 proxy） |

中文句子裡的英文與數字前後加半形空格，標點使用全形。

## 涵蓋範圍

- 以 Orca 1.4.214 的 `en.json` 為基準，所有可由語言包翻譯的字串都已翻譯。
- 下列字串依 Orca 的設計**無法**由語言包覆寫，會維持英文：
  - `auto.components.settings.plugin*` 底下 180 條 plugin 安全相關文案
  - 2 條超過 8,192 字元的內嵌 CSS 動畫樣式（不是介面文字）
- Orca 之後新增的字串，在語言包更新前會顯示英文。
- 語言選單目前會顯示 `zh-TW — mark22013333.zh-tw`，因為 plugin 語言包還不能宣告原生名稱。

## 製作方式

1. 以 Orca 內建簡體中文 catalog 為底稿，經 OpenCC `s2twp` 轉為台灣繁體。
2. 依上方用詞表將技術詞還原為英文；替換前先比對英文原文，避免誤換（例如只有英文為 agent 時，才把「代理」換成 agent）。
3. 以英文原文為準，由 AI 分批逐條校對：修正誤譯、大陸用語與歧義詞，並補齊簡體版缺漏的條目。
4. 另請一位未參與校對的審查者抽樣複查，並依結果統一全檔用詞。
5. 套用 Orca 內建語系的修正規則（品牌名、中英文之間空格），並以 Orca 本身的語言包驗證器檢查，包括條目上限、保護路徑與插值。

發現翻譯問題歡迎開 issue 或 PR。

## 授權

MIT。翻譯的英文原文來自 Orca（MIT License，Copyright (c) 2026 Lovecast Inc.）。
