---
name: wrap-up
description: >
  Use when the user says "wrap up", "close session", "end session", "wrap
  things up", "we're done", "that's it for today", "session done", or invokes
  /wrap-up, at the end of a working session or after a major deliverable.
  Collects feedback, updates learnings, writes the daily memory entry and the
  one-line Last Session pointer, and commits the doc edits. Not for regular
  coding, debugging, or feature work.
---

# Session Wrap-Up

This skill handles the judgment parts of closing a session: what to record,
what to learn, what to hand to the next session. It works in any repo by
reading its paths from the repo's instructions file.

## Resolve paths first

The instructions file is `AGENTS.md` if the repo has one, else `CLAUDE.md`.
Read its `## Skill paths` block, a markdown list such as:

```
- memory: <directory for daily memory files>
- learnings: <path of the learnings file>
```

- The daily memory directory is the `memory` key.
- The learnings file is the `learnings` key.

If a key is missing, ask the user once and suggest a default:

- default for `memory`: `context/memory`
- default for `learnings`: `context/learnings.md`

Offer to add the key to the `## Skill paths` block so it is never asked
again. Use the answer for this run.

Everywhere below, "the memory directory" and "the learnings file" mean those
resolved paths.

## Process

### 1. Summarize Work Done

Review what was accomplished this session:

- Files created or modified (check git status)
- Features implemented or bugs fixed
- Tests written or run
- Architectural decisions made
- Any infrastructure or config changes

### 2. Collect Feedback

Ask the user:

> "Quick feedback on this session? Anything that worked well or should
> be done differently next time? (skip if nothing comes to mind)"

Wait for the response. If the user skips, move on.

### 3. Update Learnings

If feedback was given and is relevant to a specific skill:

1. Read the learnings file
2. Add the learning under the relevant skill section with today's date
3. If no section exists for that skill, create one
4. Save the file

If feedback is about general workflow (not skill-specific), add it under a
`## general` section in the learnings file.

### 4. Write Daily Memory

1. Create or append to `YYYY-MM-DD.md` (today's date) in the memory directory
2. Log:
   - Session timestamp
   - Summary of work done (2-3 lines max)
   - Key decisions made, with reasoning
   - Open items / what to pick up next session
   - Any blockers or risks identified

### 5. Update the instructions file's Last Session

**Exactly ONE entry lives in the `## Last Session` section, and it is one
line.** The detail belongs in the day's memory file; this line exists only to
point at it.

```
[DATE]: [What shipped] — next: [what's pending]. Full state: [<memory dir>/YYYY-MM-DD.md](...)
```

Three rules, in order of how often they get broken:

1. **Replace, never accumulate.** Delete the previous session's entry. This
   section is not a changelog; git history is. Left alone, it grows into
   dozens of stale lines.
2. **One line, not one paragraph.** If you are explaining a decision here, it
   belongs in the day's memory file. Link to it instead.
3. **Same-day re-runs append into that same single line**: `; also HH:MM: …`.
   You still leave exactly one entry when you are done.

If the instructions file has a `## Carryover backlog` section, update it with
items surfaced or resolved this session.

### 6. Commit the doc edits

Check whether the repo has an auto-commit Stop hook (look in the project's
settings for a Stop hook that commits). If it does, it commits for you; skip
this step.

If it does not, commit only the doc edits (the instructions file, the daily
memory file, the learnings file) on the current branch:

```
chore(docs): session wrap-up YYYY-MM-DD HH:MM
```

End the message with whatever commit trailer the instructions file requires.
Stage by explicit path, never the whole tree, so unrelated feature work is not
swept in. Doc edits should never be held hostage to feature work being ready.

Run wrap-up **before** opening a PR, not after: a wrap-up commit made after
the PR is pushed can be stranded by a squash-merge, or lost if the branch is
closed unmerged. If the current branch is being abandoned, commit on the
branch that will actually merge.

**Ask before pushing.** Do not push on your own initiative.

### 7. Confirm

Tell the user the session is wrapped up: what was recorded, where, and
whether the doc commit was made (and on which branch) or left to a Stop hook.

## Same-day re-runs: append, don't overwrite

This skill can be invoked more than once a day, manually or automatically by a
Stop hook when the context window fills up. On every run after the first of
the day, treat memory as **append-only**:

1. Before writing, check whether today's file exists in the memory directory.
2. If it does:
   - Read it fully.
   - Append a new `## HH:MM — wrap-up N` section with only the new decisions,
     files, and open items from the portion of the session that happened
     **after** the last section's timestamp.
   - Do **not** rewrite, reorder, or summarize earlier sections.
   - Remove or supersede an earlier line **only if** the session explicitly
     reversed that decision, for example the code was deleted or renamed, the
     user rejected the earlier approach, or a later decision in context
     contradicts it. When you do remove a line, add a short
     `~~struck~~ (reversed HH:MM: reason)` note in place rather than deleting
     silently.
3. Apply the same append-only discipline to the learnings file (add new dated
   bullets under the relevant section) and to the instructions file's
   `## Last Session` line (append `; also HH:MM: …` rather than replacing).
4. The Step 2 feedback prompt is optional on auto-triggered re-runs. If the
   user hasn't spoken since the last wrap-up, skip it and proceed.
