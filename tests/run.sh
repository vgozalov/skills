#!/bin/bash
# Test runner: bash tests/run.sh [FILE...]
# Runs every test_* function of each tests/*.test.sh (or the given files) in its own
# subshell and temp directory, then shellcheck. Exits 1 if anything failed.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
export REPO_ROOT

# Hermetic git: fixture commits must not depend on the user's git config.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

RUN_TMP=$(mktemp -d)
trap 'rm -rf "$RUN_TMP"' EXIT

failed=0
n=0

files=()
if [ "$#" -gt 0 ]; then
  for f in "$@"; do
    case $f in
      /*) files+=("$f") ;;
      *) files+=("$PWD/$f") ;;
    esac
  done
else
  for f in "$REPO_ROOT"/tests/*.test.sh; do
    [ -e "$f" ] && files+=("$f")
  done
fi

for file in ${files[@]+"${files[@]}"}; do
  label=$(basename "$file")
  if ! names=$(
    set -euo pipefail
    # shellcheck source=/dev/null
    source "$REPO_ROOT/tests/lib.sh"
    # shellcheck source=/dev/null
    source "$file"
    declare -F | awk '$3 ~ /^test_/ { print $3 }'
  ) 2>"$RUN_TMP/load.log"; then
    echo "FAIL $label::(load)"
    sed 's/^/    /' "$RUN_TMP/load.log"
    failed=1
    continue
  fi
  for t in $names; do
    n=$((n + 1))
    dir="$RUN_TMP/t$n"
    mkdir "$dir"
    set +e
    (
      set -euo pipefail
      cd "$dir"
      # shellcheck source=/dev/null
      source "$REPO_ROOT/tests/lib.sh"
      # shellcheck source=/dev/null
      source "$file"
      "$t"
    ) >"$RUN_TMP/out.log" 2>&1
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
      echo "PASS $label::$t"
    else
      echo "FAIL $label::$t"
      sed 's/^/    /' "$RUN_TMP/out.log"
      failed=1
    fi
  done
done

if command -v shellcheck >/dev/null 2>&1; then
  targets=()
  for f in "$REPO_ROOT/install.sh" "$REPO_ROOT"/scripts/* "$REPO_ROOT"/skills/*/scripts/*; do
    [ -f "$f" ] && targets+=("$f")
  done
  if [ "${#targets[@]}" -gt 0 ]; then
    if shellcheck -x "${targets[@]}"; then
      echo "PASS shellcheck (${#targets[@]} files)"
    else
      echo "FAIL shellcheck"
      failed=1
    fi
  fi
fi

exit "$failed"
