#!/usr/bin/env python3
"""檢查 locales/zh-TW.json 是否符合 Orca 語言包規則與本專案的格式規則。

用法：python3 scripts/validate.py <en.json> <plugin-translatable-chrome.ts>

兩個檔案都取自同一版 Orca 原始碼：
  src/renderer/src/i18n/locales/en.json
  src/shared/plugins/plugin-translatable-chrome.ts（保護路徑中的例外清單）

檢查項目：
- Orca 載入限制：條目數 ≤ 20,000、深度 ≤ 16、單一字串 ≤ 8,192 字元、
  不可覆寫 auto.components.settings.plugin* 保護路徑（例外清單除外）
- {{插值}} 與 {單大括號} 佔位符集合必須與英文原文相同
- 中文字之間不可有空格
- 列出英文已刪除的 key（孤兒）與尚未翻譯的 key 數量
"""
import json
import re
import sys
from pathlib import Path

from catalog_lib import MAX_STRING_LENGTH, PLACEHOLDER, flatten, is_protected, read_exempt

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "locales" / "zh-TW.json"
CJK_SPACE = re.compile(r"[一-鿿] [一-鿿]")


def main():
    en_stats, pack_stats = {"depth": 0}, {"depth": 0}
    en = flatten(json.loads(Path(sys.argv[1]).read_text()), stats=en_stats)
    exempt = read_exempt(sys.argv[2])
    pack = flatten(json.loads(PACK.read_text()), stats=pack_stats)
    errors = []

    if len(pack) > 20000:
        errors.append(f"條目數 {len(pack)} 超過 20,000")
    if pack_stats["depth"] > 16:
        errors.append(f"深度 {pack_stats['depth']} 超過 16")
    for key, value in pack.items():
        if is_protected(key, exempt):
            errors.append(f"{key}: 保護路徑，語言包不可覆寫")
        if not isinstance(value, str):
            errors.append(f"{key}: 值不是字串")
            continue
        if len(value) > MAX_STRING_LENGTH:
            errors.append(f"{key}: 長度 {len(value)} 超過 {MAX_STRING_LENGTH:,}")
        if CJK_SPACE.search(value):
            errors.append(f"{key}: 中文字之間有空格 → {value[:60]}")
        source = en.get(key)
        if isinstance(source, str) and sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(value)):
            errors.append(f"{key}: 插值不一致 EN={PLACEHOLDER.findall(source)} ZH={PLACEHOLDER.findall(value)}")

    translatable = {k for k in en if not is_protected(k, exempt)}
    if not exempt:
        errors.append("例外清單是空的，請確認第二個參數是 plugin-translatable-chrome.ts")
    orphans = sorted(set(pack) - set(en))
    missing = sorted(translatable - set(pack))
    print(f"條目 {len(pack)}，涵蓋 {len(translatable & set(pack))}/{len(translatable)}，"
          f"未翻譯 {len(missing)}，孤兒 {len(orphans)}")
    for line in errors:
        print("✗", line)
    print("通過" if not errors else f"{len(errors)} 個問題")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
