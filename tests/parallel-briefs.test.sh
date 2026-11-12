# shellcheck shell=bash
# Pins the parallel-briefs skill: valid frontmatter, the five-block brief template, the three phases.

SKILL="$REPO_ROOT/skills/parallel-briefs"

test_frontmatter() {
  assert_skill_frontmatter "$SKILL"
}

test_brief_template_has_five_blocks() {
  local body heading
  body=$(cat "$SKILL/SKILL.md")
  for heading in \
    '### Your files' \
    '### Do not touch' \
    '### Read first' \
    '### If the shared kit is missing something' \
    '### Verify'; do
    assert_contains "$body" "$heading" "template heading"
  done
}

test_names_three_phases() {
  local body phase
  body=$(cat "$SKILL/SKILL.md")
  for phase in 'Phase 1' 'Phase 2' 'Phase 3'; do
    assert_contains "$body" "$phase" "phase"
  done
}
