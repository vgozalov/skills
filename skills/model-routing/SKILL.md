---
name: model-routing
description: Use when about to spawn a subagent or Codex job, when checking git state during a delegated run (auto-commit hooks, skip-worktree files, stray backups), or when asked how work was routed or what it cost. Picks the model across Claude (Haiku, Sonnet, Opus, Fable) and ChatGPT via Codex (Luna, Sol, Astra), with the orchestrator's own model as the ceiling, and balances usage between the accounts: the orchestrator's own provider first, the other once it passes 60% of its 5-hour window. Applies whichever provider conducts (Claude Code, Codex, Gemini).
---

# Model routing

Choose the cheapest permitted model expected to meet the job's acceptance criteria. Stronger models are for unresolved reasoning, consequential review, or demonstrated failure. Route on the job, not on how important it feels or which model is conducting: a frontier orchestrator must not make building expensive.

Paths below (`scripts/`, `references/`) are relative to this skill's folder: the base directory shown when the skill loads, typically `.claude/skills/model-routing/` in a project or `~/.claude/skills/model-routing/` when installed globally. Run the scripts from the repo root.

Each spawn is three decisions: the tier (from the job), the ceiling (from your own model), the provider (from the user, then capability, then usage).

## Tiers and ceiling

| Tier        | Claude     | ChatGPT (Codex)                                                   | ChatGPT price, $ per M tokens in / out |
| ----------- | ---------- | ----------------------------------------------------------------- | -------------------------------------- |
| 1 Light     | Haiku 5.5  | `gpt-6-luna` (GPT-6 Luna)                                         | 0.10 / 0.50 (matches Haiku 5.5)        |
| 2 Workhorse | Sonnet 5.5 | `gpt-6.1-sol` (GPT-6.1 Sol; `gpt-6-sol` if the account lacks 6.1) | 2.00 / 10.00 (matches Sonnet 5.5)      |
| 3 Frontier  | Opus 5.5   | `gpt-6-astra` (GPT-6 Astra)                                       | frontier                               |
| 4 Top       | Fable      | none                                                              | —                                      |

**Each row is interchangeable.** Astra stands in for Opus, Sol for Sonnet, Luna for Haiku, and the other way round: a job routed to a tier may run on either provider, chosen by the rules under Provider below, and a reviewer on one counts the same as on the other. Terra and older GPT models are not routed; their tier is unverified. If Codex rejects a slug, tell the user.

