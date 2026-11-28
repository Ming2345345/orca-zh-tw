"""precheck（scripts/orca_update_check.sh）的情境測試。

用假的 gh、orca 與暫存 git remote 模擬，不會碰到真的 GitHub 或 Orca 自動化。
"""
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "orca_update_check.sh"
INSTALLED = "1.4.281"
SYNCED = "1.4.280"

FAKE_GH = """#!/bin/bash
# 假的 gh：只支援 pr list，依 FAKE_GH_MODE 回傳結果。
echo "$@" >> "$FAKE_LOG/gh.args"
if [ "${FAKE_GH_MODE:-}" = "fail" ]; then
  echo "HTTP 502: Bad Gateway" >&2; exit 1
fi
echo "A new release of gh is available" >&2
jq_expr=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--jq" ]; then jq_expr="$2"; shift; fi
  shift
done
jq -r "$jq_expr" "$FAKE_LOG/prs.json"
"""

FAKE_ORCA = """#!/bin/bash
# 假的 orca：automations runs/show/edit/run。
echo "$@" >> "$FAKE_LOG/orca.args"
case "$1 $2" in
  "automations runs")
    if [ "${FAKE_ORCA_MODE:-}" = "fail" ]; then echo "Orca 未啟動" >&2; exit 1; fi
    cat "$FAKE_LOG/runs.json" ;;
  "automations show")
    echo '{"result":{"automation":{"launchSetup":{"extraAgentArgs":"--model gemini-test"}}}}' ;;
  *) echo '{}' ;;
esac
"""

FAKE_PICK = """#!/bin/bash
echo gemini-test
"""


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(shutil.which("defaults") and shutil.which("jq"), "需要 macOS 的 defaults 與 jq")
class OrcaUpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.log = root / "log"
        self.log.mkdir()

        app = root / "Orca.app"
        (app / "Contents").mkdir(parents=True)
        with open(app / "Contents" / "Info.plist", "wb") as f:
            plistlib.dump({"CFBundleShortVersionString": INSTALLED}, f)

        origin = root / "origin.git"
        work = root / "work"
        git("init", "-q", "--bare", "-b", "main", str(origin))
        git("init", "-q", "-b", "main", str(work))
        (work / "locales").mkdir()
        (work / "locales" / "orca-version.txt").write_text(SYNCED + "\n")
        git("add", ".", cwd=work)
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init", cwd=work)
        git("remote", "add", "origin", str(origin), cwd=work)
        git("push", "-q", "origin", "main", cwd=work)

        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, body in (("gh", FAKE_GH), ("orca", FAKE_ORCA), ("pick", FAKE_PICK)):
            path = bin_dir / name
            path.write_text(body)
            path.chmod(0o755)

        self.env = {
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(root),
            "FAKE_LOG": str(self.log),
            "ORCA_ZH_TW_REPO": str(work),
            "ORCA_APP": str(app),
            "ORCA_ZH_TW_PICK_MODEL": str(bin_dir / "pick"),
        }
        self.set_prs([])
        self.set_runs([])

    def set_prs(self, prs):
        (self.log / "prs.json").write_text(json.dumps(prs))

    def set_runs(self, runs):
        (self.log / "runs.json").write_text(json.dumps({"result": {"runs": runs}}))

    def run_check(self, **env):
        result = subprocess.run(
            ["bash", str(SCRIPT)], env={**self.env, **env}, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout + result.stderr

    @staticmethod
    def run_record(number, status, hours_ago):
        dispatched = None if hours_ago is None else int((time.time() - hours_ago * 3600) * 1000)
        return {"runNumber": number, "status": status, "dispatchedAt": dispatched}

    def test_open_sync_pr_skips(self):
        self.set_prs([
            {"number": 8, "headRefName": "fix/precheck-hourly"},
            {"number": 19, "headRefName": "auto/orca-v1.4.281"},
        ])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("#19 auto/orca-v1.4.281", out)
        self.assertNotIn("#8", out)
        self.assertFalse((self.log / "orca.args").exists(), "有 PR 時不該再查自動化紀錄")
        args = (self.log / "gh.args").read_text()
        self.assertIn("-R Ming2345345/orca-zh-tw", args)
        self.assertIn("--state open", args)

    def test_gh_failure_skips_instead_of_dispatching(self):
        code, out = self.run_check(FAKE_GH_MODE="fail")
        self.assertEqual(code, 2, out)
        self.assertIn("無法查詢", out)
        self.assertIn("HTTP 502", out)

    def test_running_run_skips(self):
        self.set_runs([
            self.run_record(56, "dispatching", None),  # 這次 run 自己，precheck 時還沒派工
            self.run_record(55, "dispatched", 0.5),
            self.run_record(54, "completed", 20),
        ])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 55 仍在執行", out)

    def test_stale_running_run_does_not_block(self):
        self.set_runs([self.run_record(55, "dispatched", 4)])
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("視為異常", out)

    def test_orca_failure_skips(self):
        code, out = self.run_check(FAKE_ORCA_MODE="fail")
        self.assertEqual(code, 2, out)
        self.assertIn("無法讀取自動化紀錄", out)

    def test_no_pr_and_no_running_run_dispatches(self):
        self.set_prs([{"number": 8, "headRefName": "fix/precheck-hourly"}])
        self.set_runs([
            self.run_record(56, "dispatching", None),
            self.run_record(55, "skipped_precheck", None),
            self.run_record(54, "completed", 0.2),
        ])
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn(f"需要更新：語言包 {SYNCED} → Orca {INSTALLED}", out)
        self.assertIn("模型：gemini-test", out)

    def test_already_synced_skips_before_gh(self):
        with open(Path(self.env["ORCA_APP"]) / "Contents" / "Info.plist", "wb") as f:
            plistlib.dump({"CFBundleShortVersionString": SYNCED}, f)
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("已同步", out)
        self.assertFalse((self.log / "gh.args").exists())


if __name__ == "__main__":
    unittest.main()
