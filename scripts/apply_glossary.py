#!/usr/bin/env python3
"""依 docs/zh-TW-glossary.md 的定案，統一 locales/zh-TW.json 的用詞。

用法：python3 scripts/apply_glossary.py <en.json> [--dry-run]

每條修改都以英文原文為條件（只有英文含對應術語時才換），並把修改紀錄寫到
stdout，方便逐條複查。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "locales" / "zh-TW.json"


def flatten(tree, prefix=""):
    out = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = value
    return out


def set_path(tree, path, value):
    *parents, leaf = path.split(".")
    for part in parents:
        tree = tree[part]
    tree[leaf] = value


def en_has(pattern):
    rx = re.compile(pattern, re.I)
    return lambda en: bool(rx.search(en))


# (英文條件, 舊字串, 新字串)：英文符合條件時，才把譯文中的舊字串換成新字串。
REPLACEMENTS = [
    # 1. runtime → 執行環境
    (en_has(r"\bruntimes?\b"), "執行階段", "執行環境"),
    # 2. usage：資源用「使用量」，方案、額度用「用量」
    (en_has(r"\b(cpu|memory|disk)\b.*\busage\b|\busage\b.*\b(cpu|memory|disk)\b"), "使用情況", "使用量"),
    (en_has(r"\busage\b"), "使用情況", "用量"),
    # 3. base branch → 基底 branch
    (en_has(r"\bbase\b"), "基礎 branch", "基底 branch"),
    # 4. script → 腳本
    (en_has(r"\bscripts?\b"), "指令碼", "腳本"),
    # 5. context menu → 右鍵選單
    (en_has(r"\bcontext menu\b"), "內容選單", "右鍵選單"),
    # 6. upstream 保留英文
    (en_has(r"\bupstream\b"), "上游", "upstream"),
    # 7. SSH 主機上的 relay 是中繼程式；Orca Relay 是產品名稱，維持英文
    (en_has(r"\breset the relay\b"), "重設 relay", "重設中繼"),
    # 8. daemon 保留英文
    (en_has(r"\bdaemons?\b"), "常駐程式", "daemon"),
    # 11. Orca Mobile → Orca 行動版
    (en_has(r"\bOrca Mobile\b"), "Orca Mobile", "Orca 行動版"),
    (en_has(r"\bOrca Mobile Button\b"), "Orca 手機版", "Orca 行動版"),
    (en_has(r"\bOrca mobile app\b"), "Orca 手機應用程式", "Orca 行動版"),
    (en_has(r"\bthe mobile app\b"), "手機應用程式", "行動版"),
    (en_has(r"Settings\s*(→|>)\s*Mobile"), "行動裝置", "行動版"),
    (en_has(r"^Open Mobile Settings$"), "行動裝置", "行動版"),
    # share → 分享
    (en_has(r"\bshar(e|ed|ing)\b"), "共享", "分享"),
]

# 逐條指定譯文：語意需要人工判斷，或原譯文有誤的字串。
OVERRIDES = {
    # 英文改版後舊譯文沒更新（原譯「Git AI 作者 變更」）
    "auto.components.settings.Settings.43b68e10f0": "你有尚未儲存的 AI 設定。離開將會捨棄這些設定。",
    "auto.components.settings.Settings.17bdee4ff1": "要捨棄尚未儲存的 AI 設定嗎？",
    "auto.components.status.bar.UsageRosterPanel.compactTooltip": "精簡用量：每個供應商一則摘要",
    # 5. LLM 的 context → 上下文
    "auto.components.NativeChatResumeOnRestartModal.updateBody": "當 Orca 安裝更新時，這些聊天正在進行中。恢復後會讓每個聊天回到中斷的位置並保留完整上下文，同時請 agent 先確認先前正在做的事再繼續。你自己的 prompt 不會重新傳送。",
    "auto.components.settings.LinearAgentSkillGuide.noteLinkedBody": "Issue 操作最好在從「任務」建立的 worktree 中進行，這樣 Issue 會保持連結並作為上下文。",
    "auto.components.settings.TaskSourceLinearSetup.connectDescription": "新增個人 API 金鑰，讓 Orca 能夠瀏覽 Issue，並帶著 Issue 上下文開啟工作區。",
    "auto.components.settings.settingOwnership.terminalQuickCommands": "指令儲存在此用戶端，接著限定為全域或某個專案設定，以便在所選的終端機中執行。",
    # 11. 設定頁的 Mobile 分頁 → 行動版
    "auto.hooks.useSettingsNavigationMetadata.1cd25673df": "行動版",
    "auto.components.settings.MobileSettingsPane.e7a3ae8c4e": "行動版",
    "auto.components.settings.Settings.c40dadaac8": "行動版",
    "auto.components.settings.Settings.mobile_group": "行動版",
    "auto.components.settings.mobile.settings.search.ffd52a96e4": "行動版",
    "auto.components.settings.appearance.search.74618577c7": "行動版",
    "auto.components.settings.mobile.pane.search.6db86f445f": "行動版",
    "auto.components.settings.mobile.settings.search.f213400800": "行動版",
    "auto.components.settings.mobile.settings.search.74618577c7": "行動版",
    "auto.components.mobile.MobilePageToolbar.e1c7b4a92d": "在「設定」>「行動版」中設定。",
    # 9. 介紹技能的說明文字，第一次出現時並列英文
    "auto.hooks.useSettingsNavigationMetadata.shareSkillsDescription": "透過未公開的連結分享你的技能（skill）。任何取得連結的人都能安裝。",
    "auto.components.settings.shareSkills.description": "透過未公開的連結分享你的技能（skill）。任何取得連結的人都能安裝。",
    "auto.components.settings.shareSkills.searchDescription": "透過未公開的連結分享你的技能（skill）。任何取得連結的人都能安裝。",
    "auto.components.settings.orcaAccount.skillsDescription": "透過未公開的連結分享一項技能（skill）或一整套技能，並安裝到你使用的任何電腦上。",
    "auto.components.skills.SkillsPage.emptyCopy": "已掃描的技能（skill）資料夾是空的。請安裝分享的技能組合，或新增技能後重新整理。",
    "auto.components.settings.linear.agent.skill.install.cta.description": "讓 agent 讀取和編輯 Linear 任務。完整引導設定（連線 + 技能（skill）+ 可見性）位於「設定」→「任務來源」。",
}

# 10. 保留英文的詞：句中小寫，標籤開頭首字大寫
KEEP_ENGLISH = [
    "agent", "agents", "worktree", "worktrees", "session", "sessions", "branch", "branches",
    "commit", "commits", "repo", "repos", "diff", "diffs", "prompt", "prompts", "token", "tokens",
    "plugin", "plugins", "artifact", "artifacts", "hook", "hooks", "shell", "upstream", "daemon",
    "clone", "checkout", "rebase", "stage", "stash",
]
CASE_RX = re.compile(r"(?<![A-Za-z0-9_\-./`{])(" + "|".join(KEEP_ENGLISH) + r")(?![A-Za-z0-9_\-./`}])", re.I)
PROTECTED_SPAN = re.compile(r"`[^`]*`|\{\{[^}]*\}\}")


def normalize_case(zh, en):
    protected = [m.span() for m in PROTECTED_SPAN.finditer(zh)]

    def fix(match):
        start = match.start()
        if any(a <= start < b for a, b in protected):
            return match.group(0)
        word = match.group(0)
        if start == 0:
            return word[0].upper() + word[1:] if en[:1].isupper() else word
        if not word[0].isupper():
            return word
        before = zh[max(0, start - 2):start]
        if "「" in before or "→" in before or ">" in before:
            return word  # 引用介面上的標籤名稱，維持原樣
        if re.search(r"(?<=\S )" + re.escape(word) + r"\b", en):
            return word  # 英文原文句中也大寫，視為專有名詞
        return word.lower()

    return CASE_RX.sub(fix, zh)


CJK_SPACE = re.compile(r"(?<=[一-鿿]) (?=[一-鿿])")


def main():
    en_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    en = flatten(json.loads(en_path.read_text()))
    tree = json.loads(PACK.read_text())
    pack = flatten(tree)
    changes = []

    for key, zh in pack.items():
        if not isinstance(zh, str):
            continue
        source = en.get(key)
        new = zh
        if isinstance(source, str):
            for cond, old, repl in REPLACEMENTS:
                if old in new and cond(source):
                    new = new.replace(old, repl)
            new = normalize_case(new, source)
        if key in OVERRIDES:
            new = OVERRIDES[key]
        new = CJK_SPACE.sub("", new)
        if new != zh:
            changes.append((key, source, zh, new))
            set_path(tree, key, new)

    missing = [k for k in OVERRIDES if k not in pack]
    for key, source, old, new in changes:
        print(f"{key}\n  EN  {source}\n  舊  {old}\n  新  {new}")
    print(f"\n共修改 {len(changes)} 條", file=sys.stderr)
    if missing:
        print(f"OVERRIDES 中找不到的 key：{missing}", file=sys.stderr)
        sys.exit(1)
    if not dry_run:
        PACK.write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
