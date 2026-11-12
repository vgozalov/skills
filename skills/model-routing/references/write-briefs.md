# Writing briefs

Every brief is self-contained: the worker has not seen this conversation. Paste what it needs, point at files for the rest, delete lines that do not apply.

## Rules that came from real runs

- **Contract, not mechanics.** Give the exact names and signatures other workers export, what must be true, and what is forbidden. Do not suggest techniques: a hint to "use the functional form of setState" produced a side effect inside an updater.
- **Name what not to run.** Workers run linters and builds out of habit.
- **Name the files each worker owns and must not touch.** Disjoint ownership is what makes parallel work safe, across providers too, since Claude and Codex workers share one working tree. At most four jobs at once, both providers counted.
- **Give a packet, so the worker does not explore.** Files, one existing example to copy, settled interfaces, the check to run. Repeated exploration is where most tokens go.
- **Cap test output.** Workers run `npx vitest run <file> --reporter=dot 2>&1 | tail -40`, adding `-t "<test name>"` while iterating. Full test output re-sent on every later step was the single biggest waste in the first run (one fix job: 1.98M input tokens).
- **Anchor with line ranges.** Give `file:line` ranges and short excerpts; workers read `sed -n <a>,<b>p <file>` instead of whole large files.
- **Reviewers get the distilled spec**, such as an earlier audit's numbered list, not raw prototypes or long documents.
- **Batch related mechanical changes into one job.** Each job has a fixed start-up cost (a trivial Codex run measured about 17k input tokens, three quarters cached).
- **Compact returns.** Status, changed files, checks, blockers, what it was unsure about. Code stays in files.
- **Reviewers are read-only** and return ranked findings with file:line, a reason and a failure scenario, plus one line on the checks that passed.
- **Fix checks say** "an issue that already exists in the original code does not count as a failure".

## Common block

```
Run: <run folder>   Task: <task id or ->   Role: <role>
Repo: <absolute path>   Branch: <branch>   (uncommitted working tree)
Other agents are editing other files at the same time. Touch only the files under "Your files".
Read first: <plan/spec path, sections>. <Ignore / Follow> its test steps.
Do NOT run: <npm run build, npm run lint, eslint, the full test suite, git add, git commit, git push>.
Skip-worktree files you may touch: <from git-check.py; delete the line when none>. Git does not record their changes, so list every change you make to them in your report.
Edit files with your edit tool. Never `sed -i` (on macOS `sed -i -E` leaves a `<file>-E` backup beside the file).
Tests: `npx vitest run <file> --reporter=dot 2>&1 | tail -40`. Read large files by line range.
Report in under <N> words, naming any files you created outside "Your files", temporary and backup files included.
```

The first line is the run tag `chief-run.py start` printed; keep it first and exact, for Codex too (`run-codex-job.py` reads it to record the job in the run). It is how the dashboard and the cost report find every agent. Outside a orchestrator run, drop it.

Keep project rules in the repo's `AGENTS.md` (with `CLAUDE.md` symlinked to it) so Claude and Codex both load them automatically, and do not repeat them in briefs. Without that file, add the few rules the job needs. For Codex, add: "Do not commit, push or create branches."

## Researcher

```
Question: <one question>
Where to look: <dirs or files; what is out of scope>
Return a direct answer, then up to <5> file:line references. Say "not found" plainly. Read-only; propose nothing.
```

## Plan writer

```
Use the parallel-plans skill. Goal: <one sentence>. User decisions, verbatim: <list>. Research: <summaries or paths>.
Save to <the repo's plans folder>/<date>-<name>.md, following the repo's rule on whether plans are committed.
Each task states files, exact signatures, interfaces consumed and produced, the user's exact values, one example to copy, and its verification command.
Return the path and a five-line summary.
```

## Plan reviewer

```
Read <plan path> and <decisions>. Read-only.
Lens A, coverage and consistency: is every decision in a task; do names and signatures match across tasks?
Lens B, buildability and risk: which tasks could a tier-1 builder not finish from the plan alone, and what is missing; what will bite a user that no task tests?
Return at most 10 items, most severe first: severity | task | problem | fix. One line on what is solid.
```

## Implementer: task packet

```
Objective: <one sentence>
Acceptance criteria: <numbered, checkable>
Your files: <list>   Do not touch: <everything else, including tests unless told>
Example to copy: <file:lines that already does the same kind of thing>
Contract (others write these in parallel; they will exist): <module: exported names, signatures, one line of behaviour each>
Constraints and forbidden: <rules from the plan>
Verify with: <command and the output that means pass, or "re-read your files for syntax" when tests are waived>
Stop and report BLOCKED, without guessing, if: <a design choice the plan does not settle, a file outside your list must change, the contract does not fit>
You may read other files when this is not enough; keep it targeted.
Return in under <N> words: DONE / BLOCKED / FAILED, changed files, checks and results, blockers, what you were unsure about. No code in the reply.
```

For tier 1, also list every function with its exact behaviour.

## Whole-branch reviewer

The prompt is requesting-code-review's `code-reviewer.md`, its placeholders filled: `[DESCRIPTION]` the run's goal, `[PLAN_OR_REQUIREMENTS]` the plan path (Decisions, Review Focus), `[BASE_SHA]`/`[HEAD_SHA]` the branch range. Then add, after the template:

```
Run: <run folder>   Task: -   Role: review      (as the first line, above the template)
Review package: <path from parallel-build's review-package>; read it once instead of running git diff.
git-check.py warnings: <paste>. A test that depends on a skip-worktree change fails on every other checkout.
Also check: every import resolves, including named exports in node_modules; leftovers from removed code; for UI, React correctness, polling loops, StrictMode hazards, styling and overflow, and whether the page renders without a runtime error.
```

## Fixer

```
Your files: <list>. Fix exactly these findings, nothing else:
<number | file:line | what to change>
Return status per finding, changed files, checks run, uncertainty.
```

## Fix check (to the reviewer who raised the findings)

```
These findings from your review were fixed: <number | file:line | what changed>
Read-only. PASS or FAIL per finding with file:line; say if a fix broke anything next to it or left an unresolved import.
An issue that already exists in the original code (`git show HEAD:<file>`) does not count as a failure.
```

## Git steward (clean-up, only when the user asked for it)

The orchestrator reads git state from `git-check.py` itself; a steward is for changing it.

```
Repo: <path>   Branch: <branch>   Base: <base>
git-check.py warnings: <paste>
Do exactly what the user approved, nothing else:
- Replace the auto-save commits <shas> with one commit, message: <conventional message the user approved>. Use `git reset --soft <commit before the first auto-save>` only when every later commit is in that list; otherwise stop and report. If the branch is pushed, stop and ask before rewriting it.
- Stage by explicit path. Never `git add -A`, `git add .` or `git commit -a`.
- Skip-worktree file <path>: commit only the hunks <describe>. `git update-index --no-skip-worktree <path>`, `git add -p <path>`, commit, then `git update-index --skip-worktree <path>`. Never commit a local URL.
- Delete stray files: <paths>.
Then run `python3 <skill folder>/scripts/git-check.py` and return its warnings, `git status --short` and `git log --oneline <base>..HEAD`.
```