**Tier 3 on ChatGPT (user's default, 2026-11-10):** run Astra at `--effort medium`; when Astra is rate-limited or the ChatGPT window is too low for it, fall back to Sol at `--effort high` for that job. Evidence, one side-by-side test so far: the same whole-branch review run three ways found the same findings each time, at these costs in the 5-hour window: Astra high +8%, Astra medium +7%, Sol high +3% (Sol took twice the steps). Earlier, three high-effort Astra plan reviews used a whole window. Re-run the comparison on the next large review and record the result here before changing this default.

Your own model is the ceiling on both providers: Sonnet or Sol allows tiers 1–2, Opus or Astra 1–3, Fable 1–4 (tier 4 only with a stated reason, after tier 3 failed or could not settle a call). A orchestrator on another provider takes the ceiling of the row its model matches in strength. Read your model from your own context, not the agent file. Never exceed the ceiling silently; say "needs a higher tier" to the user instead.

## Provider

Decide in this order:

1. **The user's direction.** When the user names a provider or model for the session or a job ("mostly Claude", "Codex only", "use Astra"), use it at the job's tier; when that account is near its limit, ask before switching.
2. **Capability.** A job that needs something only one provider has goes there, whatever the usage. Image generation goes to ChatGPT, because Claude cannot generate images.
3. **Usage balance.** Prefer your own provider: a Claude orchestrator spawns Claude agents, a Codex orchestrator ChatGPT jobs. Once your provider has used 60% of its 5-hour window, send new jobs to the other provider; when the other one passes 60% instead, come back. The rest of your own window is the orchestrator's reserve: you run on that account too, and when it runs dry the whole session stops, however much the other account has left.

Run `python3 <skill folder>/scripts/check-account-usage.py --orchestrator <claude|chatgpt|gemini>` at intake, at each new request from the user, at each phase start, before each wave of spawns, and after a job stops on a usage limit. A single check at intake does not hold for a long run: the usage moves while the work does. Inside Claude Code the orchestrator is detected and the flag can be left out. It reads both accounts without spending a model turn and prints each one's 5-hour and weekly use, a `pick` and the `why` (and, for a Claude orchestrator, `spawn_hook`: whether the hook below is registered):

- your own provider while it is under 60% of its 5-hour window;
- otherwise the other provider with room, lowest 5-hour use first; with both past 60%, still the other one, so your reserve holds;
- an account at 90% of either window, or blocked, only when nothing else has room;
- `"ask"` when your own account cannot be read or every account is near a limit: ask the user once.

A orchestrator whose own usage the script cannot read (Gemini today) has no reserve to keep; its jobs go to the provider with the lower 5-hour use.

In Claude Code, `scripts/usage-before-spawn.py` registered as a PreToolUse hook (the settings snippet is at its top) repeats the check before every Agent spawn and every `run-codex-job.py` launch, and adds one line to your context: both accounts, the pick, and whether this spawn matches it. The hook never blocks: a spawn that differs from the pick is right when rule 1 or 2 put it there, and otherwise a sign to switch. When `spawn_hook` is `missing`, only the checkpoints above guard the switch; tell the user once.

A job that stops on a usage limit is relaunched at the same tier on the other provider. Codex jobs run outside the sandbox, with network, tests and local containers, as a Claude agent does. For Codex jobs, `cat <skill folder>/references/use-codex.md` once per session.

## Git state

Workers share one working tree, so the orchestrator watches what git will and will not record. `python3 <skill folder>/scripts/git-check.py` prints one line of JSON: branch and upstream, Stop hooks that auto-commit, skip-worktree files whose working copy differs from HEAD, stray backup files (`*-E`, `*.orig`, `*.bak`, `*.rej`, `*~`), and auto-save commits since the base. Its `warnings` list only what needs action. Run it with `--start-run` at intake, plain before every review, and with `--end-run` at pause and at report.

| Warning | What goes wrong | Action |
| --- | --- | --- |
| Auto-commit Stop hook that does not skip runs | Commits half-finished work from several workers under a generic message | Ask the user to pause it for the run, or to make it skip runs (below) |
| Skip-worktree file differs from HEAD | `git add` and auto-save ignore it: a worker's fix never reaches a commit, and a test committed for it fails on every other checkout | Name it in the briefs; at report, commit its feature hunks selectively, never a local URL |
| Stray backup file | `sed -i -E` on macOS leaves `<file>-E`, which auto-save commits | Delete it; the briefs forbid `sed -i` |
| Auto-save commits on the branch | History breaks the repo's commit-message rule | Offer the user one descriptive conventional commit in their place |

`--start-run` writes a `chief-run` marker inside the git dir (never tracked). A project's auto-save Stop hook skips orchestrator runs when its first line is:

```sh
[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0
```

## Review rule

A reviewer is fresh, never the author, never tier 1, and never below the author's tier, whichever provider each runs on. Same tier is fine. Work by several authors is reviewed at or above the highest. A fix check goes back to the reviewer who raised the findings only while its thread is small (under about 200k tokens); otherwise to a fresh reviewer of the same tier with the finding list and `git diff -- <files>`. Why: a weaker reviewer misses what the author got subtly wrong, and its pass is unearned. A reviewer from the other provider is a bonus when usage allows.

## Five questions about any job

1. Is the spec complete: file, signatures, behaviour, nothing left to choose?
2. Does it use an API this repo has never used?
3. Do more than about six rules interact (ordering, fallbacks, edge cases)?
4. Is the blast radius wide: several files, shared state, behaviour others depend on?
5. Would a wrong answer stay invisible until a user hits it?

No flags: tier 1. One or two local flags: tier 2. A flag that is really an unsettled design decision goes back to planning, not to a bigger builder. Small is not easy: a three-line permission change can need more judgement than a hundred lines of repetitive UI.

## Routing by role

"Top" means the highest tier you are permitted, capped at 3.

| Role                                                                                                                                 | Tier                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Narrow research, git state, running commands, reading logs, environment diagnosis                                                    | 1                                                                                           |
| Web research                                                                                                                         | 2                                                                                           |
| Broad research, root cause, design options (the user decides)                                                                        | top                                                                                         |
| Plan writer, design already settled by the user                                                                                      | 2                                                                                           |
| Plan writer, the plan must decide the design                                                                                         | top                                                                                         |
| Plan reviewer, routine plan                                                                                                          | 2, one agent with both lenses                                                               |
| Plan reviewer, substantial plan                                                                                                      | top, one agent; on a Sonnet ceiling, two tier-2 agents with one lens each, one per provider |
| Implementer, all five questions clean                                                                                                | 1                                                                                           |
| Implementer, local decisions remain                                                                                                  | 2                                                                                           |
| Implementer, flags a tighter spec cannot remove                                                                                      | top, reviewed at top                                                                        |
| Per-task review, only for risky tasks (two or more flags, event handling, shared state); otherwise the whole-branch review covers it | implementer's tier, minimum 2                                                               |
| Whole-branch review                                                                                                                  | top                                                                                         |
| Bug fixer (behaviour, framework, layout, async)                                                                                      | 2                                                                                           |
| Mechanical fixer (exact edit written out)                                                                                            | 1                                                                                           |
| Failing test or build                                                                                                                | 2; top if a design flaw                                                                     |
| Triage of conflicting findings                                                                                                       | top                                                                                         |

A plan is substantial when it decides the design, has more than five tasks, touches auth, permissions, persisted data or shared state, or its tasks carry two or more flags. Otherwise routine.

**Tighten before escalating.** A build job with flags goes back to the plan writer for the missing signatures, API usage and rules first; the plan reviewer should catch these by asking which tasks a tier-1 builder could not finish. Two more plan lines cost less than a frontier build.

## Escalation

- An unsettled design decision during building: stop the job, send the question to the plan writer.
- Fails review on ordinary grounds: one repair, as a fresh job given the findings and `git diff -- <files>` (mechanical findings tier 1, behaviour tier 2). Resume the original worker (SendMessage, or `--resume`) only when its thread is under about 200k tokens: a resumed thread re-sends its whole history on every step.
- Repair fails: the diff and failure evidence go one tier up, within your ceiling. A failure at your ceiling goes to the user, after at most two repair rounds.
- Missing dependency, service down, sandbox, network or auth error: a tier-1 agent diagnoses; the model does not change.
- Each repair is reviewed at the repairer's tier or above.

## Token budget

Every worker step re-sends its whole context, so cost grows with steps × context. The four habits that cost most in the first real run: long test output carried forward, whole large files read, fixes resumed on long threads, and per-task reviews duplicating the whole-branch review. The brief templates prevent the first two; the rules above prevent the last two. Use `medium` effort for routine reviews and builds, `high` only for plan review and the whole-branch review. Start a fresh orchestrator session per feature: the plan file and git carry the state.

Before writing a brief: `cat <skill folder>/references/write-briefs.md`. Before the final report: `cat <skill folder>/references/report-costs.md`. API-equivalent prices for both providers live in `<skill folder>/prices.json`; the `chief` skill's run summary and dashboard read them.
