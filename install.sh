#!/bin/bash
# Install the skills listed in a manifest through the `skills` CLI.
#
# Usage: install.sh [--global] [--dry-run]
#        curl -fsSL https://raw.githubusercontent.com/vgozalov/skills/main/install.sh | bash -s -- [flags]
#   (default)  project scope: manifest is <git toplevel>/.agents/skills.txt
#   --global   user scope (-g): manifest is global.txt next to this script, or
#              fetched from GLOBAL_MANIFEST_URL when run from stdin
#   --dry-run  print the commands instead of running them
#
# Env: SKILLS_CLI (default "npx -y skills@1.7.2"), HOSTED_SOURCE (default
#      "vgozalov/skills"; its lines are installed last), MANIFEST (override path),
#      GLOBAL_MANIFEST_URL (default: this repo's global.txt on main).
#
# Manifest lines: "<source>[#tag] <skill|*>... [# comment]"; blank lines and
# lines starting with "#" are skipped.
set -euo pipefail
set -f # a literal `*` in the manifest must never be glob-expanded

export DISABLE_TELEMETRY=1 DO_NOT_TRACK=1

SKILLS_CLI=${SKILLS_CLI:-npx -y skills@1.7.2}
HOSTED_SOURCE=${HOSTED_SOURCE:-vgozalov/skills}
GLOBAL_MANIFEST_URL=${GLOBAL_MANIFEST_URL:-https://raw.githubusercontent.com/vgozalov/skills/main/global.txt}

# Empty when the script arrives on stdin (`curl ... | bash`), so there is no clone to read from.
SCRIPT_DIR=
if [ -f "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fi

die() {
  echo "install.sh: $1" >&2
  exit 2
}

global=0
dry_run=0
for arg in "$@"; do
  case $arg in
    --global) global=1 ;;
    --dry-run) dry_run=1 ;;
    *) die "unknown argument: $arg (usage: install.sh [--global] [--dry-run])" ;;
  esac
done

# A relative MANIFEST is relative to where the user ran us, not the repo root.
if [ -n "${MANIFEST:-}" ]; then
  case $MANIFEST in
    /*) ;;
    *) MANIFEST="$PWD/$MANIFEST" ;;
  esac
fi

if [ "$global" -eq 1 ]; then
  if [ -z "${MANIFEST:-}" ] && [ -n "$SCRIPT_DIR" ]; then
    MANIFEST=$SCRIPT_DIR/global.txt
  elif [ -z "${MANIFEST:-}" ]; then
    MANIFEST=$(mktemp)
    trap 'rm -f "$MANIFEST"' EXIT
    curl -fsSL "$GLOBAL_MANIFEST_URL" -o "$MANIFEST" 2>/dev/null ||
      die "cannot fetch global manifest: $GLOBAL_MANIFEST_URL"
  fi
else
  root=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository (use --global for user scope)"
  cd "$root"
  MANIFEST=${MANIFEST:-$root/.agents/skills.txt}
fi
[ -f "$MANIFEST" ] || die "manifest not found: $MANIFEST"

# norm_source SRC: canonical form for comparing sources only (the CLI still gets
# the source exactly as written): no #ref, no URL/scp/github: prefix, no .git, no trailing /.
norm_source() {
  local s=${1%%#*}
  s=${s#https://github.com/}
  s=${s#git@github.com:}
  s=${s#github:}
  s=${s%/}
  s=${s%.git}
  s=${s%/}
  printf '%s' "$s"
}
hosted_norm=$(norm_source "$HOSTED_SOURCE")

# Entries are "source skill skill..." strings, split again when run.
plain=()
hosted=()
lineno=0
while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))
  line=${line%$'\r'}
  read -ra tokens <<< "$line"
  [ "${#tokens[@]}" -gt 0 ] || continue
  case ${tokens[0]} in '#'*) continue ;; esac

  entry=${tokens[0]}
  skills=0
  for tok in "${tokens[@]:1}"; do
    case $tok in '#'*) break ;; esac
    entry="$entry $tok"
    skills=$((skills + 1))
  done
  [ "$skills" -gt 0 ] || die "$MANIFEST: line $lineno: source '${tokens[0]}' lists no skills"

  if [ "$(norm_source "${tokens[0]}")" = "$hosted_norm" ]; then
    hosted+=("$entry")
  else
    plain+=("$entry")
  fi
done < "$MANIFEST"

read -ra cli <<< "$SKILLS_CLI"
scope=()
[ "$global" -eq 1 ] && scope=(-g)

run() {
  if [ "$dry_run" -eq 1 ]; then
    echo "skills $*"
    return 0
  fi
  local rc=0
  "${cli[@]}" "$@" || rc=$?
  [ "$rc" -eq 0 ] || exit "$rc"
}

add_entry() {
  local parts source args
  read -ra parts <<< "$1"
  source=${parts[0]}
  args=(add "$source" ${scope[@]+"${scope[@]}"} -a claude-code -a codex)
  for name in "${parts[@]:1}"; do
    args+=(-s "$name")
  done
  run "${args[@]}" -y
}

for entry in ${plain[@]+"${plain[@]}"}; do
  add_entry "$entry"
done
for entry in ${hosted[@]+"${hosted[@]}"}; do
  add_entry "$entry"
done

run list ${scope[@]+"${scope[@]}"}
