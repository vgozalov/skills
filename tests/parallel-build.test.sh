# shellcheck shell=bash
# Pins parallel-build and the skills it hands off to: every hand-off resolves inside
# this repo, no outside plugin is named, and our additions to the upstream text stay.

SKILL_DIR="$REPO_ROOT/skills/parallel-build"

test_no_outside_plugin_is_named() {
  local hits
  # The plugin name is split so this file does not mention it either.
  hits=$(git -C "$REPO_ROOT" grep -niE "super""powers" -- . || true)
  [ -z "$hits" ] || fail "outside plugin still named:
$hits"
}

test_every_skill_handed_off_to_ships_here() {
  local skill
  for skill in parallel-build parallel-plans executing-plans requesting-code-review using-git-worktrees \
    finishing-a-development-branch test-driven-development systematic-debugging verification-before-completion; do
    assert_skill_frontmatter "$REPO_ROOT/skills/$skill" || return 1
  done
}

test_every_relative_link_between_skills_resolves() {
  local file link target missing=""
  while IFS= read -r file; do
    for link in $(grep -oE '\.\./[A-Za-z0-9._/-]+\.md' "$file" | sort -u); do
      target="$(dirname "$file")/$link"
      [ -f "$target" ] || missing="$missing
$file -> $link"
    done
  done < <(find "$REPO_ROOT/skills" -name '*.md')
  [ -z "$missing" ] || fail "links that do not resolve:$missing"
}

test_build_workspaces_live_under_parallel_build() {
  local out
  git init -q -b main repo && mkdir -p repo/docs/plans && : > repo/docs/plans/feature.md
  (cd repo && git commit -q --allow-empty -m init)
  out=$(cd repo && bash "$SKILL_DIR/scripts/plan-workspace" docs/plans/feature.md)
  assert_contains "$out" "/.parallel-build/feature" "default workspace"
}

test_our_additions_to_the_upstream_text_stay() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" "### Parallel waves" "parallel waves"
  assert_contains "$body" "## Verification Budget" "verification budget"
  assert_contains "$body" "## Pausing and resuming" "pause and resume"
  assert_contains "$body" "is the run tag" "run tag for the chief's dashboard"
  assert_contains "$(cat "$SKILL_DIR/references/preflight.md")" "group the tasks into waves" "wave grouping"
  assert_contains "$(cat "$SKILL_DIR/references/final-review.md")" "cite it instead of running the suites again" "evidence reuse"
}
