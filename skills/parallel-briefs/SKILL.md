---
name: parallel-briefs
description: Use when splitting work across several agents running at the same time outside an implementation plan, or when the user asks for per-agent briefs, file ownership, or a "do not touch" list.
---

# Parallel Briefs

## Overview

Parallel agents work only when each owns disjoint files, shared files are frozen while they run, and a gap in shared code is worked around locally and reported instead of edited. Everything below follows from those three rules. The mechanism is one brief per agent, with the same shared blocks in every brief.

## Phase 1, the kit (serial, one agent)

Build what every agent will consume: contracts, types, shared components, registries, test helpers. Commit it. Nothing parallel starts until the kit is committed, because an agent that reads a half-built kit invents its own version of it.

## Phase 2, sections (parallel, at most four agents)

One brief per agent, each covering a disjoint slice of the work. More than four concurrent agents costs more in merge conflicts and review than it saves in wall-clock time. If the work has more slices, group them or run a second wave after Phase 3. A docs slice written from the spec rather than from the code runs here, beside the code slices.

## Phase 3, merge (serial)

One agent, after every Phase 2 agent has reported:

1. Fold each "Proposed for kit" item into the kit.
2. Delete the local copies the agents wrote, and merge duplicate helpers into one.
3. Edit the registries, barrels and entry points that were frozen during Phase 2.
4. Run every suite once: each package's tests, every typecheck, and every end-to-end or browser suite at each configured viewport. This is the only full run; Phase 2 agents ran only their own tests.

## The brief template

Write each brief to a file. Four blocks are identical in every brief; only "Your files" differs.

```markdown
### Your files

<the only files/globs this agent may create or edit>

### Do not touch

<identical in every brief: the kit, registries, entry points, lockfiles, generated files>

### Read first

<identical in every brief: spec/design docs, the contract, project rules>

### If the shared kit is missing something

Write it in one of your own files and list it in your report under "Proposed for kit": what it is, where you put it, where it should live. Do not edit the kit and do not stop to ask.

### Verify

Your verification is exactly: the test files you created or edited, plus the existing test file of each source file you modified, run by path; and a typecheck of each package you edited. Every suite, end-to-end included, runs once in the merge phase. If the typecheck reports errors only in files outside "Your files", they are a sibling's unfinished work: list them in your report and leave those files alone.
```

Add the task itself (requirements, acceptance checks) and the report format around these blocks. The blocks are the part that keeps agents from colliding.

## Checks before launch

- The "Your files" sets are pairwise disjoint. Compare the globs, not just the file names.
- Every aggregate file is on "Do not touch": registries, barrels, index files, lockfiles, generated output, route or navigation tables.
- No agent consumes something another Phase 2 agent produces. If one does, the producer's output belongs in the kit, or the two slices belong to one agent.
- The kit is committed and the "Read first" paths all exist.

## Launching

With an agent tool, send all Phase 2 dispatches in one message so they run concurrently, each with its brief file path. Without one, open one session per brief.

Tell every agent to stage and commit by explicit path only, since siblings have uncommitted work in the same tree. The brief's "Verify" block keeps each agent's test runs to its own files.

## Relation to plans

Inside an implementation plan, use parallel-plans' ownership blocks and parallel-agent-development's waves instead. This skill is for work outside a plan.
