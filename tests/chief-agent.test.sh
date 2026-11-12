# shellcheck shell=bash
# Pins the chief agent: frontmatter, its tool list, and the skills it depends on.

AGENT="$REPO_ROOT/agents/chief.md"

test_frontmatter() {
  local head
  [ -f "$AGENT" ] || { fail "$AGENT missing"; return 1; }
  head=$(awk 'NR == 1 && $0 != "---" { exit } NR > 1 && $0 == "---" { exit } { print }' "$AGENT")
  assert_contains "$head" 'name: chief' "name"
  assert_contains "$head" 'description:' "description"
  assert_contains "$head" 'model: opus' "default model"
  assert_contains "$head" 'tools: Agent, SendMessage, ListAgents, Skill, AskUserQuestion, Bash' "tools"
}

test_depends_on_skills_shipped_here() {
  local body skill
  body=$(cat "$AGENT")
  for skill in chief model-routing parallel-plans parallel-briefs parallel-build; do
    assert_contains "$body" "$skill" "skill dependency"
    [ -f "$REPO_ROOT/skills/$skill/SKILL.md" ] || fail "skills/$skill is not shipped in this repo"
  done
}

test_loads_the_conduct_skill_for_its_pipeline() {
  local body
  body=$(cat "$AGENT")
  assert_contains "$body" "load the \`chief\` skill and follow it" "pipeline lives in the skill"
  assert_contains "$body" "chief-run.py" "bash allowance covers the run script"
  assert_not_contains "$body" "## Pipeline" "no second copy of the pipeline"
}

test_no_hardcoded_paths() {
  local matches
  matches=$(grep -nE 'context/|docs/plans' "$AGENT" || true)
  [ -z "$matches" ] || fail "hardcoded path(s): $matches"
}
