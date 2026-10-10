"""術語檢查器的規則及命令列測試。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_glossary as checker


class GlossaryTests(unittest.TestCase):
    def rules(self, en, zh):
        return [item["rule"] for item in checker.check_pair("test.key", en, zh)]

    def test_term_rules(self):
        cases = [
            ("runtime", "Runtimes", "執行階段", "執行環境"),
            ("usage", "Usage", "使用情況", "用量"),
            ("base-branch", "Base branch", "基礎 branch", "基底 branch"),
            ("script", "Script", "指令碼", "腳本"),
            ("context-menu", "Context menu", "內容選單", "右鍵選單"),
            ("llm-context", "LLM context", "脈絡", "上下文"),
            ("upstream", "Upstream", "上游", "upstream"),
            ("daemon", "Daemon", "常駐程式", "daemon"),
            ("mobile", "Orca mobile app", "手機應用程式", "行動版"),
            ("share", "Sharing", "共享", "分享"),
            ("agent", "Agent", "代理", "agent"),
            ("worktree", "Worktree", "工作樹", "worktree"),
            ("session", "Session", "工作階段", "session"),
            ("branch", "Branch", "分支", "branch"),
            ("commit", "Commit", "提交", "commit"),
            ("repository", "Repository", "儲存庫", "repo"),
            ("terminal", "Terminal", "終端", "終端機"),
            ("file", "File", "文件", "檔案"),
            ("folder", "Folder", "目錄", "資料夾"),
            ("command", "Command", "命令", "指令"),
            ("local", "Local", "本地", "本機"),
            ("tab", "Tab", "標籤", "分頁"),
            ("account", "Account", "帳戶", "帳號"),
            ("refresh", "Refresh", "刷新", "重新整理"),
            ("device", "Device", "設備", "裝置"),
            ("connection", "Connection", "連接", "連線"),
            ("message", "Message", "消息", "訊息"),
        ]
        self.assertEqual({case[0] for case in cases}, {r[0] for r in checker.TERM_RULES})
        for name, en, bad, good in cases:
            with self.subTest(rule=name):
                self.assertIn("term:" + name, self.rules(en, bad))
                self.assertEqual([], self.rules(en, good))
                self.assertEqual([], self.rules("Unrelated text", bad))

    def test_boundaries_and_exceptions(self):
        self.assertEqual([], self.rules("JavaScript profile agentic terminally", "指令碼文件代理終端"))
        self.assertEqual([], self.rules("Agent proxy", "agent 使用代理"))
        self.assertEqual(["term:agent"], self.rules("Agent proxy", "智慧體使用代理"))
        self.assertEqual([], self.rules("Command Prompt", "命令提示字元"))
        self.assertEqual([], self.rules("Local context", "本機脈絡"))
        self.assertEqual([], self.rules("mobile device", "手機"))
        self.assertEqual(["term:terminal"], self.rules("terminal", "終端機與終端"))
        self.assertEqual(["term:repository"], self.rules("repo", "存放庫"))
        self.assertEqual(["term:connection"], self.rules("connect", "連接"))

    def test_command_line_exception(self):
        self.assertEqual([], self.rules("Command line", "命令列"))
        self.assertEqual(["term:command"], self.rules("Command", "執行命令"))
        self.assertEqual(["term:command"], self.rules("Command line command", "命令列中的命令"))

    def test_folder_directory_exceptions(self):
        for source in ("Folder directory", "Folder DIRECTORIES"):
            with self.subTest(source=source):
                self.assertEqual([], self.rules(source, "目錄"))
        for text in ("根目錄", "子目錄", "主目錄", "上層目錄"):
            with self.subTest(text=text):
                self.assertEqual([], self.rules("Folder", text))
                self.assertEqual(["term:folder"], self.rules("Folder", text + "與目錄"))
        self.assertEqual(["term:folder"], self.rules("Folder", "目錄"))
        self.assertEqual(["term:folder"], self.rules("Folder directoryname", "目錄"))

    def test_file_document_exception(self):
        for source in ("File document", "File DOCUMENTS"):
            with self.subTest(source=source):
                self.assertEqual([], self.rules(source, "文件"))
        self.assertEqual(["term:file"], self.rules("File", "文件"))
        self.assertEqual(["term:file"], self.rules("File documentary", "文件"))

    def test_connection_hardware_exceptions(self):
        for hardware in ("microphone", "microphones", "cable", "cables", "USB", "Bluetooth"):
            with self.subTest(hardware=hardware):
                self.assertEqual([], self.rules("Connect " + hardware, "連接裝置"))
        for service in ("service", "integration", "source", "USBservice"):
            with self.subTest(service=service):
                self.assertEqual(["term:connection"], self.rules("Connect " + service, "連接來源"))
                self.assertEqual([], self.rules("Connect " + service, "連線至來源"))

    def test_mainland(self):
        for term in checker.MAINLAND_TERMS:
            with self.subTest(term=term):
                self.assertEqual(["mainland:" + term], self.rules("Other", term))
        self.assertEqual([], self.rules("Other", "資訊軟體預設影片使用者伺服器資料網路程式碼執行呼叫設定載入選單滑鼠螢幕"))

    def test_mainland_exceptions(self):
        self.assertEqual([], self.rules("Client exit code pairing code", "用戶端結束代碼配對代碼"))
        self.assertEqual(["mainland:用戶"], self.rules("Client and user", "用戶端與用戶"))
        self.assertEqual(["mainland:代碼"], self.rules("Source code and exit code", "代碼與結束代碼"))
        self.assertEqual([], self.rules("Generate code", "產生代碼"))
        self.assertEqual([], self.rules("Or paste this code in the mobile app:", "將代碼貼到行動版"))
        self.assertEqual(["mainland:代碼"], self.rules("Edit source code", "編輯代碼"))

    def test_format(self):
        for text in ("中 文", "中\t文", "中　文"):
            self.assertEqual(["cjk-space"], self.rules("Other", text))
        for text in ("中,文", "中.文"):
            self.assertEqual(["cjk-punctuation"], self.rules("Other", text))
        self.assertEqual([], self.rules("Other", "中文，中文。使用 agent 2 次"))
        self.assertEqual(["english-case"], self.rules("Open agent", "開啟 Agent"))
        self.assertEqual(["english-case"], self.rules("agent", "Agent"))
        self.assertEqual([], self.rules("Agent", "Agent"))
        self.assertEqual([], self.rules("Open Artifact sharing", "開啟 Artifact 分享"))
        self.assertEqual([], self.rules("Other", "使用 Issue、Cookie、API、SSH、PR、Orca Relay 及「Agent」"))
        self.assertEqual([], self.rules("Open agent", "開啟 agent"))

    def test_protected_spans(self):
        self.assertEqual([], self.rules("Other", "共有 {{count}} 個 `Agent` 項目"))
        self.assertEqual([], self.rules("Agent script", '`Agent 信息 中 文 指令碼` {{Agent}} <b title="信息">正常</b>'))
        self.assertEqual(["mainland:信息"], self.rules("Other", "<b>信息</b>"))
        self.assertEqual([], self.rules("{{agent}}", "代理"))

    def run_cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = checker.main(args)
        return code, output.getvalue()

    def test_batch_five_violations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.json"
            entries = [
                {"key": str(i), "status": "new", "en": en, "previous_en": None, "previous_zh": None, "zh": zh}
                for i, (en, zh) in enumerate([
                    ("Runtime", "執行階段"), ("Share", "共享"), ("Other", "信息"),
                    ("Other", "中 文"), ("Other", "中,文"), ("Agent", ""),
                ])
            ]
            path.write_text(json.dumps({"en_source": "測試", "entries": entries}), encoding="utf-8")
            code, output = self.run_cli(["--batch", str(path), "--json"])
            result = json.loads(output)
            self.assertEqual(1, code)
            self.assertEqual(5, result["summary"]["checked"])
            self.assertEqual(5, result["summary"]["violations"])
            self.assertEqual(5, len(result["summary"]["by_rule"]))
            code, output = self.run_cli(["--batch", str(path)])
            self.assertIn("共檢查 5 條，發現 5 項違規", output)
            self.assertEqual(5, len([line for line in output.splitlines() if "\t" in line]))
            entries[0]["zh"] = "執行環境"
            path.write_text(json.dumps({"entries": entries[:1]}), encoding="utf-8")
            self.assertEqual(0, self.run_cli(["--batch", str(path)])[0])
            path.write_text('{"entries": [{"zh": 3}]}', encoding="utf-8")
            self.assertEqual(2, self.run_cli(["--batch", str(path), "--json"])[0])

    def test_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            en, zh = [Path(directory) / name for name in ("en.json", "zh.json")]
            en.write_text('{"nested": {"key": "Terminal"}}', encoding="utf-8")
            zh.write_text(json.dumps({"nested": {"key": "終端機"}, "orphan": "信息"}), encoding="utf-8")
            with patch.object(checker, "PACK", zh):
                code, output = self.run_cli(["--pack", "--en", str(en), "--json"])
            self.assertEqual(1, code)
            self.assertEqual({"mainland:信息": 1}, json.loads(output)["summary"]["by_rule"])


if __name__ == "__main__":
    unittest.main()
