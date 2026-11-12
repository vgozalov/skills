#!/usr/bin/env python3
"""Claude Code PreToolUse hook: before a Claude agent or a Codex job is spawned, add the
current usage of both accounts and the routing pick to the orchestrator's context.

It never blocks or changes the spawn; some jobs need one provider's model or capability.

Register it once per project in .claude/settings.json under "hooks" (adjust the path for a
global install in ~/.claude/skills):

  "PreToolUse": [
    {"matcher": "Agent|Task", "hooks": [{"type": "command", "timeout": 75,
      "command": "python3 -B \"$CLAUDE_PROJECT_DIR/.claude/skills/model-routing/scripts/usage-before-spawn.py\""}]},
    {"matcher": "Bash", "hooks": [{"type": "command", "timeout": 75, "if": "Bash(*run-codex-job.py*)",
      "command": "python3 -B \"$CLAUDE_PROJECT_DIR/.claude/skills/model-routing/scripts/usage-before-spawn.py\""}]}
  ]
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

CACHE_SECONDS = 120
CODEX_JOB_LAUNCH = re.compile(
    r"(?:python3?(?:\s+-(?![cm]\b)\S+)*\s+|(?:^|[;&|\n])\s*)"
    r"(?:\"[^\"\n]*|'[^'\n]*|[^\s\"';&|]*)run-codex-job\.py"
)
CODEX_MODEL_FLAG = re.compile(r"--model[ =](\S+)")


def load_usage_check():
    path = Path(__file__).resolve().parent / "check-account-usage.py"
    spec = importlib.util.spec_from_file_location("check_account_usage", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe_spawn(hook_input):
    """(provider, model) for a spawn, or None when the tool call spawns nothing."""
    tool_input = hook_input.get("tool_input") or {}
    if hook_input.get("tool_name") in ("Agent", "Task"):
        return "claude", tool_input.get("model") or "default"
    command = tool_input.get("command") or ""
    if hook_input.get("tool_name") == "Bash" and CODEX_JOB_LAUNCH.search(command):
        model = CODEX_MODEL_FLAG.search(command)
        return "chatgpt", model.group(1) if model else "default"
    return None


def format_reading(name, reading):
    if not reading or reading.get("5h") is None:
        return f"{name} unreadable"
    blocked = " (blocked)" if reading.get("blocked") else ""
    return f"{name} 5h {reading['5h']:g}% / week {reading.get('week', 0):g}%{blocked}"


def usage_note(readings, pick, why, spawn):
    provider, model = spawn
    accounts = ", ".join(format_reading(name, reading) for name, reading in readings.items())
    if provider == pick:
        fit = "matches the pick"
    else:
        fit = "differs from the pick, which is fine when the user asked for it or the job needs this provider's model or capability"
    return f"Usage before this spawn: {accounts}. Routing: pick {pick} ({why}). This spawn runs on {provider} ({model}) and {fit}."


def hook_output(note):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": note}}


def main():
    try:
        spawn = describe_spawn(json.load(sys.stdin))
        if spawn is None:
            return 0
        usage = load_usage_check()
        readings = usage.read_usage(CACHE_SECONDS)
        pick, why = usage.pick_provider(readings, "claude")
        print(json.dumps(hook_output(usage_note(readings, pick, why, spawn))))
    except Exception as error:
        print(f"usage check before spawn failed: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
