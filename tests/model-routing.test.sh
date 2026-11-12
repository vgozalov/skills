# shellcheck shell=bash
# Pins the model-routing skill: valid frontmatter, the tier table, its references, and scripts that parse.

SKILL_DIR="$REPO_ROOT/skills/model-routing"

test_frontmatter() {
  assert_skill_frontmatter "$SKILL_DIR"
}

test_no_hardcoded_paths() {
  assert_no_hardcoded_paths "$SKILL_DIR"
}

test_names_tiers_for_both_providers() {
  local body model
  body=$(cat "$SKILL_DIR/SKILL.md")
  for model in Haiku Sonnet Opus Fable gpt-6-luna gpt-6.1-sol gpt-6-astra; do
    assert_contains "$body" "$model" "tier model"
  done
}

test_references_exist_and_are_linked() {
  local body ref
  body=$(cat "$SKILL_DIR/SKILL.md")
  for ref in references/use-codex.md references/write-briefs.md references/report-costs.md; do
    [ -f "$SKILL_DIR/$ref" ] || fail "$ref missing"
    assert_contains "$body" "$ref" "reference link"
  done
}

test_scripts_parse() {
  local script
  command -v python3 >/dev/null || return 0
  for script in "$SKILL_DIR"/scripts/*.py; do
    python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" "$script" \
      || fail "$script does not parse"
  done
}

test_script_unit_tests_pass() {
  local out
  command -v python3 >/dev/null || return 0
  out=$(python3 -B -m unittest discover -s "$SKILL_DIR/tests" 2>&1) || fail "model-routing unit tests failed:
$out"
}

test_run_codex_job_rejects_empty_brief() {
  local out
  command -v python3 >/dev/null || return 0
  out=$(printf '' | python3 "$SKILL_DIR/scripts/run-codex-job.py" --model gpt-6-luna || true)
  assert_contains "$out" '"status": "failed"' "empty brief status"
  assert_contains "$out" 'empty brief' "empty brief error"
}

test_briefs_carry_the_git_hygiene_rules() {
  local body
  body=$(cat "$SKILL_DIR/references/write-briefs.md")
  assert_contains "$body" "Never \`sed -i\`" "sed -i forbidden"
  assert_contains "$body" "Skip-worktree files you may touch" "skip-worktree files named"
  assert_contains "$body" "files you created outside" "stray files reported"
  assert_contains "$body" "git-check.py" "git steward uses the check"
}

test_skill_documents_the_run_marker_for_auto_save_hooks() {
  assert_contains "$(cat "$SKILL_DIR/SKILL.md")" 'git rev-parse --git-path chief-run' "hook snippet"
}

test_git_check_reports_json_outside_a_orchestrator_run() {
  local out
  command -v python3 >/dev/null || return 0
  git init -q -b main repo && (cd repo && git commit -q --allow-empty -m init)
  out=$(cd repo && python3 -B "$SKILL_DIR/scripts/git-check.py" --base main)
  assert_contains "$out" '"branch": "main"' "branch"
  assert_contains "$out" '"warnings": []' "clean repo"
}

test_git_check_warnings_only_is_compact() {
  local out
  command -v python3 >/dev/null || return 0
  git init -q -b main repo && (cd repo && git commit -q --allow-empty -m init)
  out=$(cd repo && python3 -B "$SKILL_DIR/scripts/git-check.py" --base main --warnings-only)
  assert_eq '{"branch": "main", "run_marker": false, "warnings": []}' "$out" "warnings-only output"
}
