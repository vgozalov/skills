import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


git_check = load_script("git-check")
usage = load_script("check-account-usage")

GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


class RepoTestCase(unittest.TestCase):
    """A throwaway repo on branch `feature`, branched from `main` after one commit."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name) / "repo"
        self.home = Path(self.folder.name) / "home"
        self.repo.mkdir()
        self.home.mkdir()
        self.git("init", "-q", "-b", "main")
        self.write("src/app.js", "export const url = 'https://api.example.com';\n")
        self.commit("feat: initial")
        self.git("checkout", "-q", "-b", "feature")

    def tearDown(self):
        self.folder.cleanup()

    def git(self, *args):
        return subprocess.run(GIT + list(args), cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def write(self, relative, text, root=None):
        path = (root or self.repo) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def commit(self, subject):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def report(self):
        return git_check.report(str(self.repo), base="main", home=str(self.home))


class AutoSaveCommitsTest(RepoTestCase):
    def test_generic_checkpoint_commits_on_the_branch_are_listed(self):
        self.write("src/a.js", "1\n")
        self.commit("chore: auto-save session checkpoint")
        self.write("src/b.js", "2\n")
        self.commit("feat(log): show carried bit depth")
        self.write("src/c.js", "3\n")
        self.commit("WIP")
        subjects = [commit["subject"] for commit in self.report()["auto_save_commits"]]
        self.assertEqual(subjects, ["WIP", "chore: auto-save session checkpoint"])

    def test_commits_before_the_base_are_not_listed(self):
        self.git("checkout", "-q", "main")
        self.write("src/a.js", "1\n")
        self.commit("chore: auto-save session checkpoint")
        self.git("checkout", "-q", "-b", "other")
        self.assertEqual(self.report()["auto_save_commits"], [])


class SkipWorktreeTest(RepoTestCase):
    def test_a_skip_worktree_file_that_differs_from_head_is_flagged(self):
        self.git("update-index", "--skip-worktree", "src/app.js")
        self.write("src/app.js", "export const url = 'http://localhost:8080';\n")
        result = self.report()
        self.assertEqual(result["skip_worktree"], [{"path": "src/app.js", "flag": "skip-worktree", "differs_from_head": True}])
        self.assertTrue(any("src/app.js" in warning for warning in result["warnings"]))

    def test_an_unchanged_skip_worktree_file_is_listed_without_a_warning(self):
        self.git("update-index", "--skip-worktree", "src/app.js")
        result = self.report()
        self.assertEqual(result["skip_worktree"][0]["differs_from_head"], False)
        self.assertFalse(any("src/app.js" in warning for warning in result["warnings"]))


class StrayFilesTest(RepoTestCase):
    def test_untracked_and_newly_committed_backup_files_are_flagged(self):
        self.write("src/EditPanel.test.jsx-E", "backup\n")
        self.commit("chore: auto-save session checkpoint")
        self.write("src/app.js.orig", "backup\n")
        self.write("src/notes.bak", "backup\n")
        stray = self.report()["stray_files"]
        self.assertIn({"path": "src/EditPanel.test.jsx-E", "tracked": True}, stray)
        self.assertIn({"path": "src/app.js.orig", "tracked": False}, stray)
        self.assertIn({"path": "src/notes.bak", "tracked": False}, stray)

    def test_ordinary_files_are_not_stray(self):
        self.write("src/new-E.js", "fine\n")
        self.write("src/feature.js", "fine\n")
        self.assertEqual(self.report()["stray_files"], [])


class AutoCommitHookTest(RepoTestCase):
    def settings(self, command, root=None, name="settings.json"):
        hooks = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": command}]}]}}
        self.write(f".claude/{name}", json.dumps(hooks), root=root)

    def test_a_stop_hook_that_commits_is_found_in_project_settings(self):
        self.settings("git add -A && git commit -m 'chore: auto-save session checkpoint'")
        hooks = self.report()["auto_commit_hooks"]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["settings"], ".claude/settings.json")
        self.assertFalse(hooks[0]["honors_run_marker"])

    def test_a_hook_script_that_commits_is_found_through_its_path(self):
        self.write(".claude/hooks/auto-save.sh", "#!/bin/sh\ngit add -A\ngit commit -m checkpoint\n")
        self.settings('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/auto-save.sh"', name="settings.local.json")
        hooks = self.report()["auto_commit_hooks"]
        self.assertEqual([hook["settings"] for hook in hooks], [".claude/settings.local.json"])

    def test_user_settings_are_checked(self):
        self.settings("git commit -am save", root=self.home)
        self.assertEqual([hook["settings"] for hook in self.report()["auto_commit_hooks"]], ["~/.claude/settings.json"])

    def test_a_hook_that_checks_the_run_marker_honors_it(self):
        self.settings('[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0; git add -A && git commit -m save')
        result = self.report()
        self.assertTrue(result["auto_commit_hooks"][0]["honors_run_marker"])
        self.assertFalse(any("Stop hook" in warning for warning in result["warnings"]))

    def test_a_hook_that_ignores_the_marker_is_a_warning(self):
        self.settings("git add -A && git commit -m save")
        self.assertTrue(any("Stop hook" in warning for warning in self.report()["warnings"]))

    def test_hooks_that_do_not_commit_are_ignored(self):
        self.settings("say done")
        self.assertEqual(self.report()["auto_commit_hooks"], [])


class RunMarkerTest(RepoTestCase):
    def test_start_and_end_toggle_a_marker_inside_the_git_dir(self):
        git_check.set_run_marker(str(self.repo), True)
        marker = Path(self.git("rev-parse", "--path-format=absolute", "--git-path", "chief-run").strip())
        self.assertTrue(marker.exists())
        self.assertTrue(self.report()["run_marker"])
        self.assertEqual(self.git("status", "--short"), "")
        git_check.set_run_marker(str(self.repo), False)
        self.assertFalse(marker.exists())
        self.assertFalse(self.report()["run_marker"])


class BranchStateTest(RepoTestCase):
    def test_the_branch_and_missing_upstream_are_reported(self):
        result = self.report()
        self.assertEqual(result["branch"], "feature")
        self.assertIsNone(result["upstream"])
        self.assertEqual(result["base"], "main")

    def test_a_clean_branch_has_no_warnings(self):
        self.assertEqual(self.report()["warnings"], [])


class SpawnHookTest(unittest.TestCase):
    def test_the_usage_hook_is_found_in_project_or_user_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            project, home = Path(folder) / "p", Path(folder) / "h"
            (project / ".claude").mkdir(parents=True)
            (home / ".claude").mkdir(parents=True)
            self.assertFalse(usage.spawn_hook_registered(str(project), str(home)))
            (home / ".claude" / "settings.json").write_text('{"hooks": {"PreToolUse": [{"hooks": [{"command": "python3 usage-before-spawn.py"}]}]}}')
            self.assertTrue(usage.spawn_hook_registered(str(project), str(home)))


if __name__ == "__main__":
    unittest.main()
