#!/usr/bin/env python3
"""檢查待翻譯批次或語言包是否符合 docs/zh-TW-glossary.md。

只檢查可機械判定的禁用詞與格式；語意、插值完整性仍需人工校對及 validate.py。
每個命中位置算一項違規，受保護的程式碼、插值與 HTML 標籤不檢查。
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "locales" / "zh-TW.json"

# 規則名稱、英文條件（不分大小寫且限定完整詞）、禁用譯法。
TERM_RULES = [
    ("runtime", r"runtimes?", r"執行階段"),
    ("usage", r"usage", r"使用情況"),
    ("base-branch", r"base\s+branch(?:es)?", r"基礎"),
    ("script", r"scripts?", r"指令碼"),
    ("context-menu", r"context\s+menus?", r"內容選單"),
    # 一般 context 可能是內容；術語表的兩個待確認條目不自動判錯。
    ("llm-context", r"(?:LLM|model|agent|token)s?\b.*\bcontext|context\b.*\b(?:LLM|model|agent|token)s?", r"脈絡|情境"),
    ("upstream", r"upstream", r"上游"),
    ("daemon", r"daemons?", r"常駐程式"),
    ("mobile", r"Orca\s+mobile|(?:the\s+)?mobile\s+app", r"手機版|手機應用程式"),
    ("share", r"share[sd]?|sharing", r"共享"),
    ("agent", r"agents?", r"代理|智慧體"),
    ("worktree", r"worktrees?", r"工作樹"),
    ("session", r"sessions?", r"工作階段"),
    ("branch", r"branch(?:es)?", r"分支"),
    ("commit", r"commits?", r"提交"),
    ("repository", r"repositories|repository|repos?", r"儲存庫|存放庫"),
    ("terminal", r"terminals?", r"終端(?!機)"),
    ("file", r"files?", r"文件"),
    ("folder", r"folders?", r"目錄"),
    ("command", r"commands?", r"命令(?!提示字元)"),
    ("local", r"local", r"本地"),
    ("tab", r"tabs?", r"標籤"),
    ("account", r"accounts?", r"帳戶"),
    ("refresh", r"refresh(?:es|ed|ing)?", r"刷新"),
    ("device", r"devices?", r"設備"),
    ("connection", r"connect(?:s|ed|ing|ions?)?", r"連接"),
    ("message", r"messages?", r"消息"),
]
MAINLAND_TERMS = (
    "信息", "軟件", "默認", "視頻", "用戶", "服務器", "數據", "網絡",
    "代碼", "運行", "調用", "設置", "加載", "菜單", "鼠標", "屏幕",
)
KEEP_ENGLISH = (
    "agent", "agents", "worktree", "worktrees", "session", "sessions", "branch",
    "branches", "commit", "commits", "repo", "repos", "diff", "diffs", "prompt",
    "prompts", "token", "tokens", "plugin", "plugins", "artifact", "artifacts",
    "hook", "hooks", "shell", "upstream", "daemon", "daemons", "clone", "checkout",
    "rebase", "stage", "stash",
)
# Issue、Cookie、品牌及 CLI/API/SSH/VM/WSL/PR/MR 不在大小寫檢查清單。
PROTECTED = re.compile(r"`+[^`]*`+|\{\{.*?\}\}|\{[A-Za-z_][\w.]*\}|</?[A-Za-z][^>]*>", re.S)
CASE_RX = re.compile(r"(?<![A-Za-z0-9_\-./`{])(?:" + "|".join(KEEP_ENGLISH) + r")(?![A-Za-z0-9_\-./`}])", re.I)
CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f"
FORMAT_RULES = [
    ("cjk-space", re.compile(r"(?<=[" + CJK + r"])[ \t\u3000]+(?=[" + CJK + r"])")),
    ("cjk-punctuation", re.compile(r"(?<=[" + CJK + r"])[,.](?=[" + CJK + r"])")),
]


def visible(value):
    """以等長哨兵遮住不可修改的區段，避免被當成中文間空白。"""
    return PROTECTED.sub(lambda match: "\x00" * len(match.group()), value)


def check_pair(key, en, zh):
    text = visible(zh)
    source = visible(en)
    violations = []

    def add(rule, match):
        excerpt = zh[max(0, match.start() - 16):match.end() + 16]
        violations.append({"key": key, "rule": rule, "excerpt": excerpt})

    for rule, english, banned in TERM_RULES:
        if not re.search(r"\b(?:" + english + r")\b", source, re.I):
            continue
        for match in re.finditer(banned, text):
            # 同句含 proxy 時「代理」可能指 proxy；「智慧體」仍不允許。
            if rule == "agent" and match.group() == "代理" and re.search(r"\bprox(?:y|ies)\b", source, re.I):
                continue
            add("term:" + rule, match)
    for term in MAINLAND_TERMS:
        for match in re.finditer(term, text):
            add("mainland:" + term, match)
    for rule, pattern in FORMAT_RULES:
        for match in pattern.finditer(text):
            add(rule, match)
    for match in CASE_RX.finditer(text):
        word = match.group()
        if word == word.lower():
            continue
        if match.start() == 0 and en[:1].isupper() and word == word.capitalize():
            continue
        # 沿用 normalizer：引用介面標籤與原文句中大寫的專有名詞維持原樣。
        if any(mark in text[max(0, match.start() - 2):match.start()] for mark in ("「", "→", ">")):
            continue
        if re.search(r"(?<=\S )" + re.escape(word) + r"\b", source):
            continue
        add("english-case", match)
    return violations


def flatten(tree, prefix=""):
    if not isinstance(tree, dict):
        raise ValueError("語言目錄必須是 JSON 物件")
    result = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, path))
        elif isinstance(value, str):
            result[path] = value
        else:
            raise ValueError(f"{path}：值必須是字串")
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_pairs(args):
    if args.batch:
        batch = read_json(args.batch)
        if not isinstance(batch, dict) or not isinstance(batch.get("entries"), list):
            raise ValueError("批次必須包含 entries 陣列")
        pairs = []
        for entry in batch["entries"]:
            if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) for k in ("key", "en", "zh")):
                raise ValueError("每個條目必須有字串 key、en、zh")
            if entry["zh"]:
                pairs.append((entry["key"], entry["en"], entry["zh"]))
        return pairs
    en = flatten(read_json(args.en))
    pack = flatten(read_json(PACK))
    # 孤兒 key 仍檢查一般用詞與格式；缺少原文時無法套用條件式術語規則。
    return [(key, en.get(key, ""), zh) for key, zh in pack.items()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--batch", help="待翻譯批次 JSON")
    mode.add_argument("--pack", action="store_true", help="檢查 locales/zh-TW.json")
    parser.add_argument("--en", help="Orca 英文目錄 JSON（--pack 必填）")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    args = parser.parse_args(argv)
    if args.pack and not args.en:
        parser.error("--pack 必須搭配 --en")
    if args.batch and args.en:
        parser.error("--en 僅適用於 --pack")
    try:
        pairs = load_pairs(args)
    except (OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"讀取失敗：{exc}", file=sys.stderr)
        return 2
    violations = [item for pair in pairs for item in check_pair(*pair)]
    counts = dict(sorted(Counter(item["rule"] for item in violations).items()))
    summary = {"checked": len(pairs), "violations": len(violations), "by_rule": counts}
    if args.json:
        print(json.dumps({"violations": violations, "summary": summary}, ensure_ascii=False, indent=2))
    else:
        for item in violations:
            print(f'{item["key"]}\t{item["rule"]}\t{json.dumps(item["excerpt"], ensure_ascii=False)}')
        print(f"共檢查 {len(pairs)} 條，發現 {len(violations)} 項違規")
        for rule, count in counts.items():
            print(f"  {rule}：{count}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
