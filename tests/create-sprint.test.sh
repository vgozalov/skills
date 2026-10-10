# shellcheck shell=bash
# Pins the create-sprint skill's contract: valid frontmatter, no hardcoded project paths,
# a bundled example sprint with the expected task shape, and SKILL.md pointing at it.

SKILL_DIR="$REPO_ROOT/skills/create-sprint"

test_frontmatter() {
  assert_skill_frontmatter "$SKILL_DIR"
}

test_no_hardcoded_paths() {
  assert_no_hardcoded_paths "$SKILL_DIR"
}

test_example_task_shape() {
  jq -e 'if type=="array" then .[0] else . end | (keys|sort) == ["category","description","passes","steps"]' \
    "$SKILL_DIR/example/example-prod.json" >/dev/null
}

test_references_bundled_example() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" 'example/example-prod.json' "bundled example reference"
  assert_not_contains "$body" '1-sample-spint' "no repo-specific sample path"
}

test_agents_md_named_before_claude_md() {
  # Byte offsets, not line numbers: both names may share a line.
  local agents claude
  agents=$(grep -bo 'AGENTS.md' "$SKILL_DIR/SKILL.md" | head -1 | cut -d: -f1)
  claude=$(grep -bo 'CLAUDE.md' "$SKILL_DIR/SKILL.md" | head -1 | cut -d: -f1)
  [ -n "$agents" ] || { fail "SKILL.md never names AGENTS.md"; return 1; }
  [ -n "$claude" ] || { fail "SKILL.md never names CLAUDE.md"; return 1; }
  [ "$agents" -lt "$claude" ] || fail "AGENTS.md (offset $agents) must be named before CLAUDE.md (offset $claude)"
}
