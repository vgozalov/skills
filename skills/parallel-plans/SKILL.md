---
name: parallel-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write implementation plans for an engineer who has not seen this codebase or this spec. Assume they write idiomatic code in the project's language once they know the exact interface and the exact test, and that they will make a reasonable choice wherever the plan leaves one open. What they cannot know is what you decided: which files, which names and signatures, which values from the spec, which tests prove each task. Document those. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

**Announce at start:** "I'm using the parallel-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `superpowers:using-git-worktrees` skill at execution time.

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. When drawing task boundaries: fold setup,
configuration, scaffolding, and documentation steps into the task whose
deliverable needs them; split only where a reviewer could meaningfully
reject one task while approving its neighbor. Each task ends with an
independently testable deliverable.

## Step Granularity

**Each step is one action with a checkable result:**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use parallel-agent-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Spec:** [path to the spec/design doc this plan implements — the plan
argues from the spec, so the spec travels with it; executors read both]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

## Review Focus

[The five input classes or failure modes the spec implies but no task's
tests exercise that are most likely to bite a person using this software
— one line each, naming the input or condition and the behavior a
reasonable person would expect, most likely first. The spec is a vision
document: it says what the software must do, not everything it will
meet, and its silence on an input is not permission for that input to
break the program. Write the list here, once, with the spec in front of
you. Then, for each line, add the test that pins it to the task that
owns the code, in that task's own step style.]

## Parallel layout

[Include this section when two or more tasks can run in parallel; omit it
for strictly serial plans.]

Frozen during waves: [registries, barrels, lockfile, generated files,
migrations — each path or glob in backticks, on this one line]
Wave 0 (serial): Task N — [shared contracts / the "kit"]
Wave 1 (parallel): Tasks N, N, N
Integration (serial): Task N — [registrations, generated files, "Proposed for shared"]
Final (serial): Task N — final verification, every suite once

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Owns:** `exact/path/to/file.py`, `tests/exact/path/to/test.py`
**Frozen:** (the plan's "Frozen during waves" list)
**Read first:** [spec sections, rules, contract files]
**If shared code is missing:** write it in a file you own; list it under
"Proposed for shared" in your report.

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter
  and return types. A task's implementer sees only their own task; this
  block is how they learn the names and types neighboring tasks use.]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Implement `function(input: InputType) -> ResultType` in `exact/path/to/file.py`**

One line on the approach when the signature and the test leave a choice
(which library call, which data structure); a code block only for an
algorithm they do not determine.

- [ ] **Step 4: Run the task's tests and typecheck**

Run: `pytest tests/path/test.py -v` and `mypy src/path/`
Expected: PASS; no type errors

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Parallel Layout and Ownership

When two or more tasks can run at the same time (each in its own subagent, in
one working tree), the plan must say who may touch what, or two tasks will edit
the same registry, barrel, or lockfile and the wave collides.

- **`Frozen during waves:`** one line near the top of the plan, listing in
  backticks every path or glob no wave task may edit: registries, barrels, the
  lockfile, generated files, migrations. If the repo keeps this list in its own
  rules, copy it from there. Only the integration task edits frozen files.
- **`**Owns:**`** on every task in a wave: backticked paths or globs covering
  every path in that task's Files block. Owns lines of tasks in the same wave
  must not overlap. `**` behaves like `*` (it matches across `/`), and `src/**/*.ts`
  does not match `src/top.ts` — use `src/**` or list the file.
- Waves run in order: a serial kit task first (Wave 0), then the parallel tasks
  (Wave 1), then a serial integration task that makes the frozen-file edits and
  collects each task's "Proposed for shared".
- A wave's tasks need not be adjacent in the plan. A task that consumes
  nothing from the tasks it would skip goes in the earliest wave whose Owns
  it does not overlap — usually a docs task written from the spec and the
  Interfaces blocks: `Wave 2 (parallel): Tasks 9, 16`. It needs an Owns line
  like any wave task.

Executors verify a wave with `ownership-check` (in the
`parallel-agent-development` skill), which parses exactly this format: a task
starts at a `### Task <N>:` heading, its Owns are the backticked tokens on its
`**Owns:**` line, and the frozen globs are the backticked tokens on the
`Frozen during waves:` line. Keep each of those on a single line.

Worked example:

<!-- ownership-example:start -->

```markdown
## Parallel layout

Frozen during waves: `src/registry.ts`, `package-lock.json`
Wave 0 (serial): Task 1 — shared contracts / the kit
Wave 1 (parallel): Tasks 2, 3
Integration (serial): Task 4 — registrations, generated files, "Proposed for shared"

### Task 2: Feature A

**Files:**
- Create: `src/feature-a/index.ts`
- Test: `src/feature-a/index.test.ts`

**Owns:** `src/feature-a/**`
**Frozen:** (the plan's list)
**Read first:** spec section on Feature A; `src/contracts.ts`
**If shared code is missing:** write it in a file you own; list it under
"Proposed for shared" in your report.

### Task 3: Feature B

**Files:**
- Create: `src/feature-b/index.ts`
- Test: `src/feature-b/index.test.ts`

**Owns:** `src/feature-b/**`
**Frozen:** (the plan's list)
**Read first:** spec section on Feature B; `src/contracts.ts`
**If shared code is missing:** write it in a file you own; list it under
"Proposed for shared" in your report.
```

<!-- ownership-example:end -->

Task 2 and Task 3 each cover their own directory and share no path.
`src/registry.ts` and `package-lock.json` are edited only by Task 4, where
Feature A and Feature B get registered.

## Final Verification Task

Every plan ends with one serial task that runs every suite once — the only
task whose steps run whole suites. Regular tasks verify only their own test
files and a typecheck of the packages they edit, so breakage that crosses
packages surfaces here, once, instead of being paid for in every task.

````markdown
### Task N: Final verification

**Files:** none planned — a fix goes where its failure points.

- [ ] **Step 1: Run every suite**

Run: [one line per suite, exact commands: each package's unit and
integration tests, every package's typecheck, every end-to-end or browser
suite at each configured viewport or project]
Expected: all pass, output pristine

- [ ] **Step 2: Fix each failure at its cause; re-run the failing suites and those of each package a fix touched; commit by explicit path**
````

## What a Step Contains

A step is done when the implementer can write exactly one reasonable thing
from it. That is the whole requirement: unambiguous, not complete. Each kind
of step carries what makes it unambiguous and nothing more:

- **A test step:** the test's name and its assertions, as code, with the
  spec's exact values in them.
- **A code step:** the exact signature (name, parameters, return type), the
  file it lives in, and the specific values the spec pins. The implementer
  writes the body. A body appears only for an algorithm the signature and
  tests do not determine, or for exact copy the spec fixes.
- **A verification step:** the command to run and the output that means it
  passed. In a regular task, that is the task's own test files by path and
  a typecheck of the packages it edits. Whole-suite, end-to-end and browser
  commands go in the final verification task.
- **A reference to another task:** that task's Interfaces block says what
  to use; the plan does not repeat that task's code.

A plan is the set of decisions the implementer cannot make alone. A plan
longer than the code it describes has written the code instead. Lines that
decide nothing ("TBD", "handle edge cases", "add appropriate validation",
"write tests for the above", a type or function no task defines) are the
opposite failure, and the self-review catches both.

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Step scan:** Every step must let the implementer write exactly one reasonable thing, and no step may carry more than that: a line that decides nothing is a gap, a function body the signature and tests already determine is a transcript. Fix both.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

**4. Review Focus:** For each input class or failure mode the spec implies, is there a task whose tests exercise it? The five uncovered ones most likely to bite a person go in the Review Focus section, and each line there gets its test added to the owning task. An empty section means you checked and found none, not that you skipped the check.

**5. Proportion:** Compare the plan's length to the spec's. A plan several times longer than the spec it implements is a transcript of the program, not a plan. If code blocks are most of the document, replace bodies with signatures, test names and assertions, and check that each step is still unambiguous.

**6. Ownership** (only for plans with a Parallel layout): Every task in a wave has an `**Owns:**` line covering every path in its Files block; Owns lines of tasks in the same wave share no path; every registry, barrel, lockfile, generated file or migration any task touches is on the frozen list and is edited only by the integration task. Each docs or other leaf task sits in the earliest wave it can join, not after the tasks it does not depend on.

**7. Verification:** The last task is Final verification, naming every suite's exact command. Every other task's run steps name only its own test files and a typecheck of the packages it edits.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Execution Handoff

After saving and self-reviewing the plan, link it for your human partner
to read. If they have already explicitly supplied an execution method, ask
them to review the plan and confirm it captures what they want; wait for that
review before implementation, then use the preserved method. Otherwise, ask
them to review the plan and choose an execution method before implementation.

**When no execution method has already been supplied:**

**"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Please review the plan. Which execution approach would you prefer?**

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end. Runs well with a mid-tier session model, since the plan carries the design.

**For this plan I recommend <one of the two>, because <one sentence from the plan: how much the tasks depend on each other's interfaces, how many there are, what a shipped mistake would cost>. Does the plan capture what you want, and which approach should we use?"**

**When an execution method has already been supplied:**

**"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Please review the plan. Does it capture what you want?"**

**If Subagent-driven chosen:**
- **REQUIRED SUB-SKILL:** Use parallel-agent-development

**If Native chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:executing-plans
