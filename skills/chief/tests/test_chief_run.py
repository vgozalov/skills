import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "chief-run.py"
PRICES = json.loads((HERE.parent.parent / "model-routing" / "prices.json").read_text())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chief = load(SCRIPT, "chief_run")
codex_job = load(HERE.parent.parent / "model-routing" / "scripts" / "run-codex-job.py", "run_codex_job")


class Workspace(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.repo = root / "repo"
        self.config = root / "claude-config"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        self.projects = self.config / "projects" / "-repo" / "session-1" / "subagents"
        self.projects.mkdir(parents=True)

    def tearDown(self):
        self.folder.cleanup()

    def start(self, text="Add CSV export to the report page.\nClient wants it by Friday.", **kwargs):
        return Path(chief.start_run(str(self.repo), text, **kwargs))

    def transcript(self, name, prompt, messages, done=True, model_alias="sonnet"):
        lines = [{"type": "user", "timestamp": "2026-11-12T10:00:00.000Z", "message": {"role": "user", "content": prompt}}]
        for index, (model, usage) in enumerate(messages):
            message = {"id": f"msg_{name}_{index}", "model": model, "role": "assistant", "usage": usage,
                       "stop_reason": "end_turn" if done and index == len(messages) - 1 else "tool_use",
                       "content": [{"type": "text", "text": f"DONE from {name}"}]}
            # Streaming writes the same message id more than once; only the last copy counts.
            lines.append({"type": "assistant", "timestamp": f"2026-11-12T10:0{index + 1}:00.000Z", "message": dict(message, usage={**usage, "output_tokens": 1})})
            lines.append({"type": "assistant", "timestamp": f"2026-11-12T10:0{index + 1}:30.000Z", "message": message})
        (self.projects / f"agent-{name}.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n")
        (self.projects / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": "general-purpose", "description": f"{name} job", "model": model_alias}))

    def codex_record(self, run, name, **fields):
        agents = run / "agents"
        agents.mkdir(exist_ok=True)
        record = {"provider": "chatgpt", "model": "gpt-6-luna", "effort": "medium", "task": "2", "role": "implement",
                  "label": name, "status": "completed", "started": "2026-11-12T10:00:00Z", "ended": "2026-11-12T10:03:00Z",
                  "usage": {"input": 1_000_000, "cached": 800_000, "output": 100_000, "reasoning": 40_000}}
        record.update(fields)
        (agents / f"codex-{name}.json").write_text(json.dumps(record))

    def board(self):
        return chief.build_board(str(self.repo), config_dir=str(self.config), prices=PRICES, with_git=False)


class StartRunTest(Workspace):
    def test_start_saves_the_task_verbatim_and_hides_runs_from_git(self):
        run = self.start(title="CSV export")
        task = (run / "task.md").read_text()
        self.assertIn("# CSV export", task)
        self.assertIn("Source: chat", task)
        self.assertIn("Add CSV export to the report page.\nClient wants it by Friday.", task)
        state = json.loads((run / "run.json").read_text())
        self.assertEqual(state["phase"], "intake")
        self.assertEqual(state["title"], "CSV export")
        self.assertTrue(run.name.endswith("-csv-export"))
        status = subprocess.run(["git", "status", "--short"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertEqual(status, "")

    def test_the_title_defaults_to_the_first_line(self):
        run = self.start()
        self.assertEqual(json.loads((run / "run.json").read_text())["title"], "Add CSV export to the report page.")

    def test_two_runs_in_the_same_minute_get_distinct_folders(self):
        self.assertNotEqual(self.start(title="Same"), self.start(title="Same"))

    def test_an_empty_task_is_refused(self):
        with self.assertRaises(ValueError):
            self.start(text="   ")

    def test_issue_references_map_to_gh_or_glab(self):
        self.assertEqual(chief.issue_command("123")[:3], ["gh", "issue", "view"])
        self.assertEqual(chief.issue_command("https://gitlab.com/acme/app/-/issues/7")[:3], ["glab", "issue", "view"])
        self.assertEqual(chief.issue_command("https://github.com/acme/app/issues/9")[:3], ["gh", "issue", "view"])


class PhaseTest(Workspace):
    def test_phases_are_recorded_in_order_with_the_plan_path(self):
        run = self.start(title="X")
        chief.set_phase(str(run), "plan")
        chief.set_phase(str(run), "implement", plan="docs/plan.md", workspace=".parallel-build/plan")
        state = chief.load_run(str(run))
        self.assertEqual([entry["phase"] for entry in state["phases"]], ["intake", "plan", "implement"])
        self.assertEqual(state["plan"], "docs/plan.md")
        self.assertEqual(state["workspace"], ".parallel-build/plan")

    def test_an_unknown_phase_is_refused(self):
        run = self.start(title="X")
        with self.assertRaises(ValueError):
            chief.set_phase(str(run), "deploy")

    def test_done_records_the_end_time(self):
        run = self.start(title="X")
        chief.set_phase(str(run), "done")
        self.assertIsNotNone(chief.load_run(str(run))["ended"])


class BoardTest(Workspace):
    def test_claude_and_codex_agents_of_a_run_are_listed_with_separate_costs(self):
        run = self.start(title="CSV export")
        other = self.start(title="Other task")
        self.transcript("a1", f"Run: {run}   Task: 1   Role: implement\nBuild it.", [
            ("claude-sonnet-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0,
                                   "cache_creation_input_tokens": 0}),
        ])
        self.transcript("a2", f"Run: {other}   Task: 1   Role: research\nLook.", [
            ("claude-haiku-5-5", {"input_tokens": 10, "output_tokens": 10}),
        ])
        self.transcript("untagged", "Plain prompt with no run tag", [("claude-haiku-5-5", {"input_tokens": 10, "output_tokens": 10})])
        self.codex_record(run, "build-2")

        board = self.board()
        card = next(item for item in board["runs"] if item["id"] == run.name)
        providers = sorted((agent["provider"], agent["role"], agent["task"]) for agent in card["agents"])
        self.assertEqual(providers, [("chatgpt", "implement", "2"), ("claude", "implement", "1")])
        self.assertEqual({agent["status"] for agent in card["agents"]}, {"done"})
        # Sonnet: 1M input * $2 + 0.1M output * $10 = $3.00
        self.assertAlmostEqual(card["totals"]["claude"]["cost_usd"], 3.0)
        # Luna: 0.2M uncached * $0.10 + 0.8M cached * $0.01 + 0.1M output (reasoning inside) * $0.50 = $0.078
        self.assertAlmostEqual(card["totals"]["chatgpt"]["cost_usd"], 0.078)
        self.assertAlmostEqual(card["totals"]["total_cost_usd"], 3.078)
        self.assertTrue(card["totals"]["estimate"])

    def test_streamed_copies_of_a_message_are_counted_once(self):
        run = self.start(title="X")
        self.transcript("a1", f"Run: {run}   Task: 1   Role: review", [
            ("claude-opus-5-5", {"input_tokens": 0, "output_tokens": 1_000_000}),
        ])
        agent = self.board()["runs"][0]["agents"][0]
        self.assertEqual(agent["tokens"]["output"], 1_000_000)
        self.assertAlmostEqual(agent["cost_usd"], 20.0)
        self.assertEqual(agent["status"], "done")
        self.assertEqual(agent["model"], "claude-opus-5-5")
        self.assertIn("DONE from a1", agent["report"])

    def test_cache_writes_and_reads_use_their_own_prices(self):
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 1_000_000,
                 "cache_creation_input_tokens": 2_000_000,
                 "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 1_000_000}}
        # Sonnet: read 0.10 + 5m write 2.5 + 1h write 4.0
        self.assertAlmostEqual(chief.price_claude("claude-sonnet-5-5", usage, PRICES), 6.6)

    def test_haiku_long_prompts_use_the_long_context_rate(self):
        usage = {"input_tokens": 200_000, "output_tokens": 0}
        self.assertAlmostEqual(chief.price_claude("claude-haiku-5-5", usage, PRICES), 0.1)

    def test_a_resumed_codex_thread_is_counted_once(self):
        run = self.start(title="X")
        self.codex_record(run, "fix-1", thread_id="t1", ended="2026-11-12T10:03:00Z")
        self.codex_record(run, "fix-1-resume", thread_id="t1", ended="2026-11-12T10:09:00Z", resumed=True,
                          usage={"input": 2_000_000, "cached": 1_600_000, "output": 200_000, "reasoning": 0})
        card = self.board()["runs"][0]
        superseded = [agent for agent in card["agents"] if agent.get("superseded")]
        self.assertEqual(len(superseded), 1)
        self.assertAlmostEqual(card["totals"]["chatgpt"]["cost_usd"], 0.156)

    def test_unknown_models_are_unpriced_not_guessed(self):
        run = self.start(title="X")
        self.codex_record(run, "unknown", model="gpt-5-legacy-unknown")
        totals = self.board()["runs"][0]["totals"]
        self.assertEqual(totals["chatgpt"]["unpriced"], 1)
        self.assertEqual(totals["chatgpt"]["cost_usd"], 0)

    def test_a_running_codex_job_whose_process_is_gone_shows_stopped(self):
        run = self.start(title="X")
        self.codex_record(run, "ghost", status="running", pid=99999999, ended=None, usage=None)
        self.assertEqual(self.board()["runs"][0]["agents"][0]["status"], "stopped")

    def test_board_totals_add_every_run(self):
        first, second = self.start(title="A"), self.start(title="B")
        self.codex_record(first, "one")
        self.codex_record(second, "two")
        self.assertAlmostEqual(self.board()["totals"]["chatgpt"]["cost_usd"], 0.156)


class SummaryTest(Workspace):
    def test_the_summary_keeps_providers_apart_and_labels_the_total(self):
        run = self.start(title="CSV export")
        self.transcript("a1", f"Run: {run}   Task: 1   Role: implement", [
            ("claude-sonnet-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000}),
        ])
        self.codex_record(run, "build-2")
        text = chief.summary_markdown(str(self.repo), str(run), config_dir=str(self.config), prices=PRICES)
        self.assertIn("| claude | claude-sonnet-5-5 |", text)
        self.assertIn("| chatgpt | gpt-6-luna |", text)
        self.assertIn("Claude subtotal: $3.00", text)
        self.assertIn("ChatGPT subtotal: $0.08", text)
        self.assertIn("API-equivalent estimate", text)


class MoneyTest(unittest.TestCase):
    def test_fractions_of_a_cent_are_not_shown_as_zero(self):
        self.assertEqual(chief.money(0.0004), "<$0.01")
        self.assertEqual(chief.money(0), "$0.00")
        self.assertEqual(chief.money(None), "unpriced")


class FileAccessTest(Workspace):
    def test_only_named_run_files_can_be_read(self):
        run = self.start(title="X")
        self.assertEqual(chief.resolve_file(str(self.repo), run.name, "task"), str(run / "task.md"))
        self.assertIsNone(chief.resolve_file(str(self.repo), run.name, "../../etc/passwd"))
        self.assertIsNone(chief.resolve_file(str(self.repo), "../x", "task"))


class CodexRecordTest(unittest.TestCase):
    def test_the_run_tag_is_read_from_the_brief(self):
        tag = codex_job.parse_run_tag("Run: /repo/.chief/runs/20261112-1000-x   Task: 3   Role: fix\nRepo: /repo")
        self.assertEqual(tag, {"run": "/repo/.chief/runs/20261112-1000-x", "task": "3", "role": "fix"})

    def test_a_brief_without_a_tag_has_none(self):
        self.assertIsNone(codex_job.parse_run_tag("Repo: /repo\nFix it."))

    def test_records_are_written_into_the_run_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            path = codex_job.record_path(folder, "20261112-100000", "build")
            codex_job.write_record(path, {"status": "running"})
            codex_job.write_record(path, {"status": "completed"})
            self.assertEqual(json.loads(Path(path).read_text())["status"], "completed")
            self.assertTrue(path.startswith(os.path.join(folder, "agents")))


if __name__ == "__main__":
    unittest.main()
