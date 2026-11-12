#!/usr/bin/env python3
"""Print how much of each account's usage is spent, and which provider the next job should use.

Neither check spends a model turn: Claude is read from `claude -p /usage`, ChatGPT from the
Codex app-server. The orchestrator's own provider is preferred until it has used
SWITCH_AT_5H_USED percent of its 5-hour window; past that, jobs move to another provider so
the orchestrator keeps the rest for its own turns.
"""
import argparse
import fcntl
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

TIMEOUT_SECONDS = 60
SWITCH_AT_5H_USED = 60
NEAR_LIMIT_USED = 90
CACHE_PATH = os.path.join(tempfile.gettempdir(), "model-routing-usage.json")
CLAUDE_WINDOW_LINE = re.compile(r"^Current (.+?): (\d+(?:\.\d+)?)% used", re.MULTILINE)
CLAUDE_WINDOW_NAMES = {"session": "5h", "week (all models)": "week"}


def read_claude():
    try:
        completed = subprocess.run(
            ["claude", "-p", "/usage", "--model", "haiku", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=tempfile.gettempdir(),
        )
        report = json.loads(completed.stdout).get("result") or ""
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"error": f"claude /usage unreadable: {error}"}

    windows = {
        CLAUDE_WINDOW_NAMES.get(label.strip(), label.strip()): float(used)
        for label, used in CLAUDE_WINDOW_LINE.findall(report)
    }
    if "5h" not in windows:
        return {"error": "claude /usage reported no 5-hour window"}
    return windows


def request_codex_rate_limits():
    process = subprocess.Popen(
        ["codex", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(line) for line in process.stdout], daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def wait_for(request_id, deadline):
        while time.time() < deadline:
            try:
                message = json.loads(lines.get(timeout=max(0.1, deadline - time.time())))
            except (queue.Empty, json.JSONDecodeError):
                continue
            if message.get("id") == request_id:
                return message
        return None

    try:
        deadline = time.time() + TIMEOUT_SECONDS
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "model-routing", "version": "1"}}})
        wait_for(1, deadline)
        send({"method": "initialized"})
        send({"id": 2, "method": "account/rateLimits/read", "params": {"excludeResetCreditDetails": True}})
        return wait_for(2, deadline)
    finally:
        process.terminate()


def read_chatgpt():
    try:
        response = request_codex_rate_limits()
    except OSError as error:
        return {"error": f"codex not runnable: {error}"}
    result = (response or {}).get("result")
    if not result:
        return {"error": "no answer from codex app-server"}

    limits = result.get("rateLimits") or {}
    now = time.time()
    windows = {}
    for name, window in (("5h", limits.get("primary")), ("week", limits.get("secondary"))):
        if window and window.get("usedPercent") is not None:
            reset_passed = window.get("resetsAt") and window["resetsAt"] <= now
            windows[name] = 0.0 if reset_passed else float(window["usedPercent"])
    if "5h" not in windows:
        return {"error": "codex app-server reported no 5-hour window"}
    if result.get("ordinaryUsageAllowed") is False or limits.get("rateLimitReachedType"):
        windows["blocked"] = True
    return windows


READERS = {"claude": read_claude, "chatgpt": read_chatgpt}


def read_usage(max_age, cache_path=CACHE_PATH, readers=READERS):
    """Readings for every provider, reusing a cached set younger than max_age seconds."""

    def cached():
        try:
            if time.time() - os.path.getmtime(cache_path) < max_age:
                with open(cache_path, encoding="utf-8") as handle:
                    return json.load(handle)
        except (OSError, json.JSONDecodeError):
            pass
        return None

    readings = cached()
    if readings is not None:
        return readings
    with open(cache_path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        readings = cached()
        if readings is None:
            with ThreadPoolExecutor(max_workers=len(readers)) as pool:
                futures = {name: pool.submit(reader) for name, reader in readers.items()}
                readings = {name: future.result() for name, future in futures.items()}
            temporary = f"{cache_path}.{os.getpid()}"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(readings, handle)
            os.replace(temporary, cache_path)
    return readings


def spawn_hook_registered(project, home):
    """True when usage-before-spawn.py is registered in the project's or the user's settings."""
    for path in (
        os.path.join(project, ".claude", "settings.json"),
        os.path.join(project, ".claude", "settings.local.json"),
        os.path.join(home, ".claude", "settings.json"),
    ):
        try:
            with open(path, encoding="utf-8") as handle:
                if "usage-before-spawn.py" in handle.read():
                    return True
        except OSError:
            continue
    return False


def detect_orchestrator(environment):
    return "claude" if environment.get("CLAUDECODE") == "1" else None


def is_readable(reading):
    return bool(reading) and reading.get("5h") is not None


def has_room(reading):
    return is_readable(reading) and not reading.get("blocked") and max(reading["5h"], reading.get("week", 0)) < NEAR_LIMIT_USED


def describe(name, reading):
    if not is_readable(reading):
        return f"{name} unreadable"
    blocked = ", blocked" if reading.get("blocked") else ""
    return f"{name} at {reading['5h']:g}% of its 5-hour window, {reading.get('week', 0):g}% of its week{blocked}"


def pick_provider(readings, orchestrator):
    """Return (provider or "ask", reason) for the next job."""
    own = readings.get(orchestrator)
    if orchestrator in readings and not is_readable(own):
        return "ask", f"the orchestrator's own usage is unreadable: {(own or {}).get('error', 'no reading')}"

    if has_room(own) and own["5h"] < SWITCH_AT_5H_USED:
        return orchestrator, f"{describe(orchestrator, own)}; the orchestrator's provider is used below {SWITCH_AT_5H_USED}%"

    others = sorted(
        (name for name, reading in readings.items() if name != orchestrator and has_room(reading)),
        key=lambda name: readings[name]["5h"],
    )
    if others:
        chosen = others[0]
        if orchestrator in readings:
            reason = f"{describe(orchestrator, own)}, past the {SWITCH_AT_5H_USED}% switch point or near a limit; {describe(chosen, readings[chosen])}"
        else:
            reason = f"{describe(chosen, readings[chosen])}, the lowest 5-hour use"
        return chosen, reason

    if has_room(own):
        return orchestrator, f"{describe(orchestrator, own)}; no other provider has room"
    return "ask", "; ".join(describe(name, reading) for name, reading in readings.items()) + "; every provider is near a limit"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator", "--conductor", dest="orchestrator", help="provider the orchestrator runs on: claude, chatgpt, gemini, ... (auto-detected inside Claude Code)")
    parser.add_argument("--max-age", type=float, default=0, help="reuse a cached reading younger than this many seconds")
    args = parser.parse_args()

    orchestrator = args.orchestrator or detect_orchestrator(os.environ)
    if not orchestrator:
        print("pass --orchestrator <provider you run on>, e.g. --orchestrator chatgpt", file=sys.stderr)
        return 2
    readings = read_usage(args.max_age)
    pick, why = pick_provider(readings, orchestrator)
    result = {"orchestrator": orchestrator, **readings, "pick": pick, "why": why}
    if orchestrator == "claude":
        project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        registered = spawn_hook_registered(project, os.path.expanduser("~"))
        result["spawn_hook"] = "registered" if registered else "missing"
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
