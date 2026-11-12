<div align="center">

<img alt="skills for Claude Code and Codex. The chief, a conductor robot on its podium, leads an orchestra of brass clockwork robots, each reading from its own music stand under its own lamp: every agent owns its part." src="./assets/banner.svg" width="100%">

<br>

Agent skills for running coding agents in parallel without collisions, writing plans that say who owns which file, and closing sessions cleanly.

<br>

[![tests](https://img.shields.io/github/actions/workflow/status/vgozalov/skills/test.yml?branch=main&style=flat-square&label=tests&labelColor=17110C)](https://github.com/vgozalov/skills/actions/workflows/test.yml)
[![license](https://img.shields.io/github/license/vgozalov/skills?style=flat-square&labelColor=17110C&color=B88A34)](./LICENSE)
[![agents](https://img.shields.io/badge/agents-Claude%20Code%20%2B%20Codex-D4703C?style=flat-square&labelColor=17110C)](#install)
[![bash](https://img.shields.io/badge/bash-3.2%20to%205-E4B04A?style=flat-square&labelColor=17110C)](#development)

<a href="#install"><b>Install</b></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#the-skills"><b>Skills</b></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#parallel-waves"><b>Parallel waves</b></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#why-this-repo-exists"><b>Why</b></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#how-installing-works"><b>How it works</b></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#faq"><b>FAQ</b></a>

</div>

<br>

Every skill here is a plain `SKILL.md` folder with a name of its own, so it installs next to anything else you use and replaces nothing. The [`skills`](https://www.npmjs.com/package/skills) CLI puts one copy where Codex reads it and a symlink where Claude Code reads it.

## Install

**Let your agent do it.** Tell Claude Code or Codex: *"Install the skills from https://github.com/vgozalov/skills following its INSTALL.md."* [INSTALL.md](./INSTALL.md) walks the agent through the skills, the `chief` agent, the usage hook, auto-save hooks, the `AGENTS.md` block and a final check, asking you only what it must.

Or by hand; none of these need a clone.

### Just these skills

```bash
npx skills@latest add vgozalov/skills -a claude-code -a codex
```

Swap in any agent the `skills` CLI supports (`cursor`, `opencode`, `windsurf`, `amp`, and more), or omit `-a` to choose interactively. `wrap-up`, `create-sprint` and `parallel-briefs` work on their own. `parallel-plans` and `parallel-build` work as a pair and hand off only to skills in this repo (`using-git-worktrees`, `requesting-code-review`, `finishing-a-development-branch`, `executing-plans`, and through them `test-driven-development`, `systematic-debugging` and `verification-before-completion`), so install them together. `chief` uses all of them plus `model-routing`.

### A whole repo from a manifest

For repos that pull skills from several sources, list them in `.agents/skills.txt` and let `install.sh` install them in the right order:

```
# source                  skills ("*" = all)
anthropics/skills         frontend-design webapp-testing
vgozalov/skills           *
```

Then, from the repo root, run the script straight from GitHub (add `-s -- --dry-run` after `bash` to preview), or from a clone with `<clone>/install.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/vgozalov/skills/main/install.sh | bash
```

It installs every line for Claude Code and Codex, installs `vgozalov/skills` last whatever its position in the file, pins the CLI to `skills@1.7.2`, and turns off the CLI's telemetry. [More in how installing works](#how-installing-works).

<details>
<summary><b>Then add the instructions block</b> to <code>AGENTS.md</code> (with <code>CLAUDE.md</code> symlinked to it)</summary>
<br>

```markdown
## Skills

Skills live in `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex).
Before any task, including questions, check whether a skill applies. If one
plausibly does, load it and follow it.

## Skill paths

- specs: context/specs
- plans: docs/plans
- memory: context/memory
- learnings: context/learnings.md
- sprints: sprints
```

Adjust the paths to your repo. `wrap-up` and `create-sprint` read them, and ask once when a key is missing.

</details>

<details>
<summary><b>Commit what was installed</b></summary>
<br>

Commit `.agents/skills/`, the `.claude/skills/` symlinks, `skills-lock.json` and, if you use one, `.agents/skills.txt`. Teammates and CI then get exactly the same skills without installing anything.

</details>

<details>
<summary><b>Update</b></summary>
<br>

```bash
npx skills@1.7.2 update -p -y    # this repo
npx skills@1.7.2 update -g -y    # global skills
```

`update` re-fetches changed skills, keeps pinned tags, and keeps each skill tied to its source, so these skills keep updating from this repo.

</details>

<details>
<summary><b>Global document skills</b>, available in every repo</summary>
<br>

```bash
npx skills@latest add anthropics/skills -g -s docx pdf xlsx pptx doc-coauthoring skill-creator -a claude-code -a codex -y
```

or the manifest version, which installs [`global.txt`](./global.txt): those six plus `claude-md-improver` and `claude-automation-recommender`.

```bash
curl -fsSL https://raw.githubusercontent.com/vgozalov/skills/main/install.sh | bash -s -- --global
```

</details>

## The skills

| Skill                                                                                                                                                          | What it does                                                                                                                                                                                         |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <img src="./assets/marker-chief.svg" width="44" alt=""><br>[**chief**](./skills/chief/SKILL.md) | The orchestrator pipeline, as `/chief <task>` in any session or loaded by the `chief` agent. A task can come from chat, a file or an issue; each run gets a folder, a live dashboard of every Claude and Codex agent on it, and a cost summary per provider. |
| <img src="./assets/marker-model-routing.svg" width="44" alt=""><br>[**model-routing**](./skills/model-routing/SKILL.md) | Picks the model for each delegated job across Claude and ChatGPT (Codex): the cheapest tier that can do it, never above the orchestrator's own model. Jobs stay on the orchestrator's own provider until it has used 60% of its 5-hour window, then move to the other, so the orchestrator never runs dry mid-session. Ships usage, Codex-launch and pre-spawn hook scripts. |
| <img src="./assets/marker-parallel-plans.svg" width="44" alt=""><br>[**parallel-plans**](./skills/parallel-plans/SKILL.md)                                     | Turns a spec into a task-by-task plan. Each task declares the files it **owns**, and the plan lists the files frozen while tasks run in parallel.                                                    |
| <img src="./assets/marker-parallel-build.svg" width="44" alt=""><br>[**parallel-build**](./skills/parallel-build/SKILL.md) | Runs a plan through implementer and reviewer subagents. Tasks that touch different files run **in parallel waves** in one worktree, and `ownership-check` rejects any commit outside a task's files. |
| <img src="./assets/marker-parallel-briefs.svg" width="44" alt=""><br>[**parallel-briefs**](./skills/parallel-briefs/SKILL.md)                                  | Splits work across several agents outside a plan. Each gets a brief: your files, do not touch, read first, and what to do when shared code is missing.                                               |
| <img src="./assets/marker-wrap-up.svg" width="44" alt=""><br>[**wrap-up**](./skills/wrap-up/SKILL.md)                                                          | Ends a session: feedback, learnings, the day's memory file, a one-line "Last Session" pointer, and the docs commit.                                                                                  |
| <img src="./assets/marker-create-sprint.svg" width="44" alt=""><br>[**create-sprint**](./skills/create-sprint/SKILL.md)                                        | Turns a written plan into a verification sprint, a `prod.json` acceptance harness, from its bundled example.                                                                                         |

The build also hands off to these:

- [**executing-plans**](./skills/executing-plans/SKILL.md): Runs a plan inline in one session, task by task, when you choose that over agents at the plan's handoff.
- [**requesting-code-review**](./skills/requesting-code-review/SKILL.md): The code-reviewer prompt every whole-branch review uses: strengths, graded findings, what it set aside, and a ready-to-merge verdict.
- [**using-git-worktrees**](./skills/using-git-worktrees/SKILL.md): Sets up an isolated worktree: detects existing isolation, prefers the harness's own tool, checks the folder is ignored, takes a baseline.
- [**finishing-a-development-branch**](./skills/finishing-a-development-branch/SKILL.md): Ends a branch: verifies the tests, confirms the base, offers merge, pull request or keep, and cleans up only what it created.
- [**test-driven-development**](./skills/test-driven-development/SKILL.md), [**systematic-debugging**](./skills/systematic-debugging/SKILL.md), [**verification-before-completion**](./skills/verification-before-completion/SKILL.md): The disciplines the build and inline execution hand off to: test first, find the root cause before fixing, and evidence before any claim of done.

## The chief agent

[`agents/chief.md`](./agents/chief.md) is a Claude Code agent that delivers a feature through subagents and Codex jobs and never codes itself: research, plan, plan review, your approval, parallel build, whole-branch review, report with token costs. Its pipeline lives in the `chief` skill; it routes every job with `model-routing`, plans with `parallel-plans`, and builds with `parallel-briefs` or `parallel-build`, so install those skills first.

The `skills` CLI installs skills, not agents, so copy the agent yourself:

```bash
mkdir -p ~/.claude/agents && cp agents/chief.md ~/.claude/agents/   # every project
# or: mkdir -p .claude/agents && cp agents/chief.md .claude/agents/ # one project
claude --agent chief        # tool limits enforced by the agent file
# or, in any session: /chief <the task, a file path, or an issue number>
```

It defaults to Opus; started on Sonnet it runs as a Sonnet chief with a lower ceiling. No issue tracker is needed: the task you describe, or a client's or manager's request in a file, is saved verbatim as the run's `task.md` under `.chief/runs/<id>/`, which git ignores.

### The run dashboard

```bash
python3 .claude/skills/chief/scripts/chief-run.py serve   # http://127.0.0.1:8765
```

One card per run, in columns by phase, with a chip for every agent: Claude subagents and Codex jobs alike, found through the run tag that starts each brief. Each card shows a Claude subtotal, a ChatGPT subtotal and their sum as an API-equivalent estimate; the header shows both accounts' 5-hour and weekly use with the 60% switch line, plus any git-check warnings. Click a card for the agent table, each agent's reply, and the run's task, plan, progress and handoff. `chief-run.py summary <run id>` prints the same numbers for the final report. Prices are in `skills/model-routing/prices.json`; Rates come from the official Anthropic and OpenAI pricing pages (2026-11-12); update the file when they change.

<details>
<summary><b>What model-routing needs on the machine</b></summary>
<br>

- `python3` for the scripts in `skills/model-routing/scripts/`.
- Recommended for Claude Code: run `python3 .claude/skills/model-routing/scripts/configure-hooks.py` (add `--global` for every project) to register `usage-before-spawn.py` as a PreToolUse hook; it is idempotent and keeps your other settings. Before every agent spawn and Codex job it adds both accounts' usage and the routing pick to the orchestrator's context. It never blocks a spawn.
- The chief reads git state from `git-check.py`: auto-commit Stop hooks, skip-worktree files that differ from HEAD (their changes never reach a commit), stray `*-E`/`*.orig`/`*.bak` files, and auto-save commits. To keep a project's auto-save Stop hook out of orchestrator runs, make its first line `[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0`.
- Codex jobs run outside Codex's sandbox by default (`--sandbox danger-full-access`), so they can run tests, reach the network and use local containers like a Claude agent. Pass `--sandbox workspace-write` to fence one.
- The `claude` CLI, logged in with a Claude subscription: Claude usage is read from `claude -p "/usage"`, a local command that spends no tokens.
- For ChatGPT workers, the Codex CLI (`codex`) logged in with ChatGPT. Usage is read from its local app-server, and jobs run through `codex exec`. Without Codex the skill still routes everything to Claude.
- Keep project rules in `AGENTS.md` with `CLAUDE.md` symlinked to it, so Claude and Codex workers load the same rules without them being pasted into every brief.
- Codex jobs are saved sessions; list them with `codex resume --all --include-non-interactive`.
- Optional: `"idleCompaction": false` in `~/.claude/settings.json` stops Claude Code compacting a long chief session while it waits on workers.

</details>

## Parallel waves

Running several implementer agents at once is the obvious speed-up. It's also how you get two agents editing the same registry, or one agent's `git add -A` sweeping up another's half-written files.

`parallel-plans` makes every task declare what it owns. `parallel-build` dispatches up to four tasks at once when their files don't overlap, then checks every commit before the next wave starts.

<p align="center">
<img alt="A plan flows into Wave 0, the shared kit, then fans out to tasks 2 to 5 running in parallel. All four pass through ownership-check: clean commits go to the integration task and on to main; a violation resumes that implementer." src="./assets/parallel-waves.svg" width="100%">
</p>

A plan declares ownership like this:

```markdown
## Parallel layout

Frozen during waves: `src/registry.ts`, `package-lock.json`

### Task 2: Feature A

**Owns:** `src/feature-a/**`

### Task 3: Feature B

**Owns:** `src/feature-b/**`
```

When an agent strays, `ownership-check` names the commit, the file, and the likely cause:

```console
$ bash scripts/ownership-check plan.md BASE HEAD 2,3
2fcef57 src/registry.ts: frozen during waves
2fcef57: spans tasks 2 and 3
2fcef57: looks like an auto-commit Stop hook ran mid-wave
```

If an agent needs shared code that doesn't exist yet, it writes it in a file it owns and reports it as _proposed for shared_. An integration task folds those proposals in once the wave is done, so no agent ever waits on another.

Each agent checks only what it touched: its own test files and a typecheck of the packages it edited, in its task and in every fix round. Every suite, end-to-end included, runs once, in the plan's last task. A small fix gets its re-review on the cheapest model, and a docs task runs beside whichever wave it shares no files with.

> [!NOTE]
> This repo was built this way: two parallel waves of four and two implementers, every wave ownership-clean.

## Why this repo exists

| The problem                                                                                                                  | The fix                                                                                                                                 |
| :--------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| **Parallel agents step on each other.** Shared registries get edited twice, and one agent's commit sweeps up another's work. | Each task owns its files, shared files are frozen during a wave, and `ownership-check` fails any commit that crosses a line.            |
| **Skills drift between repos.** Three repos end up with three different `wrap-up`s.                                          | One source of truth here. Repos install from it and update with one command, and every change arrives as a diff.                        |
| **Skills assume one repo layout.** A skill that hardcodes `context/memory/` breaks everywhere else.                          | Paths live in each repo's `AGENTS.md` under `## Skill paths`. The skills read them, and ask when one is missing.                        |
| **Customizations vanish on plugin updates.** Edit a skill in a plugin's cache, and the next version replaces it.             | Customized skills live here under names of their own and install with one command, so an update of anything else never overwrites them. |

## How installing works

<p align="center">
<img alt="Sources are installed one after another through npx skills add, with this repo last so it replaces skills of the same name. Each skill is written once to .agents/skills, which Codex reads, with a symlink in .claude/skills for Claude Code, and its source and tag go into skills-lock.json." src="./assets/install-flow.svg" width="100%">
</p>

When two sources ship a skill with the same name, the one installed last replaces the other: its folder and its `skills-lock.json` entry. One copy remains. That's why `install.sh` installs this repo last: a customized copy hosted here takes the place of the original it was made from.

A few rules keep this predictable:

- **Never edit installed copies.** `update` overwrites local edits without warning. Change a skill here, or host a customized copy of someone else's.
- **Keep one scope per skill name.** Claude Code prefers the personal (`~/.claude/skills`) copy over the project one, and Codex shows both. Install each skill at one scope.
- **Pin with `#tag`, never `@tag`.** The CLI silently ignores `owner/repo@tag` and installs the latest version.
- **Watch for built-in names.** A project skill named `code-review` replaces Claude Code's built-in `/code-review`.
- **Removing doesn't happen by itself.** Deleting a manifest line leaves the skill installed. Run `npx skills@1.7.2 remove <name> -y`.
- **Same-named folders get replaced.** Installing a skill replaces an existing `.claude/skills/<name>` folder, so a local untracked skill with that name is lost.

<details>
<summary><b>install.sh flags and settings</b></summary>
<br>

- `--dry-run` prints the CLI commands instead of running them.
- `--global` installs [`global.txt`](./global.txt) at user scope: `~/.agents/skills/`, symlinked from `~/.claude/skills/`.
- `SKILLS_CLI`, `HOSTED_SOURCE` (default `vgozalov/skills`) and `MANIFEST` override the CLI command, the source installed last, and the manifest path.
- The hosted line is recognised in any common spelling (`https://github.com/vgozalov/skills`, `.git`, `git@github.com:vgozalov/skills.git`, `github:vgozalov/skills`, a trailing `/`, with or without `#ref`), and is passed to the CLI exactly as written.
- If the script fails part-way, run it again before committing, because some skills may still be the copies from another source.

</details>

## FAQ

<details>
<summary><b>Why not a Claude Code plugin?</b></summary>
<br>

Plugin skills are namespaced (`my-plugin:wrap-up`), so they never take the place of a same-named skill from another source. Plugins also update themselves, and a plugin is Claude-only. Installing with `skills` gives one copy of each skill, under its plain name, for every agent, and updates only when you run `update`.

</details>

<details>
<summary><b>Why have install.sh if npx works?</b></summary>
<br>

For one or two sources, plain `npx` is all you need. The script earns its place when a repo pulls from several sources: it reads one file, installs everything for both agents in the right order, pins the CLI version, and turns off telemetry.

</details>

<details>
<summary><b>Does it work with Cursor, OpenCode or other agents?</b></summary>
<br>

The skills are plain `SKILL.md` folders, so any agent the `skills` CLI supports can install them with `-a <agent>`. They're written and tested against Claude Code and Codex. `parallel-build` needs an agent that can dispatch subagents.

</details>

## Development

```bash
bash tests/run.sh
```

This runs every `tests/*.test.sh`, then shellcheck over the scripts. [CI](https://github.com/vgozalov/skills/actions/workflows/test.yml) runs it on Linux with bash 5 and on macOS with `/bin/bash` 3.2, the version every script has to support.

The art (the banner, the skill emblems and the two diagrams) is drawn by [`assets/generate.py`](./assets/generate.py). It needs `fonttools`, downloads its three typefaces once into `assets/.fonts/` (pinned and checked against a SHA-256), and turns all text into outlines so the SVGs look the same everywhere:

```bash
pip install fonttools && python3 assets/generate.py
```

## Licenses

MIT. See [`LICENSE`](./LICENSE).

Do not install these skills next to another plugin that ships skills with the same names. Skills installed from other sources keep their own licenses and are never committed here. Anthropic's `docx`, `pdf`, `xlsx` and `pptx` are only ever installed from their source. The art uses Instrument Serif, Instrument Sans and IBM Plex Mono (SIL Open Font License 1.1); only their outlines appear in the SVGs.
