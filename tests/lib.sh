# shellcheck shell=bash
# Shared assertions for tests/*.test.sh. Sourced by tests/run.sh; bash 3.2 compatible.
# REPO_ROOT is exported by the runner.

fail() {
  printf '  FAIL: %s\n' "$1" >&2
  return 1
}

assert_eq() {
  local expected=$1 actual=$2 label=$3
  [ "$expected" = "$actual" ] || fail "$label: expected [$expected], got [$actual]"
}

assert_contains() {
  local haystack=$1 needle=$2 label=$3
  case $haystack in
    *"$needle"*) return 0 ;;
  esac
  fail "$label: expected to contain [$needle], got [$haystack]"
}

assert_not_contains() {
  local haystack=$1 needle=$2 label=$3
  case $haystack in
    *"$needle"*) fail "$label: expected NOT to contain [$needle], got [$haystack]" ;;
  esac
  return 0
}

# SKILL_DIR/SKILL.md exists, name: equals the directory name, description starts with "Use when".
# Folded/literal descriptions (> >- | |-): the first non-empty line after "description:" is used.
assert_skill_frontmatter() {
  local dir=$1 file name expected desc
  file="$dir/SKILL.md"
  [ -f "$file" ] || { fail "$file does not exist"; return 1; }
  expected=$(basename "$dir")
  name=$(awk '
    NR == 1 { if ($0 != "---") exit; next }
    $0 == "---" { exit }
    /^name:/ { sub(/^name:[ \t]*/, ""); gsub(/^["'\'']|["'\'']$/, ""); print; exit }
  ' "$file")
  [ "$name" = "$expected" ] || { fail "$file: name [$name] != directory [$expected]"; return 1; }
  desc=$(awk '
    NR == 1 { if ($0 != "---") exit; next }
    $0 == "---" { exit }
    found && $0 ~ /[^ \t]/ { sub(/^[ \t]+/, ""); print; exit }
    /^description:/ {
      v = $0; sub(/^description:[ \t]*/, "", v)
      if (v ~ /^[>|][-+]?[ \t]*$/ || v == "") { found = 1; next }
      gsub(/^["'\'']/, "", v); print v; exit
    }
  ' "$file")
  case $desc in
    "Use when"*) return 0 ;;
  esac
  fail "$file: description must start with 'Use when', got [$desc]"
}

# No file under SKILL_DIR may hardcode a project path (context/, docs/plans, sprints/1-sample)
# on a line whose CONTENT does not also say "default" (the file path is never consulted).
assert_no_hardcoded_paths() {
  local dir=$1 file matches hits=""
  while IFS= read -r file; do
    # grep -n output is "LINE:CONTENT", so filtering it never looks at the path.
    matches=$(grep -nE 'context/|docs/plans|sprints/1-sample' "$file" 2>/dev/null | grep -v 'default' || true)
    [ -z "$matches" ] || hits="$hits$(printf '%s\n' "$matches" | sed "s|^|$file:|")
"
  done < <(find "$dir" -type f)
  [ -z "$hits" ] || fail "hardcoded path(s) without 'default':
$hits"
}
