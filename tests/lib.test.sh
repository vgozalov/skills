# shellcheck shell=bash
# Pins the behaviour of tests/lib.sh helpers that other test files depend on.

make_skill() { # DIR NAME DESCRIPTION-LINE
  mkdir -p "$1"
  printf -- '---\nname: %s\ndescription: %s\n---\nbody\n' "$2" "$3" > "$1/SKILL.md"
}

test_paths_clean_skill_passes() {
  make_skill ok ok "Use when x"
  printf 'nothing special\n' > ok/ref.md
  assert_no_hardcoded_paths ok
}
test_paths_hardcoded_line_fails_naming_file_and_line() {
  make_skill bad bad "Use when x"
  printf 'ok\nsee docs/plans/foo\n' > bad/ref.md
  set +e; out=$(assert_no_hardcoded_paths bad 2>&1); code=$?; set -e
  assert_eq "1" "$code" "fails"
  assert_contains "$out" "bad/ref.md:2:" "names file and line"
}
test_paths_each_pattern_is_detected() {
  for p in 'context/x' 'docs/plans' 'sprints/1-sample'; do
    mkdir -p "p"; printf 'see %s\n' "$p" > p/a.md
    set +e; assert_no_hardcoded_paths p 2>/dev/null; code=$?; set -e
    assert_eq "1" "$code" "pattern $p"
  done
}
test_paths_default_in_line_content_exempts_that_line() {
  mkdir -p s; printf 'the default is context/foo\n' > s/a.md
  assert_no_hardcoded_paths s
}
test_paths_default_in_file_path_does_not_exempt() {
  mkdir -p default-skill; printf 'see context/foo\n' > default-skill/a.md
  set +e; assert_no_hardcoded_paths default-skill 2>/dev/null; code=$?; set -e
  assert_eq "1" "$code" "path containing default must still fail"
}
test_paths_default_in_directory_name_does_not_exempt() {
  mkdir -p s/default/sub; printf 'see sprints/1-sample\n' > s/default/sub/a.md
  set +e; assert_no_hardcoded_paths s 2>/dev/null; code=$?; set -e
  assert_eq "1" "$code" "directory named default must still fail"
}

test_frontmatter_valid_skill_passes() {
  make_skill good good "Use when testing"
  assert_skill_frontmatter good
}
test_frontmatter_folded_description_passes() {
  mkdir -p fold
  printf -- '---\nname: fold\ndescription: >\n  Use when folded\n  more text\n---\n' > fold/SKILL.md
  assert_skill_frontmatter fold
}
test_frontmatter_name_directory_mismatch_fails() {
  make_skill dirname othername "Use when x"
  set +e; out=$(assert_skill_frontmatter dirname 2>&1); code=$?; set -e
  assert_eq "1" "$code" "fails"
  assert_contains "$out" "othername" "names the bad name"
}
test_frontmatter_description_must_start_with_use_when() {
  make_skill d d "Does things"
  set +e; assert_skill_frontmatter d 2>/dev/null; code=$?; set -e
  assert_eq "1" "$code" "fails"
}
test_frontmatter_missing_skill_md_fails() {
  mkdir -p empty
  set +e; assert_skill_frontmatter empty 2>/dev/null; code=$?; set -e
  assert_eq "1" "$code" "fails"
}
