# Changelog

## 1.0.1 (2026-11-12)

- Fixed: `model-routing`'s `description` held an unquoted `: `, which is invalid YAML, so `npx skills add` and `npx skills update` refused the skill. The text is unchanged apart from a dash in place of that colon.
- Tests: the frontmatter check now fails an unquoted description containing `: ` or ` #`.

## 1.0.0 (2026-11-12)

First stable release. Every skill and the agent are self-contained: nothing here needs another plugin.

### The chief: one orchestrator for agent teams

- New `chief` skill and `chief` agent (were `conduct` and `conductor`). Start a run with `/chief <task>` in any session or `claude --agent chief`; it also answers to "orchestrate", "orchestrator", "manage agents", "team of agents" and "use parallel agents". The agent loads the skill, so the two never drift apart.
- Tasks come from anywhere: a description in chat, a file from a client or manager, or a GitHub or GitLab issue. Each run gets a folder under `.chief/runs/` (ignored by git) with the request saved verbatim.
- Every brief starts with a run tag, so Claude subagents and Codex jobs are found without bookkeeping: `chief-run.py` reads Claude Code's transcripts and the records `run-codex-job.py` now writes.
- Live dashboard (`chief-run.py serve`): runs in columns by phase, a chip per agent on either provider, both accounts' 5-hour and weekly use with the 60% switch line, git warnings, and per-run detail with each agent's reply and the run's task, plan, progress and handoff.
- Cost report (`chief-run.py summary`): one row per agent, a Claude subtotal, a ChatGPT subtotal and their sum labelled as an API-equivalent estimate, plus each account's window use from start to end. Prices from the official Anthropic and OpenAI pages in `model-routing/prices.json`, including Haiku 5.5 long-context rates.
- Pipeline adds a gate (the project's full checks before any reviewer runs) and a finish step (pull request, local merge, keep or discard, only on the user's answer).

### Routing and git hygiene

- The usage check runs at intake, each new request, each phase start, before each wave and after a usage-limit stop, so one account is no longer drained while the other sits idle. It reports whether the pre-spawn hook is registered.
- New `git-check.py`: auto-committing Stop hooks, skip-worktree files that differ from HEAD, stray `*-E`/`*.orig`/`*.bak` files and auto-save commits, with a `chief-run` marker that auto-save hooks can respect. Briefs forbid `sed -i` and ask workers to name stray files.
- New `configure-hooks.py` registers the usage hook and, with permission, makes auto-save hooks skip chief runs.

### Renames and independence

- `parallel-agent-development` is now `parallel-build`, rebased on the current upstream text word for word (its `references/` files, `plan-repo` and `-C DIR` support in the scripts), with our parallel waves, ownership checks, verification budget, pause and resume, and run tag kept as separate sections. `parallel-plans` is likewise the current upstream text plus the parallel layout, ownership and final verification task. Workspaces live under `.parallel-build/`.
- New in this repo, copied word for word with only names changed: `executing-plans`, `requesting-code-review`, `using-git-worktrees`, `finishing-a-development-branch`, `test-driven-development`, `systematic-debugging` and `verification-before-completion`, the skills the build hands off to. Nothing here needs another plugin.
- `parallel-plans` and `parallel-build` have descriptions of their own, so "parallel agents" requests reach them instead of similarly described skills from other plugins.
- `check-account-usage.py --conductor` is now `--orchestrator` (the old flag still works).

### Install

- New [INSTALL.md](./INSTALL.md): point any agent at it to install the skills, the agent and the hooks.
