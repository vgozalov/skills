# shellcheck shell=bash
INSTALL="$REPO_ROOT/install.sh"

setup_repo() { git init -q . && mkdir -p .agents; }
setup_stub() {
  STUB_LOG="$PWD/stub.log"; export STUB_LOG
  cat > stub.sh <<'EOF'
#!/bin/bash
printf '%s|tel=%s|dnt=%s|pwd=%s|\n' "$*" "${DISABLE_TELEMETRY:-}" "${DO_NOT_TRACK:-}" "$(pwd -P)" >> "$STUB_LOG"
exit "${STUB_EXIT:-0}"
EOF
  chmod +x stub.sh; SKILLS_CLI="$PWD/stub.sh"; export SKILLS_CLI
}
call() { sed -n "${1}p" "$STUB_LOG" | cut -d'|' -f1; }
AGENTS="-a claude-code -a codex"

test_hosted_source_installs_last() {
  setup_repo; setup_stub
  printf 'vgozalov/skills *\nexample/source#v1.2.3 *\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add example/source#v1.2.3 $AGENTS -s * -y" "$(call 1)" "other source first"
  assert_eq "add vgozalov/skills $AGENTS -s * -y" "$(call 2)" "hosted last"
  assert_eq "list" "$(call 3)" "list at end"
}
test_hosted_pinned_still_last() {
  setup_repo; setup_stub
  printf 'vgozalov/skills#v1 *\nanthropics/skills pdf\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add vgozalov/skills#v1 $AGENTS -s * -y" "$(call 2)" "pinned hosted last"
}
test_star_is_not_glob_expanded() {
  setup_repo; setup_stub; touch a.txt b.txt
  printf 'example/source#v1.2.3 *\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add example/source#v1.2.3 $AGENTS -s * -y" "$(call 1)" "literal star"
  assert_not_contains "$(cat "$STUB_LOG")" "a.txt" "no filenames"
}
test_named_skills_each_get_s_flag() {
  setup_repo; setup_stub
  printf 'anthropics/skills frontend-design webapp-testing\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add anthropics/skills $AGENTS -s frontend-design -s webapp-testing -y" "$(call 1)" "names"
}
test_pin_hash_is_not_a_comment() {
  setup_repo; setup_stub
  printf '# header\n\n   # indented comment\nexample/source#v1.2.3 frontend-design\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add example/source#v1.2.3 $AGENTS -s frontend-design -y" "$(call 1)" "pinned source kept"
  assert_eq "2" "$(wc -l < "$STUB_LOG" | tr -d ' ')" "only add + list"
}
test_trailing_hash_token_ends_line() {
  setup_repo; setup_stub
  printf 'anthropics/skills pdf # docs only\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add anthropics/skills $AGENTS -s pdf -y" "$(call 1)" "comment dropped"
}
test_runs_at_repo_root_from_subdirectory() {
  setup_repo; setup_stub; mkdir -p sub/deeper
  printf 'anthropics/skills pdf\n' > .agents/skills.txt
  root=$(pwd -P); (cd sub/deeper && bash "$INSTALL")
  assert_contains "$(sed -n 1p "$STUB_LOG")" "pwd=$root|" "cwd is repo root"
}
test_telemetry_disabled_for_cli() {
  setup_repo; setup_stub
  printf 'anthropics/skills pdf\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_contains "$(sed -n 1p "$STUB_LOG")" "|tel=1|dnt=1|" "telemetry env"
}
test_global_uses_g_flag_outside_git() {
  setup_stub; printf 'anthropics/skills pdf\n' > g.txt
  MANIFEST="$PWD/g.txt" bash "$INSTALL" --global
  assert_eq "add anthropics/skills -g $AGENTS -s pdf -y" "$(call 1)" "global add"
  assert_eq "list -g" "$(call 2)" "global list"
}
test_default_global_manifest_is_the_spec_set() {
  setup_stub
  out=$(bash "$INSTALL" --global --dry-run)
  assert_contains "$out" "add anthropics/skills -g $AGENTS -s docx -s pdf -s xlsx -s pptx -s doc-coauthoring -s skill-creator -y" "global.txt anthropics"
  assert_contains "$out" "add anthropics/claude-plugins-official -g $AGENTS -s claude-md-improver -s claude-automation-recommender -y" "global.txt plugin skills"
  [ ! -e "$STUB_LOG" ] || fail "dry run called the CLI"
}
test_missing_manifest_exits_2() {
  setup_repo; setup_stub
  set +e; bash "$INSTALL" 2>err; code=$?; set -e
  assert_eq "2" "$code" "exit code"; assert_contains "$(cat err)" ".agents/skills.txt" "names manifest"
}
test_source_without_skills_exits_2_naming_line() {
  setup_repo; setup_stub; printf '\nanthropics/skills\n' > .agents/skills.txt
  set +e; bash "$INSTALL" 2>err; code=$?; set -e
  assert_eq "2" "$code" "exit code"; assert_contains "$(cat err)" "line 2" "line number"
}
test_cli_failure_stops_and_propagates() {
  setup_repo; setup_stub; printf 'a/b x\nc/d y\n' > .agents/skills.txt
  set +e; STUB_EXIT=3 bash "$INSTALL" 2>/dev/null; code=$?; set -e
  assert_eq "3" "$code" "propagated"; assert_eq "1" "$(wc -l < "$STUB_LOG" | tr -d ' ')" "stopped"
}
test_unknown_argument_exits_2() {
  setup_repo; setup_stub; printf 'a/b x\n' > .agents/skills.txt
  set +e; bash "$INSTALL" --bogus 2>/dev/null; code=$?; set -e
  assert_eq "2" "$code" "exit code"
}
test_outside_git_repo_project_scope_exits_2() {
  setup_stub
  set +e; bash "$INSTALL" 2>/dev/null; code=$?; set -e
  assert_eq "2" "$code" "exit code"
}

