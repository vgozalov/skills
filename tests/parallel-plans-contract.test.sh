# shellcheck shell=bash
# Pins the parallel-plans skill: valid frontmatter, and an embedded ownership example
# that the sdd ownership-check script parses and enforces as documented.

SKILL="$REPO_ROOT/skills/parallel-plans"
OC="$REPO_ROOT/skills/parallel-agent-development/scripts/ownership-check"

# make_example_repo: git repo whose plan.md is the SKILL.md ownership example; sets BASE.
make_example_repo() {
  git init -q .
  awk '
    /<!-- ownership-example:end -->/ { on = 0 }
    on { print }
    /<!-- ownership-example:start -->/ { on = 1 }
  ' "$SKILL/SKILL.md" > plan.md
  [ -s plan.md ] || { fail "no ownership example between the markers in SKILL.md"; return 1; }
  git add plan.md
  git commit -q -m base
  BASE=$(git rev-parse HEAD)
}

# commit_file PATH: commit one new file.
commit_file() {
  mkdir -p "$(dirname "$1")"
  echo x > "$1"
  git add -- "$1"
  git commit -q -m "add $1"
}

test_skill_frontmatter() {
  assert_skill_frontmatter "$SKILL"
}

test_ownership_example_parses_clean() {
  local out rc=0
  make_example_repo
  commit_file src/feature-a/x.ts
  commit_file src/feature-b/y.ts
  out=$(bash "$OC" plan.md "$BASE" HEAD 2,3 2>&1) || rc=$?
  assert_eq 0 "$rc" "exit code"
  assert_eq "ownership-check: 2 commit(s) clean" "$out" "stdout"
}

test_ownership_example_rejects_frozen() {
  local out rc=0
  make_example_repo
  commit_file src/registry.ts
  out=$(bash "$OC" plan.md "$BASE" HEAD 2,3 2>&1) || rc=$?
  assert_eq 1 "$rc" "exit code"
  assert_contains "$out" "src/registry.ts: frozen during waves" "violation line"
}

test_mit_notice_travels_with_derived_skills() {
  local s
  for s in parallel-agent-development parallel-plans; do
    [ -f "$REPO_ROOT/skills/$s/LICENSE-third-party.txt" ] || { fail "skills/$s/LICENSE-third-party.txt missing"; return 1; }
    cmp -s "$REPO_ROOT/LICENSES/third-party-MIT.txt" "$REPO_ROOT/skills/$s/LICENSE-third-party.txt" \
      || { fail "skills/$s/LICENSE-third-party.txt differs from LICENSES/third-party-MIT.txt"; return 1; }
  done
}
