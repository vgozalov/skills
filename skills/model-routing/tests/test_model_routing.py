import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


usage = load_script("check-account-usage")
hook = load_script("usage-before-spawn")
codex_job = load_script("run-codex-job")


class PickProviderTest(unittest.TestCase):
    def pick(self, orchestrator, **readings):
        return usage.pick_provider(readings, orchestrator)[0]

    def test_orchestrator_provider_is_preferred_below_the_switch_point(self):
        self.assertEqual(self.pick("claude", claude={"5h": 43, "week": 58}, chatgpt={"5h": 0, "week": 64}), "claude")

    def test_work_moves_off_the_orchestrator_provider_at_60_percent_of_its_5h_window(self):
        self.assertEqual(self.pick("claude", claude={"5h": 72, "week": 62}, chatgpt={"5h": 0, "week": 64}), "chatgpt")
        self.assertEqual(self.pick("claude", claude={"5h": 60, "week": 10}, chatgpt={"5h": 0, "week": 10}), "chatgpt")

    def test_a_chatgpt_orchestrator_moves_work_to_claude_at_60_percent(self):
        self.assertEqual(self.pick("chatgpt", claude={"5h": 20, "week": 30}, chatgpt={"5h": 65, "week": 40}), "claude")
        self.assertEqual(self.pick("chatgpt", claude={"5h": 20, "week": 30}, chatgpt={"5h": 59, "week": 40}), "chatgpt")

    def test_when_both_are_past_60_the_orchestrator_reserve_is_kept(self):
        self.assertEqual(self.pick("claude", claude={"5h": 70, "week": 50}, chatgpt={"5h": 75, "week": 50}), "chatgpt")

    def test_a_provider_near_its_weekly_limit_is_skipped_while_another_has_room(self):
        self.assertEqual(self.pick("claude", claude={"5h": 7, "week": 99}, chatgpt={"5h": 21, "week": 34}), "chatgpt")

    def test_the_orchestrator_takes_the_work_when_no_other_provider_has_room(self):
        self.assertEqual(self.pick("claude", claude={"5h": 70, "week": 50}, chatgpt={"5h": 95, "week": 50}), "claude")
        self.assertEqual(self.pick("claude", claude={"5h": 70, "week": 50}, chatgpt={"error": "no answer"}), "claude")

    def test_a_blocked_account_has_no_room(self):
        blocked = {"5h": 5, "week": 10, "blocked": True}
        self.assertEqual(self.pick("claude", claude={"5h": 70, "week": 50}, chatgpt=blocked), "claude")

    def test_unreadable_orchestrator_usage_means_ask(self):
        self.assertEqual(self.pick("claude", claude={"error": "x"}, chatgpt={"5h": 0, "week": 10}), "ask")

    def test_every_provider_near_its_limit_means_ask(self):
        self.assertEqual(self.pick("claude", claude={"5h": 95, "week": 50}, chatgpt={"5h": 92, "week": 50}), "ask")

    def test_a_orchestrator_without_a_usage_reader_balances_on_the_lower_5h_window(self):
        self.assertEqual(self.pick("gemini", claude={"5h": 40, "week": 50}, chatgpt={"5h": 10, "week": 60}), "chatgpt")

    def test_the_reason_names_the_numbers_behind_the_pick(self):
        readings = {"claude": {"5h": 72, "week": 62}, "chatgpt": {"5h": 0, "week": 64}}
        why = usage.pick_provider(readings, "claude")[1]
        self.assertIn("72%", why)
        self.assertIn("60%", why)


class DetectOrchestratorTest(unittest.TestCase):
    def test_claude_code_is_detected(self):
        self.assertEqual(usage.detect_orchestrator({"CLAUDECODE": "1"}), "claude")

    def test_an_unknown_environment_gives_none(self):
        self.assertIsNone(usage.detect_orchestrator({}))


class ReadUsageCacheTest(unittest.TestCase):
    def read_twice(self, max_age):
        calls = []

        def reader():
            calls.append(1)
            return {"5h": 1.0, "week": 2.0}

        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "usage.json")
            first = usage.read_usage(max_age, cache_path=path, readers={"claude": reader})
            second = usage.read_usage(max_age, cache_path=path, readers={"claude": reader})
        return first, second, len(calls)

    def test_a_fresh_cached_reading_is_reused(self):
        first, second, reads = self.read_twice(max_age=120)
        self.assertEqual(first, {"claude": {"5h": 1.0, "week": 2.0}})
        self.assertEqual(second, first)
        self.assertEqual(reads, 1)

    def test_max_age_zero_reads_again(self):
        self.assertEqual(self.read_twice(max_age=0)[2], 2)