# A hosted-source spelling listed BEFORE another source's `*` must still install last.
assert_hosted_last() {
  local spelling=$1
  setup_repo; setup_stub
  printf '%s *\nexample/source#v1.2.3 *\n' "$spelling" > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add example/source#v1.2.3 $AGENTS -s * -y" "$(call 1)" "other source first ($spelling)"
  assert_eq "add $spelling $AGENTS -s * -y" "$(call 2)" "hosted last, source as written ($spelling)"
}
test_hosted_https_url_installs_last() { assert_hosted_last "https://github.com/vgozalov/skills"; }
test_hosted_dot_git_installs_last() { assert_hosted_last "vgozalov/skills.git"; }
test_hosted_trailing_slash_installs_last() { assert_hosted_last "https://github.com/vgozalov/skills/"; }
test_hosted_ssh_installs_last() { assert_hosted_last "git@github.com:vgozalov/skills.git"; }
test_hosted_github_prefix_installs_last() { assert_hosted_last "github:vgozalov/skills"; }
test_hosted_pinned_url_installs_last() {
  setup_repo; setup_stub
  printf 'https://github.com/vgozalov/skills.git#v1 *\nexample/source#v1.2.3 *\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add https://github.com/vgozalov/skills.git#v1 $AGENTS -s * -y" "$(call 2)" "pinned URL hosted last"
}
test_hosted_source_env_in_url_spelling() {
  setup_repo; setup_stub
  printf 'vgozalov/skills *\nexample/source#v1.2.3 *\n' > .agents/skills.txt
  HOSTED_SOURCE="https://github.com/vgozalov/skills.git" bash "$INSTALL"
  assert_eq "add vgozalov/skills $AGENTS -s * -y" "$(call 2)" "HOSTED_SOURCE normalised too"
}
test_crlf_manifest_lines_are_clean() {
  setup_repo; setup_stub
  printf 'anthropics/skills pdf\r\nexample/source#v1.2.3 *\r\n' > .agents/skills.txt
  bash "$INSTALL"
  assert_eq "add anthropics/skills $AGENTS -s pdf -y" "$(call 1)" "CR stripped from skill name"
  assert_eq "add example/source#v1.2.3 $AGENTS -s * -y" "$(call 2)" "CR stripped after star"
}

# --- Run without a clone: `curl -fsSL .../install.sh | bash -s -- [flags]` ---

test_runs_from_stdin_project_scope() {
  setup_repo; setup_stub
  printf 'vgozalov/skills *\nexample/source#v1.2.3 *\n' > .agents/skills.txt
  bash -s -- < "$INSTALL"
  assert_eq "add example/source#v1.2.3 $AGENTS -s * -y" "$(call 1)" "other source first"
  assert_eq "add vgozalov/skills $AGENTS -s * -y" "$(call 2)" "hosted last"
  assert_eq "list" "$(call 3)" "list at end"
}
test_global_from_stdin_fetches_manifest_url() {
  setup_stub; printf 'anthropics/skills pdf\n' > g.txt
  GLOBAL_MANIFEST_URL="file://$PWD/g.txt" bash -s -- --global < "$INSTALL"
  assert_eq "add anthropics/skills -g $AGENTS -s pdf -y" "$(call 1)" "fetched global manifest"
  assert_eq "list -g" "$(call 2)" "global list"
}
test_global_from_stdin_fetch_failure_exits_2() {
  setup_stub
  set +e; GLOBAL_MANIFEST_URL="file://$PWD/missing.txt" bash -s -- --global < "$INSTALL" 2>err; code=$?; set -e
  assert_eq "2" "$code" "exit code"
  assert_contains "$(cat err)" "cannot fetch global manifest" "names the failure"
  [ ! -e "$STUB_LOG" ] || fail "CLI called after a failed fetch"
}
