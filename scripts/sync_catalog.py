#!/usr/bin/env python3
"""找出新增／變更英文，並將待翻譯批次合併回語言包。"""
import argparse
import copy
import sys
from pathlib import Path

from catalog_lib import MAX_STRING_LENGTH, flatten, is_protected, PLACEHOLDER, put, read_exempt, read_json, remove, write_json

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "locales" / "zh-TW.json"
BASELINE = ROOT / "locales" / "en-baseline.json"


def exemptions(en_path, chrome=None):
    # init/apply 可從 Orca 原始碼樹找到清單；獨立英文檔可用 --chrome 指定。
    if chrome:
        return read_exempt(chrome)
    for parent in Path(en_path).resolve().parents:
        candidate = parent / "shared/plugins/plugin-translatable-chrome.ts"
        if candidate.is_file():
            return read_exempt(candidate)
    # 無清單時採保守規則，不允許寫入任何 plugin 保護路徑。
    return set()


def batches(entries, size):
    if not size:
        return [entries]
    groups = {}
    for entry in entries:
        parts = entry["key"].split(".")
        component = ".".join(parts[:3] if parts[:2] == ["auto", "components"] else parts[:2])
        groups.setdefault(component, []).append(entry)
    result, current = [], []
    for group in groups.values():
        if current and len(current) + len(group) > size:
            result.append(current)
            current = []
        while len(group) > size:
            result.append(group[:size])
            group = group[size:]
        current.extend(group)
    if current or not result:
        result.append(current)
    return result


def run(args):
    en_tree, pack_tree = read_json(args.en), read_json(PACK)
    en, pack = flatten(en_tree), flatten(pack_tree)
    exempt = exemptions(args.en, args.chrome)
    if args.command == "init":
        baseline = {}
        for key in pack:
            if key in en and not is_protected(key, exempt):
                put(baseline, key, en[key], pack_tree)
        write_json(BASELINE, baseline)
        print(f"已建立英文基準：{len(flatten(baseline))} 條")
        return
    if not BASELINE.exists():
        raise ValueError("缺少英文基準，請先執行 init")
    baseline_tree = read_json(BASELINE)
    baseline = flatten(baseline_tree)
    orphans = [key for key in pack if key not in en and not is_protected(key, exempt)]
    if args.command == "diff":
        entries = []
        over_limit = 0
        for key, value in en.items():
            if not isinstance(value, str) or is_protected(key, exempt):
                continue
            if len(value) > MAX_STRING_LENGTH:
                over_limit += 1
                continue
            status = "new" if key not in pack else "changed" if baseline.get(key) != value else None
            if status:
                entries.append(dict(key=key, status=status, en=value,
                                    previous_en=baseline.get(key) if status == "changed" else None,
                                    previous_zh=pack.get(key) if status == "changed" else None, zh=""))
        output = Path(args.out)
        for index, batch in enumerate(batches(entries, args.batch_size), 1):
            path = output.with_name(f"{output.stem}-{index:03d}.json") if args.batch_size else output
            write_json(path, dict(en_source=args.label or str(args.en), entries=batch))
        new = sum(e["status"] == "new" for e in entries)
        print(f"新增 {new}，變更 {len(entries) - new}，孤兒 {len(orphans)}，"
              f"超過長度上限略過 {over_limit}")
        return
    original_pack, original_baseline = copy.deepcopy(pack_tree), copy.deepcopy(baseline_tree)
    applied, skipped = 0, 0
    for filename in args.inputs:
        document = read_json(filename)
        for entry in document["entries"]:
            key = entry.get("key") if isinstance(entry, dict) else None
            reason = None
            if not isinstance(key, str):
                reason = "條目缺少有效的 key"
            elif is_protected(key, exempt):
                reason = "保護路徑"
            elif not isinstance(entry.get("zh"), str) or not entry["zh"].strip():
                reason = "尚未翻譯"
            elif len(entry["zh"]) > MAX_STRING_LENGTH:
                reason = f"譯文長度 {len(entry['zh'])} 超過 {MAX_STRING_LENGTH:,}"
            elif key not in en or not isinstance(en[key], str) or entry.get("en") != en[key]:
                reason = "英文已變更或刪除"
            elif sorted(PLACEHOLDER.findall(entry["zh"])) != sorted(PLACEHOLDER.findall(en[key])):
                reason = "插值不一致"
            else:
                # 先確認兩棵樹都能寫入，避免半套更新。
                new_pack, new_baseline = copy.deepcopy(pack_tree), copy.deepcopy(baseline_tree)
                try:
                    put(new_pack, key, entry["zh"], en_tree)
                    put(new_baseline, key, entry["en"], en_tree)
                except ValueError as error:
                    reason = str(error)
                else:
                    pack_tree, baseline_tree = new_pack, new_baseline
                    applied += 1
            if reason:
                skipped += 1
                print(f"略過 {key}：{reason}")
    pruned = set()
    if args.prune:
        pruned = {key for key in set(flatten(pack_tree)) | set(flatten(baseline_tree))
                  if key not in en and not is_protected(key, exempt)}
        for key in pruned:
            remove(pack_tree, key)
            remove(baseline_tree, key)
    if pack_tree != original_pack:
        write_json(PACK, pack_tree)
    if baseline_tree != original_baseline:
        write_json(BASELINE, baseline_tree)
    print(f"已套用 {applied}，略過 {skipped}，清除孤兒 {len(pruned)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "diff", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--en", required=True, type=Path)
        command.add_argument("--chrome", type=Path, required=name == "diff", help="外掛保護路徑例外清單")
        if name == "diff":
            command.add_argument("--out", required=True)
            command.add_argument("--label")
            command.add_argument("--batch-size", type=int)
        if name == "apply":
            command.add_argument("--in", dest="inputs", action="append", default=[])
            command.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    if getattr(args, "batch_size", None) is not None and args.batch_size < 1:
        parser.error("--batch-size 必須大於零")
    if args.command == "apply" and not args.inputs and not args.prune:
        parser.error("apply 必須指定 --in 或 --prune")
    try:
        run(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"錯誤：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
