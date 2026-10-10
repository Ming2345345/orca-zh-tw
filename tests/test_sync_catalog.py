"""同步目錄的回歸測試；所有寫入都使用暫存目錄。"""
import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_catalog as sync
from catalog_lib import MAX_STRING_LENGTH, flatten, read_json, write_json


class SyncCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack = self.root / "zh-TW.json"
        self.base = self.root / "en-baseline.json"
        self.en = self.root / "en.json"
        self.chrome = self.root / "chrome.ts"
        self.chrome.write_text("'auto.components.settings.plugin.allowed'", encoding="utf-8")
        self.pending = self.root / "pending.json"
        self.patcher = patch.multiple(sync, PACK=self.pack, BASELINE=self.base)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        write_json(self.pack, {"component": {"a": "甲", "c": "丙", "orphan": "舊"}})
        write_json(self.base, {"component": {"a": "A", "c": "Old C", "orphan": "Gone"}})
        write_json(self.en, {"component": {"a": "A", "b": "B", "c": "C"},
                             "auto": {"components": {"settings": {"plugin": {"secret": "Secret", "allowed": "Allowed"}}}}})

    def run_sync(self, command, **kwargs):
        args = dict(command=command, en=self.en, chrome=self.chrome, out=str(self.pending),
                    label="測試版本", batch_size=None, inputs=[str(self.pending)], prune=False)
        args.update(kwargs)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.run(argparse.Namespace(**args))
        return output.getvalue()

    def entry(self, key="component.b", en="B", zh="乙"):
        return dict(key=key, status="new", en=en, previous_en=None, previous_zh=None, zh=zh)

    def save_entries(self, entries, path=None):
        write_json(path or self.pending, dict(en_source="測試版本", entries=entries))

    def test_diff_new_changed_orphan_and_protection(self):
        self.assertEqual(self.run_sync("diff"), "新增 2，變更 1，孤兒 1，超過長度上限略過 0\n")
        document = read_json(self.pending)
        entries = {e["key"]: e for e in document["entries"]}
        self.assertEqual(document["en_source"], "測試版本")
        self.assertEqual(entries["component.c"]["previous_en"], "Old C")
        self.assertEqual(entries["component.c"]["previous_zh"], "丙")
        self.assertEqual(entries["component.b"]["status"], "new")
        self.assertNotIn("auto.components.settings.plugin.secret", entries)

    def test_diff_skips_over_limit_english(self):
        write_json(self.en, {"component": {"b": "B" * MAX_STRING_LENGTH,
                                           "c": "C" * (MAX_STRING_LENGTH + 1),
                                           "long_new": "N" * (MAX_STRING_LENGTH + 1)}})
        output = self.run_sync("diff")
        self.assertIn("新增 1，變更 0", output)
        self.assertIn("超過長度上限略過 2", output)
        entries = read_json(self.pending)["entries"]
        self.assertEqual([entry["key"] for entry in entries], ["component.b"])
        self.assertEqual(len(entries[0]["en"]), MAX_STRING_LENGTH)

    def test_apply_rejects_over_limit_translation(self):
        before, base_before = self.pack.read_bytes(), self.base.read_bytes()
        self.save_entries([self.entry(zh="譯" * (MAX_STRING_LENGTH + 1))])
        output = self.run_sync("apply")
        self.assertIn("譯文長度 8193 超過 8,192", output)
        self.assertIn("已套用 0，略過 1", output)
        self.assertEqual(self.pack.read_bytes(), before)
        self.assertEqual(self.base.read_bytes(), base_before)
        self.save_entries([self.entry(zh="譯" * MAX_STRING_LENGTH)])
        self.assertIn("已套用 1，略過 0", self.run_sync("apply"))
        self.assertEqual(len(read_json(self.pack)["component"]["b"]), MAX_STRING_LENGTH)

    def test_init_restricts_to_pack(self):
        self.run_sync("init")
        self.assertEqual(read_json(self.base), {"component": {"a": "A", "c": "C"}})
        self.assertIn("變更 0", self.run_sync("diff"))

    def test_batching_keeps_components_and_limits_large_groups(self):
        entries = [self.entry(f"auto.components.{component}.{i}")
                   for component, count in (("one", 2), ("two", 2), ("three", 5)) for i in range(count)]
        chunks = sync.batches(entries, 3)
        self.assertEqual([len(chunk) for chunk in chunks], [2, 2, 3, 2])
        self.assertEqual([e for chunk in chunks for e in chunk], entries)
        self.run_sync("diff", batch_size=2)
        self.assertTrue((self.root / "pending-001.json").exists())
        self.assertTrue((self.root / "pending-002.json").exists())

    def test_apply_multiple_files_and_order(self):
        self.save_entries([self.entry()])
        second = self.root / "second.json"
        self.save_entries([self.entry("component.c", "C", "新丙")], second)
        self.assertIn("已套用 2，略過 0", self.run_sync("apply", inputs=[str(self.pending), str(second)]))
        pack = read_json(self.pack)["component"]
        self.assertEqual(list(pack), ["a", "b", "c", "orphan"])
        self.assertEqual(pack["c"], "新丙")
        self.assertEqual(flatten(read_json(self.base))["component.b"], "B")

    def test_placeholder_and_stale_rejection(self):
        write_json(self.en, {"greeting": "Hi {{name}} {count}"})
        self.save_entries([self.entry("greeting", "Hi {{name}} {count}", "你好 {{name}}"),
                           self.entry("component.b", "B", "乙"),
                           self.entry("greeting", "Old", "舊")])
        before = self.pack.read_bytes()
        output = self.run_sync("apply")
        self.assertIn("插值不一致", output)
        self.assertIn("英文已變更或刪除", output)
        self.assertIn("略過 3", output)
        self.assertEqual(self.pack.read_bytes(), before)
        self.save_entries([self.entry("greeting", "Hi {{name}} {count}", "你好 {{name}} {count}")])
        self.assertIn("已套用 1", self.run_sync("apply"))

    def test_noop_is_byte_identical(self):
        self.pack.write_text('{"component": {"a": "甲", "c": "丙"}}', encoding="utf-8")
        before, base_before = self.pack.read_bytes(), self.base.read_bytes()
        self.save_entries([self.entry(zh="")])
        self.run_sync("apply")
        self.assertEqual(self.pack.read_bytes(), before)
        self.assertEqual(self.base.read_bytes(), base_before)

    def test_prune_both_trees_and_preserve_protected(self):
        protected = {"auto": {"components": {"settings": {"plugin": {"old": "保護"}}}}}
        pack = read_json(self.pack)
        pack.update(protected)
        write_json(self.pack, pack)
        base = read_json(self.base)
        base["baseline_only"] = "Removed"
        base.update(protected)
        write_json(self.base, base)
        self.save_entries([self.entry("auto.components.settings.plugin.secret", "Secret", "祕密")])
        output = self.run_sync("apply", prune=True)
        self.assertIn("保護路徑", output)
        self.assertIn("清除孤兒 2", output)
        for path in (self.pack, self.base):
            result = flatten(read_json(path))
            self.assertNotIn("component.orphan", result)
            self.assertNotIn("baseline_only", result)
            self.assertIn("auto.components.settings.plugin.old", result)

    def test_allowlist_can_apply(self):
        self.save_entries([self.entry("auto.components.settings.plugin.allowed", "Allowed", "允許")])
        self.assertIn("已套用 1", self.run_sync("apply"))

    def test_apply_prune_without_inputs(self):
        output = self.run_sync("apply", inputs=[], prune=True)
        self.assertIn("已套用 0，略過 0，清除孤兒 1", output)


if __name__ == "__main__":
    unittest.main()
