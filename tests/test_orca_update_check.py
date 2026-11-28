"""precheck（scripts/orca_update_check.sh）與 prepare_update.sh 分支命名的情境測試。

用假的 gh、orca 與暫存 git remote 模擬，不會碰到真的 GitHub 或 Orca 自動化。
假指令會檢查收到的引數，引數不符合預期時以非 0 結束，讓測試失敗。
"""
import json
import plistlib
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "orca_update_check.sh"
PREPARE = ROOT / "scripts" / "prepare_update.sh"
AUTOMATION_ID = "3f122394-4962-42b7-a928-5a1048a50ed9"
INSTALLED = "1.4.281"
SYNCED = "1.4.280"

FAKE_GH = r"""#!/bin/bash
# 假的 gh：只接受 precheck 會下的 pr list 指令。
echo "$*" >> "$FAKE_LOG/gh.args"
expected="pr list -R Ming2345345/orca-zh-tw --state open --base main --limit 500 --json number,headRefName,baseRefName,isCrossRepository"
if [ "$*" != "$expected" ]; then echo "fake gh: 非預期引數：$*" >&2; exit 64; fi
case "${FAKE_GH_MODE:-}" in
  fail) echo "HTTP 502: Bad Gateway" >&2; exit 1 ;;
esac
echo "A new release of gh is available" >&2
cat "$FAKE_LOG/prs.json"
"""

FAKE_ORCA = r"""#!/bin/bash
# 假的 orca：automations runs 依 cursor 回傳 runs.json 的第幾頁；show/edit/run 只回固定內容。
echo "$*" >> "$FAKE_LOG/orca.args"
case "$1 $2" in
  "automations runs")
    base="automations runs --id $FAKE_AUTOMATION_ID --limit 100 --json"
    if [ "${FAKE_ORCA_MODE:-}" = "loop" ]; then  # cursor 永遠不前進
      echo '{"ok":true,"result":{"runs":[],"nextCursor":"same"}}'; exit 0
    fi
    case "$*" in
      "$base") page=0 ;;
      "$base --cursor p"*) all="$*"; page="${all##*--cursor p}" ;;
      *) echo "fake orca: 非預期引數：$*" >&2; exit 64 ;;
    esac
    case "${FAKE_ORCA_MODE:-}" in
      fail) echo '{"ok":false,"error":{"code":"runtime_error","message":"Automation not found."}}'; exit 1 ;;
      empty) exit 0 ;;
      notok) echo '{"ok":false,"result":{"runs":[]}}'; exit 0 ;;
      noruns) echo '{"ok":true,"result":{}}'; exit 0 ;;
      truncated) echo '{"ok":true,"result":{"runs":['; exit 0 ;;
      double) echo '{"ok":true,"result":{"runs":[]}}'; echo '{"ok":true,"result":{"runs":[]}}'; exit 0 ;;
    esac
    jq -c --argjson p "$page" '{ok: true, result: {runs: .[$p],
      nextCursor: (if $p + 1 < length then "p\($p + 1)" else null end)}}' "$FAKE_LOG/runs.json" ;;
  "automations show")
    echo '{"ok":true,"result":{"automation":{"launchSetup":{"extraAgentArgs":"--model gemini-test"}}}}' ;;
  *) echo '{"ok":true}' ;;
esac
"""

FAKE_PICK = "#!/bin/bash\necho gemini-test\n"


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def commit_all(cwd, message):
    git("add", "-A", cwd=cwd)
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", message, cwd=cwd)


def write_plist(app, version):
    (app / "Contents").mkdir(parents=True, exist_ok=True)
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleShortVersionString": version}, f)


def make_repo(root, synced):
    """建立 origin（bare）與一份 clone，main 上有 locales/orca-version.txt。"""
    origin = root / "origin.git"
    work = root / "work"
    git("init", "-q", "--bare", "-b", "main", str(origin))
    git("init", "-q", "-b", "main", str(work))
    (work / "locales").mkdir()
    (work / "locales" / "orca-version.txt").write_text(synced + "\n")
    commit_all(work, "init")
    git("remote", "add", "origin", str(origin), cwd=work)
    git("push", "-q", "origin", "main", cwd=work)
    return origin, work