class DescribeSpawnTest(unittest.TestCase):
    def test_an_agent_spawn_runs_on_claude(self):
        spawn = hook.describe_spawn({"tool_name": "Agent", "tool_input": {"model": "haiku"}})
        self.assertEqual(spawn, ("claude", "haiku"))

    def test_an_agent_without_a_model_uses_the_default(self):
        self.assertEqual(hook.describe_spawn({"tool_name": "Agent", "tool_input": {}}), ("claude", "default"))

    def test_a_codex_job_runs_on_chatgpt(self):
        command = "python3 .claude/skills/model-routing/scripts/run-codex-job.py --model gpt-6-luna --effort low <<'BRIEF'\nx\nBRIEF"
        spawn = hook.describe_spawn({"tool_name": "Bash", "tool_input": {"command": command}})
        self.assertEqual(spawn, ("chatgpt", "gpt-6-luna"))

    def test_other_bash_commands_are_not_spawns(self):
        self.assertIsNone(hook.describe_spawn({"tool_name": "Bash", "tool_input": {"command": "git status"}}))

    def bash_spawn(self, command):
        return hook.describe_spawn({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_commands_that_only_mention_the_job_script_are_not_spawns(self):
        for command in (
            'cp "$NEW/scripts/run-codex-job.py" skills/model-routing/scripts/',
            "grep -n sandbox scripts/run-codex-job.py",
            "python3 -c \"import ast; ast.parse(open('scripts/run-codex-job.py').read())\"",
        ):
            self.assertIsNone(self.bash_spawn(command), command)

    def test_a_quoted_job_script_path_with_spaces_is_a_spawn(self):
        command = 'cd repo && python3 -B "/Users/me/My Code/model-routing/scripts/run-codex-job.py" --model gpt-6.1-sol'
        self.assertEqual(self.bash_spawn(command), ("chatgpt", "gpt-6.1-sol"))

    def test_running_the_job_script_directly_is_a_spawn(self):
        self.assertEqual(self.bash_spawn("./scripts/run-codex-job.py --model gpt-6-astra"), ("chatgpt", "gpt-6-astra"))


class UsageNoteTest(unittest.TestCase):
    def test_the_note_reports_both_accounts_the_pick_and_the_spawn(self):
        readings = {"claude": {"5h": 72.0, "week": 62.0}, "chatgpt": {"5h": 0.0, "week": 64.0}}
        note = hook.usage_note(readings, "chatgpt", "the reason", ("claude", "sonnet"))
        self.assertIn("claude 5h 72% / week 62%", note)
        self.assertIn("chatgpt 5h 0% / week 64%", note)
        self.assertIn("pick chatgpt (the reason)", note)
        self.assertIn("claude (sonnet)", note)

    def test_an_unreadable_account_is_named(self):
        readings = {"claude": {"5h": 10.0, "week": 20.0}, "chatgpt": {"error": "no answer"}}
        self.assertIn("chatgpt unreadable", hook.usage_note(readings, "claude", "r", ("claude", "haiku")))

    def test_the_hook_output_adds_context_and_never_decides_permission(self):
        output = hook.hook_output("the note")["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["additionalContext"], "the note")
        self.assertNotIn("permissionDecision", output)


class CodexCommandTest(unittest.TestCase):
    def command(self, *argv):
        return codex_job.build_command(codex_job.parse_args(["--model", "gpt-6-luna", *argv]), "/tmp/last.txt")

    def test_jobs_run_outside_the_sandbox_by_default(self):
        command = self.command()
        self.assertEqual(command[command.index("-s") + 1], "danger-full-access")

    def test_resumed_jobs_keep_the_same_access(self):
        self.assertIn('sandbox_mode="danger-full-access"', self.command("--resume", "thread-1"))

    def test_a_sandbox_can_still_be_requested(self):
        command = self.command("--sandbox", "read-only")
        self.assertEqual(command[command.index("-s") + 1], "read-only")


if __name__ == "__main__":
    unittest.main()
