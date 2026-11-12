import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("configure_hooks", SCRIPTS / "configure-hooks.py")
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


class ConfigureHooksTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.settings = Path(self.folder.name) / ".claude" / "settings.json"

    def tearDown(self):
        self.folder.cleanup()

    def write(self, data):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps(data))

    def read(self):
        return json.loads(self.settings.read_text())

    def test_the_usage_hook_is_added_once_and_other_settings_are_kept(self):
        self.write({"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]}})
        first = hooks.configure(str(self.settings), "/x/usage-before-spawn.py")
        second = hooks.configure(str(self.settings), "/x/usage-before-spawn.py")
        data = self.read()
        self.assertEqual(data["model"], "opus")
        self.assertEqual(len(data["hooks"]["Stop"]), 1)
        commands = [h["command"] for group in data["hooks"]["PreToolUse"] for h in group["hooks"]]
        self.assertEqual(len(commands), 2)
        self.assertTrue(all("usage-before-spawn.py" in command for command in commands))
        self.assertTrue(first["usage_hook_added"])
        self.assertFalse(second["usage_hook_added"])

    def test_a_missing_settings_file_is_created(self):
        result = hooks.configure(str(self.settings), "/x/usage-before-spawn.py")
        self.assertTrue(self.settings.exists())
        self.assertTrue(result["usage_hook_added"])

    def test_auto_save_hooks_are_patched_only_when_asked(self):
        self.write({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "git add -A && git commit -m save"}]}]}})
        report = hooks.configure(str(self.settings), "/x/usage-before-spawn.py")
        self.assertEqual(report["auto_save_hooks_unpatched"], 1)
        self.assertNotIn("chief-run", self.read()["hooks"]["Stop"][0]["hooks"][0]["command"])
        report = hooks.configure(str(self.settings), "/x/usage-before-spawn.py", patch_auto_save=True)
        command = self.read()["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith('[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0; '))
        self.assertEqual(report["auto_save_hooks_patched"], 1)
        hooks.configure(str(self.settings), "/x/usage-before-spawn.py", patch_auto_save=True)
        self.assertEqual(self.read()["hooks"]["Stop"][0]["hooks"][0]["command"].count("chief-run"), 1)

    def test_dry_run_writes_nothing(self):
        result = hooks.configure(str(self.settings), "/x/usage-before-spawn.py", dry_run=True)
        self.assertFalse(self.settings.exists())
        self.assertTrue(result["usage_hook_added"])


if __name__ == "__main__":
    unittest.main()
