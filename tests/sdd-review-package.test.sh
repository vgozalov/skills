# shellcheck shell=bash
# Pins the parallel-wave pathspec behaviour of review-package.

RP="$REPO_ROOT/skills/parallel-agent-development/scripts/review-package"

make_repo() {
  git init -q .
  echo plan > plan.md
  echo a > a.txt
  echo b > b.txt
  git add plan.md a.txt b.txt
  git commit -q -m base
  BASE=$(git rev-parse HEAD)
  echo a2 >> a.txt
  git commit -q -am "task A"
  echo b2 >> b.txt
  git commit -q -am "task B"
}

test_pathspec_limits_to_own_commits() {
  make_repo
  bash "$RP" plan.md "$BASE" HEAD "$PWD/out.diff" -- a.txt >/dev/null
  local out
  out=$(cat out.diff)
  assert_contains "$out" "task A" "own commit listed"
  assert_not_contains "$out" "task B" "sibling commit excluded"
  assert_not_contains "$out" "b.txt" "sibling file excluded"
}

test_no_pathspec_includes_all() {
  make_repo
  local out
  out=$(bash "$RP" plan.md "$BASE" HEAD "$PWD/out.diff")
  assert_contains "$out" "2 commit(s)" "all commits counted"
}

test_pathspec_with_no_commits_exits_3() {
  make_repo
  local rc=0
  bash "$RP" plan.md "$BASE" HEAD "$PWD/out.diff" -- plan.md >/dev/null 2>&1 || rc=$?
  assert_eq 3 "$rc" "exit code"
}

test_bare_separator_exits_2() {
  make_repo
  local rc=0
  bash "$RP" plan.md "$BASE" HEAD "$PWD/out.diff" -- >/dev/null 2>&1 || rc=$?
  assert_eq 2 "$rc" "exit code"
}

test_default_outfile_differs_per_pathspec() {
  make_repo
  local one two
  one=$(bash "$RP" plan.md "$BASE" HEAD -- a.txt)
  two=$(bash "$RP" plan.md "$BASE" HEAD -- b.txt)
  [ "$one" != "$two" ] || fail "default OUTFILE identical for different pathspecs: $one"
}

test_no_arguments_exits_2_under_system_bash() {
  make_repo
  local rc=0
  /bin/bash "$RP" >/dev/null 2>&1 || rc=$?
  assert_eq 2 "$rc" "no args"
  rc=0
  /bin/bash "$RP" -- a.txt >/dev/null 2>&1 || rc=$?
  assert_eq 2 "$rc" "only a pathspec"
}