def now_ms(hours_ago):
    return int((time.time() - hours_ago * 3600) * 1000)


def run_record(number, status, hours_ago, launched_only=False, created_hours_ago=None):
    """hours_ago 是派工時間；None 表示還沒派工（例如這次 run 自己還在 precheck）。"""
    at = None if hours_ago is None else now_ms(hours_ago)
    if created_hours_ago is None:
        created_hours_ago = 0 if hours_ago is None else hours_ago
    created = now_ms(created_hours_ago)
    return {
        "runNumber": number,
        "status": status,
        "createdAt": created,
        "launchedAt": at,
        "dispatchedAt": None if launched_only else at,
    }


def sync_pr(number, branch, base="main", cross=False):
    return {"number": number, "headRefName": branch, "baseRefName": base, "isCrossRepository": cross}


@unittest.skipUnless(shutil.which("defaults") and shutil.which("jq"), "需要 macOS 的 defaults 與 jq")
class OrcaUpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.log = root / "log"
        self.log.mkdir()
        self.app = root / "Orca.app"
        write_plist(self.app, INSTALLED)
        self.origin, self.work = make_repo(root, SYNCED)

        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, body in (("gh", FAKE_GH), ("orca", FAKE_ORCA), ("pick", FAKE_PICK)):
            path = bin_dir / name
            path.write_text(body)
            path.chmod(0o755)

        self.env = {
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(root), "LANG": "zh_TW.UTF-8",
            "FAKE_LOG": str(self.log),
            "FAKE_AUTOMATION_ID": AUTOMATION_ID,
            "ORCA_ZH_TW_REPO": str(self.work),
            "ORCA_APP": str(self.app),
            "ORCA_ZH_TW_PICK_MODEL": str(bin_dir / "pick"),
        }
        self.set_prs([])
        self.set_runs([])

    def set_prs(self, prs):
        (self.log / "prs.json").write_text(json.dumps(prs))

    def set_runs(self, *pages):
        (self.log / "runs.json").write_text(json.dumps(list(pages) or [[]]))

    def run_check(self, **env):
        result = subprocess.run(
            ["bash", str(SCRIPT)], env={**self.env, **env}, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout + result.stderr

    def assert_dispatches(self, **env):
        code, out = self.run_check(**env)
        self.assertEqual(code, 0, out)
        self.assertIn(f"需要更新：語言包 {SYNCED} → Orca {INSTALLED}", out)
        return out

    # --- 版本 ---
    def test_already_synced_skips_before_gh(self):
        write_plist(self.app, SYNCED)
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("已同步", out)
        self.assertFalse((self.log / "gh.args").exists())

    def test_downgraded_app_skips(self):
        write_plist(self.app, "1.4.279")
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("比語言包 1.4.280 舊", out)

    def test_numeric_version_compare(self):
        write_plist(self.app, "1.10.0")
        (self.work / "locales" / "orca-version.txt").write_text("1.9.99\n")
        commit_all(self.work, "bump")
        git("push", "-q", "origin", "main", cwd=self.work)
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_missing_version_file_exits_2(self):
        (self.work / "locales" / "orca-version.txt").unlink()
        commit_all(self.work, "rm")
        git("push", "-q", "origin", "main", cwd=self.work)
        code, out = self.run_check()
        self.assertEqual(code, 2, out)
        self.assertIn("讀不到 origin/main", out)

    def test_pr_merged_during_check_is_rechecked(self):
        # 假 gh 被呼叫時，模擬同版 PR 剛好合併進 main。
        hook = self.log / "merge.sh"
        hook.write_text(
            f"cd {self.work} && echo {INSTALLED} > locales/orca-version.txt && "
            "git -c user.name=t -c user.email=t@example.com commit -qam merged && git push -q origin main\n"
        )
        gh = Path(self.env["PATH"].split(":")[0]) / "gh"
        gh.write_text(gh.read_text().replace('cat "$FAKE_LOG/prs.json"', f'bash {hook} >/dev/null 2>&1\ncat "$FAKE_LOG/prs.json"'))
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn(f"已同步：Orca {INSTALLED}", out)

    # --- 同步 PR ---
    def test_open_sync_pr_skips(self):
        self.set_prs([sync_pr(8, "fix/precheck-hourly"), sync_pr(19, "auto/orca-v1.4.281-20261128-090000")])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("#19 auto/orca-v1.4.281-20261128-090000", out)
        self.assertNotIn("#8", out)
        self.assertFalse((self.log / "orca.args").exists(), "有 PR 時不該再查自動化紀錄")

    def test_fork_or_other_base_pr_does_not_block(self):
        self.set_prs([
            sync_pr(20, "auto/orca-v1.4.281", cross=True),
            sync_pr(21, "auto/orca-v1.4.281", base="dev"),
        ])
        self.assert_dispatches()

    def test_closed_pr_with_leftover_branch_retries(self):
        # 同版 PR 已關閉（不在 open 清單），但舊分支還留在 origin。
        git("push", "-q", "origin", "main:auto/orca-v1.4.281", cwd=self.work)
        self.assert_dispatches()

    def test_gh_failure_skips_instead_of_dispatching(self):
        code, out = self.run_check(FAKE_GH_MODE="fail")
        self.assertEqual(code, 2, out)
        self.assertIn("HTTP 502", out)

    def test_gh_invalid_or_full_response_exits_2(self):
        for prs in ({"not": "array"}, [sync_pr(i, f"feat/{i}") for i in range(500)]):
            with self.subTest(prs=str(prs)[:30]):
                self.set_prs(prs)
                code, out = self.run_check()
                self.assertEqual(code, 2, out)
                self.assertIn("無法解析", out)

    # --- 自動化 run ---
    def test_running_run_skips(self):
        self.set_runs([
            run_record(56, "dispatching", None),  # 這次 run 自己，precheck 時還沒派工
            run_record(55, "dispatched", 0.5),
            run_record(54, "completed", 20),
        ])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 55（dispatched", out)
        args = (self.log / "orca.args").read_text()
        self.assertIn(f"automations runs --id {AUTOMATION_ID} --limit 100 --json", args)

    def test_newer_finished_run_does_not_hide_running_one(self):
        # 54 還在翻譯時手動啟動 55，55 先結束；54 仍在執行，應該擋住。
        self.set_runs([
            run_record(56, "dispatching", None),
            run_record(55, "completed", 0.2),
            run_record(54, "dispatched", 1),
        ])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 54（dispatched", out)

    def test_launched_but_not_delivered_run_skips(self):
        self.set_runs([run_record(55, "dispatching", 0.1, launched_only=True)])
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 55（dispatching", out)

    def test_running_run_on_second_page_skips(self):
        self.set_runs(
            [run_record(n, "completed", 0.01 * (60 - n)) for n in range(60, 55, -1)],
            [run_record(55, "dispatched", 0.5)],
        )
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 55", out)
        self.assertIn("--cursor p1", (self.log / "orca.args").read_text())

    def test_reads_all_pages_even_if_created_long_ago(self):
        # run 53 建立得比第一頁的 run 早，但排隊到半小時前才派工；不能依建立時間提早停止翻頁。
        self.set_runs(
            [run_record(54, "completed", 10)],
            [run_record(53, "dispatched", 0.5, created_hours_ago=11)],
        )
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 53（dispatched", out)

    def test_large_page_is_not_passed_as_argument(self):
        # 一頁 100 筆、每筆帶 20 KB 輸出，總共超過 macOS 的 ARG_MAX（1 MB）。
        big = {"outputSnapshot": {"content": "x" * 20000}}
        page = [{**run_record(n, "completed", 1), **big} for n in range(200, 101, -1)]
        page.append({**run_record(101, "dispatched", 0.5), **big})
        self.set_runs(page)
        self.assertGreater((self.log / "runs.json").stat().st_size, 1_100_000)
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("run 101（dispatched", out)

    def test_cursor_not_advancing_exits_2(self):
        code, out = self.run_check(FAKE_ORCA_MODE="loop")
        self.assertEqual(code, 2, out)
        self.assertIn("cursor 沒有前進", out)

    def test_three_hour_boundary(self):
        for hours, blocks in ((2.95, True), (3.05, False)):
            with self.subTest(hours=hours):
                self.set_runs([run_record(55, "dispatched", hours)])
                code, out = self.run_check()
                if blocks:
                    self.assertEqual(code, 1, out)
                else:
                    self.assertEqual(code, 0, out)
                    self.assertIn("視為異常", out)

    def test_custom_timeout(self):
        self.set_runs([run_record(55, "dispatched", 4)])
        code, out = self.run_check(ORCA_ZH_TW_RUN_TIMEOUT_HOURS="6")
        self.assertEqual(code, 1, out)

    def test_invalid_timeout_exits_2(self):
        for value in ('"3"', "null", "0", "0.0", "-1", "abc"):
            with self.subTest(value=value):
                code, out = self.run_check(ORCA_ZH_TW_RUN_TIMEOUT_HOURS=value)
                self.assertEqual(code, 2, out)
                self.assertIn("必須是正數", out)

    def test_orca_failure_shows_json_error(self):
        code, out = self.run_check(FAKE_ORCA_MODE="fail")
        self.assertEqual(code, 2, out)
        self.assertIn("Automation not found.", out)

    def test_invalid_orca_responses_exit_2(self):
        for mode in ("empty", "notok", "noruns", "truncated", "double"):
            with self.subTest(mode=mode):
                code, out = self.run_check(FAKE_ORCA_MODE=mode)
                self.assertEqual(code, 2, out)
                self.assertIn("回應無效", out)

    def test_no_pr_and_no_running_run_dispatches(self):
        self.set_prs([sync_pr(8, "fix/precheck-hourly")])
        self.set_runs([
            run_record(56, "dispatching", None),
            run_record(55, "skipped_precheck", None),
            run_record(54, "completed", 0.2),
            run_record(53, "dispatch_failed", 0.3),
        ])
        out = self.assert_dispatches()
        self.assertIn("模型：gemini-test", out)


@unittest.skipUnless(shutil.which("defaults"), "需要 macOS 的 defaults")
class PrepareUpdateBranchTests(unittest.TestCase):
    """prepare_update.sh：每次建立唯一分支，同版重試不會撞到舊 worktree 佔用的分支。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.app = root / "Orca.app"
        write_plist(self.app, INSTALLED)
        _, self.work = make_repo(root, SYNCED)
        shutil.copytree(ROOT / "scripts", self.work / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("zh-TW.json", "en-baseline.json"):
            (self.work / "locales" / name).write_text("{}\n")
        commit_all(self.work, "scripts")
        git("push", "-q", "origin", "main", cwd=self.work)

        # 假的 Orca 原始碼：有 v<版本> tag 與 en.json、chrome 檔。
        src_origin = root / "orca-src.git"
        self.src = root / "orca-src"
        git("init", "-q", "--bare", str(src_origin))
        git("init", "-q", "-b", "main", str(self.src))
        en = self.src / "src" / "renderer" / "src" / "i18n" / "locales" / "en.json"
        en.parent.mkdir(parents=True)
        en.write_text(json.dumps({"hello": "Hello"}))
        chrome = self.src / "src" / "shared" / "plugins" / "plugin-translatable-chrome.ts"
        chrome.parent.mkdir(parents=True)
        chrome.write_text("")
        commit_all(self.src, "src")
        git("tag", f"v{INSTALLED}", cwd=self.src)
        git("remote", "add", "origin", str(src_origin), cwd=self.src)
        git("push", "-q", "--tags", "origin", "main", cwd=self.src)
        self.env = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(root), "LANG": "zh_TW.UTF-8",
            "ORCA_SRC": str(self.src),
            "ORCA_APP": str(self.app),
        }

    def prepare(self, cwd, env=None):
        return subprocess.run(["bash", str(cwd / "scripts" / "prepare_update.sh")], cwd=cwd,
                              env={**self.env, **(env or {})}, capture_output=True, text=True, timeout=60)

    def new_worktree(self, name):
        path = Path(self.temp.name) / name
        git("worktree", "add", "-q", "--detach", str(path), "origin/main", cwd=self.work)
        return path

    def test_same_second_runs_get_different_branches(self):
        fake_bin = Path(self.temp.name) / "fixed-date"
        fake_bin.mkdir()
        (fake_bin / "date").write_text("#!/bin/bash\necho 20261128-090000\n")
        (fake_bin / "date").chmod(0o755)
        env = {"PATH": f"{fake_bin}:{self.env['PATH']}"}
        branches = []
        for name in ("run-a", "run-b"):
            path = self.new_worktree(name)
            result = self.prepare(path, env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            branches.append(git("branch", "--show-current", cwd=path).strip())
        self.assertNotEqual(branches[0], branches[1])
        for branch in branches:
            self.assertTrue(branch.startswith(f"auto/orca-v{INSTALLED}-20261128-090000-"), branch)

    def test_main_newer_than_app_exits_3_before_touching_orca_src(self):
        (self.work / "locales" / "orca-version.txt").write_text("1.4.282\n")
        commit_all(self.work, "newer")
        git("push", "-q", "origin", "main", cwd=self.work)
        path = self.new_worktree("run-old")
        # ORCA_SRC 指到不存在的路徑：只要 prepare 去 fetch 或切換它就會失敗，不會是 3。
        result = self.prepare(path, {"ORCA_SRC": str(Path(self.temp.name) / "missing")})
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("1.4.282", result.stdout)
        self.assertEqual(git("branch", "--show-current", cwd=path).strip(), "")

    def test_retry_while_old_branch_is_checked_out(self):
        # 舊 run 的 worktree 還佔著舊命名的分支，遠端也還留著。
        old = Path(self.temp.name) / "old-run"
        git("worktree", "add", "-q", "-b", f"auto/orca-v{INSTALLED}", str(old), "origin/main", cwd=self.work)
        git("push", "-q", "origin", f"auto/orca-v{INSTALLED}", cwd=self.work)
        new = Path(self.temp.name) / "new-run"
        git("worktree", "add", "-q", "--detach", str(new), "origin/main", cwd=self.work)
        result = self.prepare(new)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        branch = git("branch", "--show-current", cwd=new).strip()
        self.assertRegex(branch, rf"^auto/orca-v{INSTALLED}-\d{{8}}-\d{{6}}-[0-9a-f]{{8}}$")
        self.assertIn(f"BRANCH={branch}", (new / "pending" / "update.env").read_text())

    def test_already_synced_exits_3_without_branch(self):
        write_plist(self.app, SYNCED)
        git("tag", f"v{SYNCED}", cwd=self.src)
        git("push", "-q", "--tags", "origin", cwd=self.src)
        result = self.prepare(self.work)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(git("branch", "--show-current", cwd=self.work).strip(), "main")


@unittest.skipUnless(shutil.which("jq"), "需要 jq")
class PublishGuardTests(unittest.TestCase):
    """publish_guard.sh：發布前重讀 main 版本與開著的同步 PR。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.log = root / "log"
        self.log.mkdir()
        _, self.work = make_repo(root, SYNCED)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
        self.env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(root), "LANG": "zh_TW.UTF-8", "FAKE_LOG": str(self.log)}
        (self.log / "prs.json").write_text("[]")

    def guard(self, **env):
        result = subprocess.run(["bash", str(ROOT / "scripts" / "publish_guard.sh"), INSTALLED], cwd=self.work,
                                env={**self.env, **env}, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout + result.stderr

    def test_ok_when_nobody_published(self):
        (self.log / "prs.json").write_text(json.dumps([sync_pr(8, "fix/precheck-hourly")]))
        code, out = self.guard()
        self.assertEqual(code, 0, out)

    def test_main_already_published(self):
        for version in (INSTALLED, "1.4.282"):
            with self.subTest(version=version):
                (self.work / "locales" / "orca-version.txt").write_text(version + "\n")
                commit_all(self.work, version)
                git("push", "-q", "origin", "main", cwd=self.work)
                code, out = self.guard()
                self.assertEqual(code, 3, out)

    def test_other_run_opened_pr(self):
        (self.log / "prs.json").write_text(json.dumps([sync_pr(30, "auto/orca-v1.4.281-20261128-090000-abcd1234")]))
        code, out = self.guard()
        self.assertEqual(code, 3, out)
        self.assertIn("#30", out)

    def test_gh_failure_blocks_publish(self):
        code, out = self.guard(FAKE_GH_MODE="fail")
        self.assertEqual(code, 2, out)
        self.assertIn("HTTP 502", out)


if __name__ == "__main__":
    unittest.main()
