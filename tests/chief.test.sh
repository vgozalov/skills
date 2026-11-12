# shellcheck shell=bash
# Pins the chief skill: the pipeline the chief agent and /chief share, its run script and dashboard.

SKILL_DIR="$REPO_ROOT/skills/chief"

test_frontmatter() {
  assert_skill_frontmatter "$SKILL_DIR"
}

test_no_hardcoded_paths() {
  assert_no_hardcoded_paths "$SKILL_DIR"
}

test_rechecks_usage_beyond_intake() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" "at each phase start, before each wave" "usage re-check cadence"
  assert_contains "$body" "spawn_hook" "missing pre-spawn hook is surfaced"
}

test_runs_the_git_check_at_intake_review_pause_and_report() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" "git-check.py --start-run" "intake starts the run marker"
  assert_contains "$body" "git-check.py --end-run" "pause and report end the run marker"
  assert_contains "$body" "before every review" "check before reviews"
  assert_contains "$body" "skip-worktree" "skip-worktree changes reported"
}

test_every_brief_carries_the_run_tag() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" "Run: <run folder>   Task:" "tag format"
  assert_contains "$(cat "$REPO_ROOT/skills/model-routing/references/write-briefs.md")" "Run: <run folder>   Task:" "common block starts with the tag"
}

test_runs_start_without_an_issue_tracker() {
  local body
  body=$(cat "$SKILL_DIR/SKILL.md")
  assert_contains "$body" "--file <path>" "task from a file"
  assert_contains "$body" "--issue <number or URL>" "optional issue import"
  assert_contains "$body" "verbatim" "chat request saved as given"
}

test_report_uses_the_run_summary() {
  assert_contains "$(cat "$SKILL_DIR/SKILL.md")" "chief-run.py summary" "cost summary at report"
}

test_dashboard_is_self_contained() {
  local html
  html=$(cat "$SKILL_DIR/dashboard.html")
  assert_contains "$html" "/board.json" "polls the board"
  assert_not_contains "$html" "<script src=" "no external scripts"
  assert_not_contains "$html" "<link rel=\"stylesheet\"" "no external styles"
}

test_script_unit_tests_pass() {
  local out
  command -v python3 >/dev/null || return 0
  out=$(python3 -B -m unittest discover -s "$SKILL_DIR/tests" 2>&1) || fail "chief unit tests failed:
$out"
}

test_start_phase_and_summary_from_the_command_line() {
  local out run
  command -v python3 >/dev/null || return 0
  git init -q -b main repo
  out=$(cd repo && printf 'Client asks for CSV export\n' | python3 -B "$SKILL_DIR/scripts/chief-run.py" start --title "CSV export")
  assert_contains "$out" '"id": "' "start prints the id"
  run=$(cd repo && ls .chief/runs)
  out=$(cd repo && python3 -B "$SKILL_DIR/scripts/chief-run.py" phase "$run" plan)
  assert_contains "$out" '"phase": "plan"' "phase recorded"
  out=$(cd repo && CLAUDE_CONFIG_DIR="$PWD/none" python3 -B "$SKILL_DIR/scripts/chief-run.py" summary "$run")
  assert_contains "$out" "Claude subtotal: \$0.00" "summary renders with no agents"
  assert_eq "" "$(cd repo && git status --short)" "runs stay out of git"
}
