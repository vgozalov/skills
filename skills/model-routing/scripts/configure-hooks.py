#!/usr/bin/env python3
"""Register the model-routing hooks in a Claude Code settings file, idempotently.

  configure-hooks.py                  the project's .claude/settings.json (run from the repo)
  configure-hooks.py --global         ~/.claude/settings.json
  configure-hooks.py --patch-auto-save   also make auto-committing Stop hooks skip chief runs
  configure-hooks.py --dry-run        print what would change, write nothing

Adds the PreToolUse hook that runs usage-before-spawn.py before every Agent spawn and every
run-codex-job.py launch. Every other setting is kept. An auto-committing Stop hook in the same
file is reported, and changed only with --patch-auto-save (ask the user first): its command gets
the line that makes it skip while a chief run is active. Prints one line of JSON.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK_SCRIPT = "usage-before-spawn.py"
MARKER_GUARD = '[ -e "$(git rev-parse --git-path chief-run)" ] && exit 0; '
COMMITS = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
STOP_EVENTS = ("Stop", "SubagentStop")


def usage_hook_entries(script_path):
    command = f'python3 -B "{script_path}"'
    return [
        {"matcher": "Agent|Task", "hooks": [{"type": "command", "timeout": 75, "command": command}]},
        {"matcher": "Bash", "hooks": [{"type": "command", "timeout": 75, "if": "Bash(*run-codex-job.py*)", "command": command}]},
    ]


def hook_script_text(command, base):
    """The command plus any script file it names, so a hook that calls a script is judged by the script."""
    parts = [command]
    expanded = command.replace("$CLAUDE_PROJECT_DIR", base).replace("${CLAUDE_PROJECT_DIR}", base)
    for token in re.findall(r"[^\s\"';&|()]+", expanded):
        path = token if os.path.isabs(token) else os.path.join(base, token)
        if os.path.isfile(path):
            try:
                parts.append(Path(path).read_text(errors="replace")[:65536])
            except OSError:
                pass
    return "\n".join(parts)


def configure(settings_path, script_path, patch_auto_save=False, dry_run=False):
    path = Path(settings_path)
    try:
        settings = json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError as error:
        raise ValueError(f"{settings_path} is not valid JSON ({error}); fix it before configuring hooks")
    hooks = settings.setdefault("hooks", {})
    report = {"settings": str(path), "usage_hook_added": False, "auto_save_hooks_patched": 0, "auto_save_hooks_unpatched": 0}

    if HOOK_SCRIPT not in json.dumps(hooks.get("PreToolUse", [])):
        hooks.setdefault("PreToolUse", []).extend(usage_hook_entries(script_path))
        report["usage_hook_added"] = True

    base = str(path.parent.parent)
    for event in STOP_EVENTS:
        for group in hooks.get(event) or []:
            for hook in (group or {}).get("hooks") or []:
                command = (hook or {}).get("command") or ""
                text = hook_script_text(command, base)
                if not COMMITS.search(text) or "chief-run" in text:
                    continue
                if patch_auto_save:
                    hook["command"] = MARKER_GUARD + command
                    report["auto_save_hooks_patched"] += 1
                else:
                    report["auto_save_hooks_unpatched"] += 1

    changed = report["usage_hook_added"] or report["auto_save_hooks_patched"]
    if changed and not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2) + "\n")
    report["written"] = bool(changed and not dry_run)
    return report


def default_script_path(global_scope, project):
    own = Path(__file__).resolve().parent / HOOK_SCRIPT
    if global_scope:
        return str(own)
    installed = Path(project) / ".claude" / "skills" / "model-routing" / "scripts" / HOOK_SCRIPT
    if installed.exists():
        return "$CLAUDE_PROJECT_DIR/.claude/skills/model-routing/scripts/" + HOOK_SCRIPT
    return str(own)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--global", dest="global_scope", action="store_true", help="configure ~/.claude/settings.json")
    parser.add_argument("--patch-auto-save", action="store_true", help="make auto-committing Stop hooks skip chief runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.global_scope:
        config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        settings_path, project = os.path.join(config, "settings.json"), None
    else:
        completed = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if completed.returncode != 0:
            print("configure-hooks: run it inside the project's repository, or pass --global", file=sys.stderr)
            return 2
        project = completed.stdout.strip()
        settings_path = os.path.join(project, ".claude", "settings.json")
    try:
        report = configure(settings_path, default_script_path(args.global_scope, project), args.patch_auto_save, args.dry_run)
    except ValueError as error:
        print(f"configure-hooks: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
