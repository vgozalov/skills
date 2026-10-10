# shellcheck shell=bash
# Behaviour of scripts/ownership-check: wave commits must stay inside their task's Owns.

OC="$REPO_ROOT/skills/parallel-agent-development/scripts/ownership-check"

make_wave_repo() {
  git init -q .
  cat > plan.md <<'PLAN'
## Parallel layout

Frozen during waves: `registry.ts`, `gen/**`

### Task 2: A

**Owns:** `a/**`, `shared name.txt`

### Task 3: B

**Owns:** `b/**`
PLAN
  git add plan.md
  git commit -q -m base
  BASE=$(git rev-parse HEAD)
}

# commit_files SUBJECT FILE...
commit_files() {
  local subject=$1 f
  shift
  for f in "$@"; do
    mkdir -p "$(dirname "$f")"
    echo x >> "$f"
    git add -- "$f"
  done
  git commit -q -m "$subject"
}

run_oc() {
  RC=0
  OUT=$(bash "$OC" plan.md "$BASE" HEAD "$1" 2>&1) || RC=$?
}

test_clean_wave_passes() {
  make_wave_repo
  commit_files "task A" a/x.ts
  commit_files "task B" b/y.ts
  run_oc 2,3
  assert_eq 0 "$RC" "exit code"
  assert_eq "ownership-check: 2 commit(s) clean" "$OUT" "stdout"
}

test_nested_glob_matches() {
  make_wave_repo
  commit_files "task A" a/deep/er/x.ts
  run_oc 2,3
  assert_eq 0 "$RC" "exit code"
}

test_path_with_space_is_matched() {
  make_wave_repo
  commit_files "task A" "shared name.txt"
  run_oc 2,3
  assert_eq 0 "$RC" "exit code"
}

test_file_outside_owns_fails() {
  make_wave_repo
  commit_files "stray" c/z.ts
  run_oc 2,3
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "c/z.ts: outside Owns of tasks 2,3" "message"
}

test_frozen_file_fails() {
  make_wave_repo
  commit_files "touch frozen" registry.ts
  run_oc 2,3
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "registry.ts: frozen during waves" "message"
}

test_commit_spanning_two_tasks_fails() {
  make_wave_repo
  commit_files "mixed" a/x.ts b/y.ts
  run_oc 2,3
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "spans tasks 2 and 3" "message"
}

test_checkpoint_commit_names_stop_hook() {
  make_wave_repo
  commit_files "chore: auto-save session checkpoint" a/x.ts b/y.ts
  run_oc 2,3
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "auto-commit Stop hook" "message"
}

test_only_listed_tasks_count() {
  make_wave_repo
  commit_files "task B" b/y.ts
  run_oc 2
  assert_eq 1 "$RC" "exit code"
}

test_task_without_owns_exits_2() {
  make_wave_repo
  commit_files "task A" a/x.ts
  run_oc 2,4
  assert_eq 2 "$RC" "exit code"
  assert_contains "$OUT" "Task 4 has no **Owns:** line" "message"
}

# make_bracket_repo: a plan whose Owns/Frozen globs contain [ ] ( ) like Next.js routes.
make_bracket_repo() {
  git init -q .
  cat > plan.md <<'PLAN'
## Parallel layout

Frozen during waves: `gen/[x]/**`

### Task 2: Route

**Owns:** `apps/web/src/app/(app)/jobs/[id]/**`, `docs/v?.md`
PLAN
  git add plan.md
  git commit -q -m base
  BASE=$(git rev-parse HEAD)
}

test_bracketed_owns_path_matches() {
  make_bracket_repo
  commit_files "route" "apps/web/src/app/(app)/jobs/[id]/page.tsx"
  run_oc 2
  assert_eq 0 "$RC" "exit code"
}

test_bracket_in_owns_is_not_a_character_class() {
  make_bracket_repo
  commit_files "route" "apps/web/src/app/(app)/jobs/i/page.tsx"
  run_oc 2
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "outside Owns" "message"
}

test_question_mark_in_owns_is_literal() {
  make_bracket_repo
  commit_files "doc" "docs/v?.md"
  run_oc 2
  assert_eq 0 "$RC" "literal ? file"
  commit_files "doc2" "docs/v1.md"
  run_oc 2
  assert_eq 1 "$RC" "? must not match a single char"
}

test_bracketed_frozen_path_is_rejected() {
  make_bracket_repo
  commit_files "frozen" "gen/[x]/f.ts"
  run_oc 2
  assert_eq 1 "$RC" "exit code"
  assert_contains "$OUT" "gen/[x]/f.ts: frozen during waves" "message"
}

test_empty_range_exits_3() {
  make_wave_repo
  RC=0
  OUT=$(bash "$OC" plan.md "$BASE" "$BASE" 2,3 2>&1) || RC=$?
  assert_eq 3 "$RC" "exit code"
  assert_contains "$OUT" "empty commit range" "message"
}

test_head_not_descendant_of_base_exits_3() {
  make_wave_repo
  commit_files "task A" a/x.ts
  local tip
  tip=$(git rev-parse HEAD)
  git checkout -q "$BASE"
  commit_files "other branch" b/y.ts
  RC=0
  OUT=$(bash "$OC" plan.md "$tip" HEAD 2,3 2>&1) || RC=$?
  assert_eq 3 "$RC" "exit code"
  assert_contains "$OUT" "HEAD is not a descendant of BASE" "message"
}
