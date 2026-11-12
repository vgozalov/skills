# Using Codex for ChatGPT models

`scripts/run-codex-job.py` runs `codex exec` on the user's ChatGPT account and prints one compact JSON object instead of a transcript. Run it from the repo root, in the background (Bash `run_in_background: true`), with the brief on stdin through a quoted heredoc:

```bash
python3 <skill folder>/scripts/run-codex-job.py \
  --model gpt-6-luna --effort medium --label task-2 <<'BRIEF'
<the brief>
BRIEF
```

When notified, `cat` the background output file.

Jobs run outside the sandbox (`--sandbox danger-full-access`, the default), so a Codex worker can do what a Claude agent does: run the test suite, reach the network and local containers, and work in a git worktree (add `--cd <worktree>`). Pass `--sandbox workspace-write` or `read-only` only to fence a job on purpose. A fenced job in a worktree cannot commit, because the worktree's git metadata lives in the main checkout's `.git/worktrees/`, outside the writable root, and cannot run tests that write under a linked `node_modules`; commit its edits yourself by explicit path after checking `git status`.

| Role                                                         | `--effort`                                           |
| ------------------------------------------------------------ | ---------------------------------------------------- |
| Implementer, fixer, researcher, per-task reviewer, fix check | `medium`                                             |
| Plan writer, plan reviewer, whole-branch reviewer            | `high`; Astra `medium` (SKILL.md, tier 3 on ChatGPT) |

Tier 3 runs Astra at `medium` whatever the role says; its fallback is Sol at `high`.

Always pass `--effort`, so the role decides the effort rather than whatever `model_reasoning_effort` the Codex config sets.

**Resume** with `--resume <thread_id>` (same model, follow-up brief on stdin) only when the thread's input total is under about 200k tokens; a resumed thread re-sends its whole history on every step. Otherwise launch a fresh job with the findings and `git diff -- <files>`. On a resumed thread `usage` is the running total; record the difference.

**Output:** `status`, `thread_id`, `usage` (input, cached, output, reasoning), `steps` (completed items: commands, file reads, messages) and `largest_item_chars` (the biggest single output carried in context), `last_message`; plus `exit_code`, `error` and `log` when it did not complete. A high `steps` or `largest_item_chars` points at exploration or uncapped test output: tighten the next brief.

- `completed`: read `last_message`.
- `rate_limited`: relaunch at the same tier on Claude.
- `failed`: an unsupported slug, sandbox or auth error is an environment problem, not a reason to change tier. If `error` does not explain it, a tier-1 agent reads `log`; you do not.

**The script also** disables Codex's own sub-agents (so the ceiling holds) and uses the repo, or `--cd`, as the working root.

**Briefs:** Codex loads the repo's `AGENTS.md` automatically, so do not paste project rules that live there; add "Do not commit, push or create branches" unless that is the job. Codex cannot message you mid-job; `last_message` is its whole answer.

**Seeing the jobs:** they are saved Codex sessions. In a terminal, `codex resume --all --include-non-interactive` lists them (non-interactive `exec` sessions are hidden by default) and opens one to read or continue.
