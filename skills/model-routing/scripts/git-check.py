#!/usr/bin/env python3
"""Report the git state a orchestrator run must not get wrong, as one line of JSON. Read-only,
except --start-run and --end-run, which create or remove the run marker inside the git dir.

Checks: branch and upstream; Stop hooks that auto-commit (project, local and user settings),
and whether they skip orchestrator runs; skip-worktree and assume-unchanged files whose working
copy differs from HEAD (their changes never reach a commit); stray backup files such as
`<file>-E` from `sed -i -E` on macOS; generic auto-save commits since the base. `warnings`
lists only what needs action.

An auto-save Stop hook skips orchestrator runs when its first line is:
  [ -e "$(git rev-parse --git-path chief-run)" ] && exit 0
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

MARKER = "chief-run"
BACKUP_SUFFIXES = ("-E", ".orig", ".bak", ".rej", "~")
AUTO_SAVE_SUBJECT = re.compile(r"auto[- ]?save|checkpoint|^wip\b", re.IGNORECASE)
COMMITS = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
PATH_TOKEN = re.compile(r"[^\s\"';&|()]+")
STOP_EVENTS = ("Stop", "SubagentStop")


def git(repo, *args, check=True):
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True)
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return completed.stdout if completed.returncode == 0 else None


def text(output):
    return output.decode(errors="replace").strip() if output is not None else None


def paths(output):
    return [item.decode(errors="replace") for item in (output or b"").split(b"\0") if item]


def default_base(repo):
    for ref in (text(git(repo, "rev-parse", "--abbrev-ref", "origin/HEAD", check=False)), "main", "master"):
        if ref and ref != "origin/HEAD" and git(repo, "rev-parse", "--verify", "-q", ref, check=False) is not None:
            return ref
    return None


def branch_state(repo):
    branch = text(git(repo, "symbolic-ref", "--short", "-q", "HEAD", check=False)) or "HEAD (detached)"
    upstream = text(git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False))
    state = {"branch": branch, "upstream": upstream}
    if upstream:
        behind, ahead = text(git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")).split()
        state.update(ahead=int(ahead), behind=int(behind))
    return state


def auto_save_commits(repo, merge_base):
    if not merge_base:
        return []
    log = text(git(repo, "log", "--format=%h%x09%s", f"{merge_base}..HEAD")) or ""
    commits = [line.split("\t", 1) for line in log.splitlines() if "\t" in line]
    return [{"sha": sha, "subject": subject} for sha, subject in commits if AUTO_SAVE_SUBJECT.search(subject)]


def head_bytes(repo, path):
    return git(repo, "cat-file", "blob", f"HEAD:{path}", check=False)


def skip_worktree_files(repo):
    files = []
    for entry in paths(git(repo, "ls-files", "-v", "-z")):
        tag, path = entry[0], entry[2:]
        if tag in "Ss":
            flag = "skip-worktree"
        elif tag.islower():
            flag = "assume-unchanged"
        else:
            continue
        try:
            with open(os.path.join(repo, path), "rb") as handle:
                working = handle.read()
        except OSError:
            working = None
        files.append({"path": path, "flag": flag, "differs_from_head": working != head_bytes(repo, path)})
    return files


def stray_files(repo, merge_base):
    tracked = paths(git(repo, "diff", "-z", "--name-only", "--diff-filter=A", merge_base, "HEAD")) if merge_base else []
    untracked = paths(git(repo, "ls-files", "-z", "--others", "--exclude-standard"))
    found = [{"path": path, "tracked": True} for path in tracked]
    found += [{"path": path, "tracked": False} for path in untracked]
    return [entry for entry in found if entry["path"].endswith(BACKUP_SUFFIXES)]


def hook_text(command, repo, home):
    """The hook command plus the contents of any script file it names."""
    expanded = re.sub(r"\$\{?CLAUDE_PROJECT_DIR\}?", repo, command)
    expanded = re.sub(r"\$\{?HOME\}?|(?<![\w/])~(?=/)", home, expanded)
    parts = [command]
    for token in PATH_TOKEN.findall(expanded):
        path = token if os.path.isabs(token) else os.path.join(repo, token)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    parts.append(handle.read(65536))
            except OSError:
                pass
    return "\n".join(parts)


def auto_commit_hooks(repo, home):
    sources = [
        (os.path.join(repo, ".claude", "settings.json"), ".claude/settings.json"),
        (os.path.join(repo, ".claude", "settings.local.json"), ".claude/settings.local.json"),
        (os.path.join(home, ".claude", "settings.json"), "~/.claude/settings.json"),
    ]
    found = []
    for path, label in sources:
        try:
            with open(path, encoding="utf-8") as handle:
                settings = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        events = (settings.get("hooks") or {}) if isinstance(settings, dict) else {}
        for event in STOP_EVENTS:
            for group in events.get(event) or []:
                for hook in (group or {}).get("hooks") or []:
                    command = (hook or {}).get("command") or ""
                    body = hook_text(command, repo, home)
                    if COMMITS.search(body):
                        found.append({"settings": label, "event": event, "command": command, "honors_run_marker": MARKER in body})
    return found


def marker_path(repo):
    return os.path.join(repo, text(git(repo, "rev-parse", "--git-path", MARKER)))


def set_run_marker(repo, active):
    path = marker_path(repo)
    if active:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%dT%H:%M:%S%z\n"))
    elif os.path.exists(path):
        os.remove(path)


def warnings_for(result):
    warnings = []
    for hook in result["auto_commit_hooks"]:
        if not hook["honors_run_marker"]:
            warnings.append(
                f"auto-commit {hook['event']} hook in {hook['settings']} does not skip orchestrator runs: "
                "ask the user to pause it for this run, or to add the run-marker line to it"
            )
    for entry in result["skip_worktree"]:
        if entry["differs_from_head"]:
            warnings.append(
                f"{entry['path']} is {entry['flag']} and differs from HEAD: git add and auto-save skip it, so its "
                "feature changes need a selective commit; never commit a local URL from it"
            )
    for entry in result["stray_files"]:
        where = "committed on this branch" if entry["tracked"] else "untracked"
        warnings.append(f"stray backup file {entry['path']} ({where}): delete it")
    if result["auto_save_commits"]:
        count = len(result["auto_save_commits"])
        warnings.append(f"{count} auto-save commit(s) since {result['base']}: offer the user one descriptive conventional commit in their place")
    return warnings


def report(repo, base=None, home=None):
    home = home or os.path.expanduser("~")
    base = base or default_base(repo)
    merge_base = text(git(repo, "merge-base", base, "HEAD", check=False)) if base else None
    result = {
        **branch_state(repo),
        "base": base,
        "run_marker": os.path.exists(marker_path(repo)),
        "auto_commit_hooks": auto_commit_hooks(repo, home),
        "skip_worktree": skip_worktree_files(repo),
        "stray_files": stray_files(repo, merge_base),
        "auto_save_commits": auto_save_commits(repo, merge_base),
    }
    result["warnings"] = warnings_for(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="branch the work started from (default: origin/HEAD, else main or master)")
    run = parser.add_mutually_exclusive_group()
    run.add_argument("--start-run", action="store_true", help="create the chief-run marker, then report")
    run.add_argument("--end-run", action="store_true", help="remove the chief-run marker, then report")
    parser.add_argument("--warnings-only", action="store_true", help="print only the branch, the run marker and the warnings")
    args = parser.parse_args()

    repo = text(git(".", "rev-parse", "--show-toplevel", check=False))
    if not repo:
        print(json.dumps({"error": "not inside a git repository"}))
        return 2
    if args.start_run or args.end_run:
        set_run_marker(repo, args.start_run)
    result = report(repo, args.base)
    if args.warnings_only:
        result = {key: result[key] for key in ("branch", "run_marker", "warnings")}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
