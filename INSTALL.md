# Installing vgozalov/skills

This file is for the AI agent doing the install. A person can say "install the skills from https://github.com/vgozalov/skills following its INSTALL.md" and you follow the steps below. Run each command, check its result, and stop to report if a step fails; do not improvise around a failure.

What gets installed:

| Piece | What it is |
| --- | --- |
| `chief` skill and `chief` agent | The orchestrator: `/chief <task>` in any session, or `claude --agent chief`. Delivers a task through Claude subagents and Codex jobs, with a live dashboard and a cost report. |
| `model-routing` | Picks the model and provider for every delegated job, balances the Claude and ChatGPT accounts, checks git state. Ships the hook and the scripts below. |
| `parallel-plans`, `parallel-build`, `parallel-briefs` | Plans whose tasks own their files, a build that runs them in parallel waves with reviews, and briefs for ad-hoc parallel work. |
| `executing-plans`, `requesting-code-review`, `using-git-worktrees`, `finishing-a-development-branch`, `test-driven-development`, `systematic-debugging`, `verification-before-completion` | The skills the build hands off to: inline execution, the final code review, worktree setup, finishing the branch, and the test-first, root-cause and verify-before-claiming disciplines. |
| `wrap-up`, `create-sprint` | Session wrap-up, and a verification sprint from a plan. |

Release: `v1.0.1`. Use the tag in every command below so the skills, the agent and the scripts match.

## 1. Ask the user, once

Ask these together (use your question tool if you have one), and wait for the answers:

1. **Scope:** this project only, or every project on this machine?
2. **Codex:** should ChatGPT models via Codex take jobs too? (Needs the `codex` CLI logged in with ChatGPT.)
3. **Auto-save hooks:** if the project has a Stop hook that auto-commits, may you make it skip while a chief run is active? (Step 5 says whether there is one; ask then if you did not know yet.)

## 2. Check the tools

```bash
git --version && python3 --version && npx --version && claude --version
codex --version   # only if the user wants Codex jobs
gh --version || glab --version   # optional: issue import and pull requests
```

Python must be 3.8 or newer. Missing `git`, `python3`, `npx` or `claude`: stop and tell the user what to install. Missing `codex`: everything routes to Claude; say so. For Codex, the user runs `codex login` themselves.

## 3. Install the skills

Project scope, from the repo root:

```bash
npx -y skills@1.7.2 add vgozalov/skills#v1.0.1 -a claude-code -a codex -y
```

Every project:

```bash
npx -y skills@1.7.2 add vgozalov/skills#v1.0.1 -g -a claude-code -a codex -y
```

If the project lists its skills in `.agents/skills.txt`, add the line `vgozalov/skills#v1.0.1 *` there instead and run `curl -fsSL https://raw.githubusercontent.com/vgozalov/skills/v1.0.1/install.sh | bash` (add `-s -- --global` for every project).

Check: `.claude/skills/chief/SKILL.md` exists (globally: `~/.claude/skills/chief/SKILL.md`). Call that skills folder `<skills>` below.

If another plugin already installs skills named `executing-plans`, `requesting-code-review`, `using-git-worktrees`, `finishing-a-development-branch`, `test-driven-development`, `systematic-debugging` or `verification-before-completion`, tell the user: two skills with one name compete for the same requests, so they should disable the other plugin (`claude plugin list`, then `claude plugin disable <name>`).

**Upgrading from before 1.0.0:** `conduct` became `chief`, `parallel-agent-development` became `parallel-build`, and the `conductor` agent became `chief`. Remove the old skill folders or symlinks named `conduct` and `parallel-agent-development` from `.claude/skills/` and `.agents/skills/` (or the global ones), and the old `conductor.md` agent, after showing the user what you will delete.

## 4. Install the agent

The skills CLI installs skills, not agents, so fetch the agent file:

```bash
mkdir -p .claude/agents && curl -fsSL https://raw.githubusercontent.com/vgozalov/skills/v1.0.1/agents/chief.md -o .claude/agents/chief.md
# every project instead: mkdir -p ~/.claude/agents && curl ... -o ~/.claude/agents/chief.md
```

Check: the file starts with `name: chief`.

## 5. Configure the hooks

```bash
python3 <skills>/model-routing/scripts/configure-hooks.py            # project: .claude/settings.json
python3 <skills>/model-routing/scripts/configure-hooks.py --global   # every project: ~/.claude/settings.json
```

It adds the PreToolUse hook that shows both accounts' usage and the routing pick before every agent spawn and Codex job, keeps every other setting, and does nothing the second time. It prints JSON:

- `usage_hook_added`: true the first time, false when it was already there.
- `auto_save_hooks_unpatched`: Stop hooks in that file that auto-commit and would commit half-finished work during a run. If above 0 and the user agreed in step 1, run it again with `--patch-auto-save`; it puts `[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0; ` in front of each such command. Auto-save hooks in other settings files (`.claude/settings.local.json`, the user's global file) need the same line; show the user the line and the file.

## 6. Tell agents which skill does what

Add this block to the project's `AGENTS.md` (with `CLAUDE.md` symlinked to it, so Claude and Codex read the same rules); for every project, to `~/.claude/CLAUDE.md` instead:

```markdown
## Agent teams

- To orchestrate work across agents ("orchestrate", "orchestrator", "manage agents", "team of agents", "use parallel agents", "/chief"), use the `chief` skill, or start `claude --agent chief`.
- To write a plan whose tasks agents build in parallel: `parallel-plans`. To build an approved plan with agents: `parallel-build`. To split ad-hoc work across agents: `parallel-briefs`.
- Every model or provider choice for a delegated job comes from `model-routing`.

## Skill paths

- plans: docs/plans
- specs: context/specs
- memory: context/memory
- learnings: context/learnings.md
- sprints: sprints
```

Adjust the paths to the repo; skills ask once when a key is missing.

## 7. Verify

```bash
python3 <skills>/model-routing/scripts/check-account-usage.py     # JSON with "pick"; "spawn_hook": "registered" in Claude Code
python3 <skills>/model-routing/scripts/git-check.py --warnings-only
python3 <skills>/chief/scripts/chief-run.py board > /dev/null && echo board ok
```

`check-account-usage.py` may take up to a minute (it reads both accounts without spending a model turn). An `"ask"` pick means an account is unreadable or near its limit; report it, it is not an install failure.

## 8. Report to the user

Say what was installed and where, which hooks were added or patched, whether Codex is on, anything skipped and why, and how to start:

```text
/chief <the task, a file path, or an issue number>      or      claude --agent chief
python3 <skills>/chief/scripts/chief-run.py serve        dashboard on http://127.0.0.1:8765
```

Commit `.agents/skills/`, the `.claude/skills/` links, `skills-lock.json`, `.claude/agents/chief.md`, `.claude/settings.json` and the `AGENTS.md` change only if the user asks; offer it once.
