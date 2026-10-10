# shellcheck shell=bash
# Pins the wrap-up skill's contract: valid frontmatter, no hardcoded project paths,
# and path resolution through the repo instructions file's "## Skill paths" block.

SKILL_DIR="$REPO_ROOT/skills/wrap-up"

test_frontmatter() {
  assert_skill_frontmatter "$SKILL_DIR"
}

test_no_hardcoded_paths() {
  assert_no_hardcoded_paths "$SKILL_DIR"
}

test_reads_skill_paths_keys() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" '## Skill paths' "skill paths heading"
  assert_contains "$body" "\`memory\`" "memory key"
  assert_contains "$body" "\`learnings\`" "learnings key"
}
