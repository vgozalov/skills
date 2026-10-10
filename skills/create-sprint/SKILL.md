---
name: create-sprint
description: >
  Use when the user says "create a sprint", "create sprint", "make a sprint",
  "build the sprint", "new sprint", or asks to turn a written plan or spec into
  a verification sprint. Produces a date-named sprint folder with a prod.json
  acceptance harness (category, description, steps per task) and a
  claude-progress.txt placeholder, in the format of the example bundled with
  this skill. Run after a spec and plan have been written for a sub-project.
  Does NOT trigger for writing the spec or plan themselves, or for regular
  coding/debugging.
---

# Create Sprint

Turns a written implementation plan into a self-contained verification sprint:
an acceptance harness of independently-checkable tasks. The format source of
truth is the `example/` folder inside this skill (`example/example-prod.json`
and `example/claude-progress.txt`).

Follow this process and ORDER exactly every time, so every sprint is consistent.

## 0. Resolve folders

Folder locations come from the `## Skill paths` block in the repo's instructions
file (`AGENTS.md` if present, else `CLAUDE.md`): a markdown list
of `- key: path` lines. This skill uses three keys:

- `sprints`: the sprint root, where the new sprint folder goes.
- `plans`: where written plans live.
- `specs`: where specs live.

Read the block before doing anything else. If a key is missing, ask the user
once for that folder. For `sprints`, suggest `sprints` as the default. Then
offer to add the answer to the `## Skill paths` block so the question is not
asked again. Use the paths exactly as written; do not assume any other layout.

## 1. Identify the source plan

- Determine which plan the sprint covers. Default to the plan the user is
  "picking up" or just wrote. Plans live in the `plans` folder as
  `YYYY-MM-DD-<name>.md`; the matching spec is usually in the `specs` folder.
- If the plan is ambiguous and more than one is plausible, ask which one.
  Otherwise proceed with the obvious candidate and state which you chose.

## 2. Read the plan (and spec) fully

- Read the entire plan. Extract every discrete, independently-verifiable
  behavior, not just the top-level task headings. One plan "Task" usually
  fans out into several sprint tasks (each behavior, each edge case, each
  validation guard, plus coverage/build gates).
- Skim the linked spec for acceptance criteria the plan assumes.

## 3. Inspect the example for format

- Read `example/example-prod.json` and `example/claude-progress.txt` from this
  skill's folder to confirm the shape before writing. The example is the
  source of truth; re-check it each time in case it has evolved.
- Each task object has exactly these keys:
  `category` (string), `description` (string), `steps` (string[]), `passes` (boolean).

## 4. Create the sprint folder

- Name it `YYYY-MM-DD-<sprintname>-sprint` using **today's date** and a short
  kebab-case sprint name derived from the plan (the plan's sub-project, for
  example `billing-core` or `search-filters`).
- Path: `<sprints>/YYYY-MM-DD-<sprintname>-sprint/`, where `<sprints>` is the
  `sprints` folder from step 0.

## 5. Write prod.json

- A JSON **array** of task objects (the example shows one object; the real
  file is the array of them).
- For EACH sprint task, write all of:
  - **category**: one of `functional`, `edge-case`, `validation`,
    `integration`, `coverage`, `build` (add a new category only if a behavior
    genuinely doesn't fit; keep the vocabulary small and consistent).
  - **description**: one concise sentence naming the behavior being verified.
  - **steps**: an ordered array of concrete, executable verification actions
    (the function + inputs + expected output, or the exact command to run and
    what to confirm). A reader with no extra context should be able to follow
    them and judge pass/fail.
  - **passes**: always `false` at creation (the verification run flips it).
- Coverage and build gates from the plan become their own tasks (for example
  "100% coverage", "typecheck + lint clean").
- Order tasks to mirror the plan's flow: core behaviors, edge cases,
  validation, integration/exports, coverage, build.

## 6. Write claude-progress.txt

- Copy the placeholder shape from `example/claude-progress.txt` (the two-line
  header plus the Anthropic harness URL), then add a short footer noting the
  source plan and spec paths for this sprint.

## 7. Report

- Summarize: sprint folder path, number of tasks, and the source plan.
- Do NOT commit unless the user asks. If they do, use a conventional commit
  (`chore(sprints): ...`) and end the message with whatever commit trailer or
  attribution the repo's instructions file requires. If it names none, add none.
