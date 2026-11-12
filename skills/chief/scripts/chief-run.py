#!/usr/bin/env python3
"""One chief run: its task, its phases, and every agent that worked on it, Claude and Codex.

  chief-run.py start [--title T] [--file F | --issue REF]   task text on stdin otherwise
  chief-run.py phase <run> <phase> [--plan P] [--workspace W]
  chief-run.py summary <run>                                 cost table for the report
  chief-run.py board                                         the dashboard's data, as JSON
  chief-run.py serve [--port 8765]                           the dashboard, on 127.0.0.1

Runs live in <repo>/.chief/runs/<id>/, which git ignores. This script is the only writer of
run.json. Agents are never registered by hand: Claude subagents are found in Claude Code's
transcripts and Codex jobs in the records run-codex-job.py writes, both by the brief's first
line, `Run: <run dir>   Task: <id>   Role: <role>`. Costs are API-equivalent estimates from
model-routing's prices.json, kept per provider.
"""
import argparse
import glob
import http.server
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILLS_ROOT = SKILL_DIR.parent
PRICES_PATH = SKILLS_ROOT / "model-routing" / "prices.json"
GIT_CHECK_PATH = SKILLS_ROOT / "model-routing" / "scripts" / "git-check.py"
USAGE_SCRIPT = SKILLS_ROOT / "model-routing" / "scripts" / "check-account-usage.py"
USAGE_CACHE = os.path.join(tempfile.gettempdir(), "model-routing-usage.json")
DASHBOARD = SKILL_DIR / "dashboard.html"

PHASES = ["intake", "research", "plan", "plan-review", "approval", "implement", "review", "report", "paused", "done"]
RUN_TAG = re.compile(r"Run:\s*(\S+)(?:\s+Task:\s*(\S+))?(?:\s+Role:\s*(\S+))?")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
STALE_SECONDS = 15 * 60
PROVIDERS = ("claude", "chatgpt")


# ---- small helpers -----------------------------------------------------------------------


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def runs_root(repo):
    return os.path.join(repo, ".chief", "runs")


def write_json(path, data):
    temporary = f"{path}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1)
    os.replace(temporary, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def slugify(text, limit=40):
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words)[:limit].strip("-") or "task"


def git_toplevel(cwd="."):
    completed = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


# ---- starting a run and moving its phase ---------------------------------------------------


def start_run(repo, text, title=None, source="chat", now=None):
    if not text or not text.strip():
        raise ValueError("the task is empty: pass the request on stdin, with --file or with --issue")
    title = (title or text.strip().splitlines()[0]).strip()[:120]
    root = runs_root(repo)
    os.makedirs(root, exist_ok=True)
    ignore = os.path.join(repo, ".chief", ".gitignore")
    if not os.path.exists(ignore):
        with open(ignore, "w", encoding="utf-8") as handle:
            handle.write("*\n")
    stamp = time.strftime("%Y%m%d-%H%M", time.localtime(now))
    base = f"{stamp}-{slugify(title)}"
    run_id, counter = base, 2
    while True:
        try:
            os.makedirs(os.path.join(root, run_id))
            break
        except FileExistsError:
            run_id, counter = f"{base}-{counter}", counter + 1
    run_dir = os.path.join(root, run_id)
    with open(os.path.join(run_dir, "task.md"), "w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\nSource: {source}\n\n{text.strip()}\n")
    started = now_iso()
    write_json(os.path.join(run_dir, "run.json"), {
        "id": run_id, "title": title, "source": source, "repo": repo, "started": started, "ended": None,
        "phase": "intake", "plan": None, "workspace": None,
        "phases": [{"phase": "intake", "at": started, "usage": usage_snapshot()}],
    })
    return run_dir


def issue_command(ref, remote_url=None):
    gitlab = "gitlab" in ref or (not ref.startswith("http") and "gitlab" in (remote_url or ""))
    if gitlab:
        return ["glab", "issue", "view", ref, "--output", "json"]
    return ["gh", "issue", "view", ref, "--json", "title,body,url"]


def import_issue(repo, ref):
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, capture_output=True, text=True).stdout
    command = issue_command(ref, remote)
    completed = subprocess.run(command, cwd=repo, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed: {completed.stderr.strip()}")
    issue = json.loads(completed.stdout)
    body = issue.get("body") or issue.get("description") or ""
    url = issue.get("url") or issue.get("web_url") or ref
    return issue.get("title") or f"Issue {ref}", body or "(the issue has no description)", f"issue {url}"


def resolve_run(repo, run):
    """A run's folder from its id or its path, or None."""
    candidate = run if os.path.isabs(run) or os.sep in run else os.path.join(runs_root(repo), run)
    return candidate if os.path.isfile(os.path.join(candidate, "run.json")) else None


def load_run(run_dir):
    state = read_json(os.path.join(run_dir, "run.json"))
    if state is None:
        raise ValueError(f"no run.json in {run_dir}")
    return state


def set_phase(run_dir, phase, plan=None, workspace=None):
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}; one of: {', '.join(PHASES)}")
    state = load_run(run_dir)
    at = now_iso()
    state["phase"] = phase
    state["phases"].append({"phase": phase, "at": at, "usage": usage_snapshot()})
    if plan:
        state["plan"] = plan
    if workspace:
        state["workspace"] = workspace
    state["ended"] = at if phase == "done" else None
    write_json(os.path.join(run_dir, "run.json"), state)
    return state


# ---- account usage (read from model-routing's cache; never spends a model turn) ----------


def read_usage_cache(max_age=None):
    try:
        age = time.time() - os.path.getmtime(USAGE_CACHE)
    except OSError:
        return None
    if max_age is not None and age > max_age:
        return None
    readings = read_json(USAGE_CACHE)
    if not isinstance(readings, dict):
        return None
    as_of = datetime.fromtimestamp(os.path.getmtime(USAGE_CACHE), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"as_of": as_of, **{name: readings.get(name) for name in PROVIDERS}}


def usage_snapshot():
    cache = read_usage_cache(max_age=900)
    if not cache:
        return None
    return {name: {key: (cache.get(name) or {}).get(key) for key in ("5h", "week")} for name in PROVIDERS}


# ---- prices -----------------------------------------------------------------------------


def load_prices(path=PRICES_PATH):
    return read_json(path, {}) or {}


def price_claude(model, usage, prices):
    """API-equivalent USD for one Claude message, or None when the model has no price."""
    rates = (prices.get("claude") or {}).get(model)
    if not rates:
        return None
    split = usage.get("cache_creation") or {}
    write_1h = split.get("ephemeral_1h_input_tokens", 0) or 0
    write_5m = (usage.get("cache_creation_input_tokens", 0) or 0) - write_1h
    read = usage.get("cache_read_input_tokens", 0) or 0
    fresh = usage.get("input_tokens", 0) or 0
    long_rates = rates.get("long_context")
    if long_rates and fresh + read + write_5m + write_1h > long_rates.get("above_input_tokens", float("inf")):
        rates = {**rates, **long_rates}
    return (fresh * rates["input"] + (usage.get("output_tokens", 0) or 0) * rates["output"]
            + write_5m * rates["cache_write_5m"] + write_1h * rates["cache_write_1h"]
            + read * rates["cache_read"]) / 1e6


def price_codex(model, usage, prices):
    """API-equivalent USD for one Codex job. Cached input is part of input; reasoning is part of output."""
    rates = (prices.get("chatgpt") or {}).get(model)
    if not rates or not usage:
        return None
    cached = usage.get("cached", 0) or 0
    uncached = max((usage.get("input", 0) or 0) - cached, 0)
    return (uncached * rates["input"] + cached * rates.get("cached_input", rates["input"])
            + (usage.get("output", 0) or 0) * rates["output"]) / 1e6


# ---- Claude agents, from Claude Code's transcripts ----------------------------------------

_TRANSCRIPTS = {}


def prompt_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(block.get("text", "") for block in content or [] if isinstance(block, dict))


def parse_messages(lines, prices, start=None, end=None, sidechain=None):
    """Usage, cost and the last reply over the assistant messages in a transcript."""
    messages, last_text, last_entry, first_at, last_at = {}, "", None, None, None
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        at = parse_time(entry.get("timestamp"))
        if start is not None and (at is None or at < start or (end is not None and at > end)):
            continue
        if sidechain is not None and bool(entry.get("isSidechain")) != sidechain:
            continue
        if entry.get("type") in ("user", "assistant"):
            last_entry = entry
            first_at = first_at or entry.get("timestamp")
            last_at = entry.get("timestamp") or last_at
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict):
            continue
        if message.get("usage") and message.get("id"):
            messages[message["id"]] = message
        text = prompt_text(entry).strip()
        if text:
            last_text = text
    tokens = {"input": 0, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}
    cost, unpriced, model = 0.0, False, None
    for message in messages.values():
        usage = message["usage"]
        split = usage.get("cache_creation") or {}
        write_1h = split.get("ephemeral_1h_input_tokens", 0) or 0
        tokens["input"] += usage.get("input_tokens", 0) or 0
        tokens["output"] += usage.get("output_tokens", 0) or 0
        tokens["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
        tokens["cache_write_1h"] += write_1h
        tokens["cache_write_5m"] += (usage.get("cache_creation_input_tokens", 0) or 0) - write_1h
        model = message.get("model") or model
        price = price_claude(message.get("model"), usage, prices)
        if price is None:
            unpriced = True
        else:
            cost += price
    done = bool(last_entry and last_entry.get("type") == "assistant"
                and (last_entry.get("message") or {}).get("stop_reason") == "end_turn")
    return {"tokens": tokens, "cost_usd": None if unpriced else round(cost, 6), "model": model,
            "report": last_text[-6000:], "started": first_at, "ended": last_at if done else None, "done": done}


def parse_subagent(path, prices):
    with open(path, encoding="utf-8", errors="replace") as handle:
        first = handle.readline()
        try:
            prompt = prompt_text(json.loads(first))
        except json.JSONDecodeError:
            return None
        tag = RUN_TAG.search(prompt[:600])
        if not tag:
            return None
        parsed = parse_messages(handle, prices)
    meta = read_json(path[: -len(".jsonl")] + ".meta.json", {}) or {}
    return {"tag_run": tag.group(1), "task": tag.group(2) or "-", "role": tag.group(3) or meta.get("agentType") or "agent",
            "description": meta.get("description") or "", **parsed}


def cached_parse(path, parser, prices):
    stat = os.stat(path)
    key = (path, stat.st_mtime, stat.st_size)
    if key not in _TRANSCRIPTS:
        _TRANSCRIPTS[key] = parser(path, prices)
    return _TRANSCRIPTS[key], stat.st_mtime


def same_run(tag_run, run_dir, run_id):
    if os.path.isabs(tag_run):
        return os.path.realpath(tag_run) == os.path.realpath(run_dir)
    return tag_run == run_id


def claude_agents(config_dir, runs, prices):
    """{run id: [agent]} for every tagged subagent transcript, plus each run's chief session."""
    found = {run["id"]: [] for run in runs}
    if not runs:
        return found
    since = min(parse_time(run["started"]) or 0 for run in runs) - 300
    for path in glob.glob(os.path.join(config_dir, "projects", "*", "*", "subagents", "agent-*.jsonl")):
        try:
            if os.path.getmtime(path) < since:
                continue
            parsed, mtime = cached_parse(path, parse_subagent, prices)
        except OSError:
            continue
        if not parsed:
            continue
        for run in runs:
            if same_run(parsed["tag_run"], run["dir"], run["id"]):
                status = "done" if parsed["done"] else ("stopped" if time.time() - mtime > STALE_SECONDS else "running")
                found[run["id"]].append({
                    "id": "claude-" + os.path.basename(path)[len("agent-"): -len(".jsonl")], "provider": "claude",
                    "model": parsed["model"], "task": parsed["task"], "role": parsed["role"],
                    "description": parsed["description"], "status": status, "started": parsed["started"],
                    "ended": parsed["ended"], "tokens": parsed["tokens"], "cost_usd": parsed["cost_usd"],
                    "report": parsed["report"]})
                break
    for run in runs:
        chief = chief_session(config_dir, run, prices, since)
        if chief:
            found[run["id"]].append(chief)
    return found


def chief_session(config_dir, run, prices, since):
    """The chief session.s own tokens: the main session that started this run, inside the run's time."""
    start = parse_time(run["started"])
    end = parse_time(run.get("ended"))
    for path in glob.glob(os.path.join(config_dir, "projects", "*", "*.jsonl")):
        try:
            if os.path.getmtime(path) < since:
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        if f"chief-run.py start" not in text or run["id"] not in text:
            continue
        parsed = parse_messages(text.splitlines(), prices, start=start - 120, end=end, sidechain=False)
        return {"id": "chief", "provider": "claude", "model": parsed["model"], "task": "-", "role": "chief",
                "description": "the chief session", "status": "done" if run.get("ended") else "running",
                "started": run["started"], "ended": run.get("ended"), "tokens": parsed["tokens"],
                "cost_usd": parsed["cost_usd"], "report": ""}
    return None


# ---- Codex agents, from run-codex-job.py's records ----------------------------------------


def process_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def codex_agents(run_dir, prices):
    agents = []
    for path in sorted(glob.glob(os.path.join(run_dir, "agents", "codex-*.json"))):
        record = read_json(path)
        if not isinstance(record, dict):
            continue
        status = {"completed": "done"}.get(record.get("status"), record.get("status") or "running")
        if status == "running" and not process_alive(record.get("pid")):
            status = "stopped"
        usage = record.get("usage") or {}
        report = record.get("last_message") or ""
        agents.append({
            "id": os.path.basename(path)[: -len(".json")], "provider": "chatgpt", "model": record.get("model"),
            "effort": record.get("effort"), "task": record.get("task") or "-", "role": record.get("role") or "agent",
            "description": record.get("label") or "", "status": status, "started": record.get("started"),
            "ended": record.get("ended"), "thread_id": record.get("thread_id"), "resumed": bool(record.get("resumed")),
            "tokens": {key: usage.get(key, 0) or 0 for key in ("input", "cached", "output", "reasoning")},
            "cost_usd": price_codex(record.get("model"), record.get("usage"), prices), "report": report[-6000:]})
    latest = {}
    for agent in agents:
        if agent["thread_id"]:
            mark = agent["ended"] or agent["started"] or ""
            if agent["thread_id"] not in latest or mark >= latest[agent["thread_id"]][0]:
                latest[agent["thread_id"]] = (mark, agent["id"])
    for agent in agents:
        if agent["thread_id"] and latest[agent["thread_id"]][1] != agent["id"]:
            agent["superseded"] = True  # a later resume of the same thread reports its whole usage
    return agents


# ---- the board ----------------------------------------------------------------------------


def token_count(agent):
    tokens = agent["tokens"]
    if agent["provider"] == "chatgpt":
        return tokens.get("input", 0) + tokens.get("output", 0)
    return sum(tokens.values())


def totals_for(agents):
    totals = {name: {"agents": 0, "tokens": 0, "cost_usd": 0.0, "unpriced": 0} for name in PROVIDERS}
    for agent in agents:
        bucket = totals[agent["provider"]]
        bucket["agents"] += 1
        if agent.get("superseded"):
            continue
        bucket["tokens"] += token_count(agent)
        if agent["cost_usd"] is None:
            bucket["unpriced"] += 1
        else:
            bucket["cost_usd"] += agent["cost_usd"]
    for bucket in totals.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 6)
    totals["total_cost_usd"] = round(sum(totals[name]["cost_usd"] for name in PROVIDERS), 6)
    totals["estimate"] = True
    return totals


def list_runs(repo):
    runs = []
    for run_dir in sorted(glob.glob(os.path.join(runs_root(repo), "*")), reverse=True):
        state = read_json(os.path.join(run_dir, "run.json"))
        if isinstance(state, dict) and state.get("id"):
            runs.append({**state, "dir": run_dir})
    return runs


def git_state(repo):
    try:
        spec = importlib.util.spec_from_file_location("git_check", GIT_CHECK_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.report(repo)
        return {"branch": result.get("branch"), "upstream": result.get("upstream"), "warnings": result.get("warnings", [])}
    except Exception as error:  # the board still renders without git
        return {"error": str(error)}


def default_config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def build_board(repo, config_dir=None, prices=None, with_git=True):
    prices = load_prices() if prices is None else prices
    runs = list_runs(repo)
    claude = claude_agents(config_dir or default_config_dir(), runs, prices)
    cards = []
    for run in runs:
        agents = claude[run["id"]] + codex_agents(run["dir"], prices)
        agents.sort(key=lambda agent: agent.get("started") or "")
        card = {key: run.get(key) for key in ("id", "title", "source", "phase", "phases", "started", "ended", "plan", "workspace", "dir")}
        card.update(agents=agents, totals=totals_for(agents))
        cards.append(card)
    every = [agent for card in cards for agent in card["agents"]]
    return {"generated": now_iso(), "repo": repo, "runs": cards, "totals": totals_for(every),
            "accounts": read_usage_cache(), "git": git_state(repo) if with_git else None,
            "prices_note": "API-equivalent estimates from model-routing/prices.json; on a subscription the window use is what limits you"}


def money(value):
    if value is None:
        return "unpriced"
    return "<$0.01" if 0 < value < 0.005 else f"${value:,.2f}"


def summary_markdown(repo, run_dir, config_dir=None, prices=None):
    board = build_board(repo, config_dir=config_dir, prices=prices, with_git=False)
    run_id = os.path.basename(os.path.normpath(run_dir))
    card = next((item for item in board["runs"] if item["id"] == run_id), None)
    if card is None:
        raise ValueError(f"no run {run_id}")
    lines = [f"Run {card['id']}: {card['title']}", "",
             "| provider | model | role | task | status | tokens | API-eq $ |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for agent in card["agents"]:
        tokens = agent["tokens"]
        if agent["provider"] == "chatgpt":
            detail = f"in {tokens['input']:,} (cached {tokens['cached']:,}) / out {tokens['output']:,} (reasoning {tokens['reasoning']:,})"
        else:
            detail = (f"in {tokens['input']:,} / cache w {tokens['cache_write_5m'] + tokens['cache_write_1h']:,}"
                      f" r {tokens['cache_read']:,} / out {tokens['output']:,}")
        cost = "in the resume below" if agent.get("superseded") else money(agent["cost_usd"])
        lines.append(f"| {agent['provider']} | {agent['model'] or '?'} | {agent['role']} | {agent['task']} | {agent['status']} | {detail} | {cost} |")
    totals = card["totals"]
    for name, label in (("claude", "Claude"), ("chatgpt", "ChatGPT")):
        bucket = totals[name]
        extra = f", {bucket['unpriced']} unpriced" if bucket["unpriced"] else ""
        lines.append(f"{label} subtotal: {money(bucket['cost_usd'])} over {bucket['agents']} agent(s), {bucket['tokens']:,} tokens{extra}")
    lines.append(f"Total: {money(totals['total_cost_usd'])}, an API-equivalent estimate; on subscriptions the window use below is what limits you.")
    snapshots = [entry for entry in card.get("phases") or [] if entry.get("usage")]
    if snapshots:
        first, last = snapshots[0], snapshots[-1]
        for name in PROVIDERS:
            before, after = (first["usage"].get(name) or {}), (last["usage"].get(name) or {})
            lines.append(f"{name} 5-hour window: {before.get('5h')}% at {first['phase']} -> {after.get('5h')}% at {last['phase']}; week {before.get('week')}% -> {after.get('week')}%")
    return "\n".join(lines)


# ---- files the dashboard may open ----------------------------------------------------------


def resolve_file(repo, run_id, name):
    if not RUN_ID.match(run_id or "") or ".." in run_id:
        return None
    run_dir = os.path.join(runs_root(repo), run_id)
    state = read_json(os.path.join(run_dir, "run.json"))
    if not isinstance(state, dict):
        return None
    fixed = {"task": os.path.join(run_dir, "task.md"), "run": os.path.join(run_dir, "run.json")}
    if name in fixed:
        return fixed[name]
    targets = {"plan": state.get("plan"),
               "progress": state.get("workspace") and os.path.join(state["workspace"], "progress.md"),
               "handoff": state.get("workspace") and os.path.join(state["workspace"], "handoff.md")}
    target = targets.get(name)
    if not target:
        return None
    path = os.path.realpath(os.path.join(repo, target))
    return path if path.startswith(os.path.realpath(repo) + os.sep) and os.path.isfile(path) else None


# ---- the dashboard server ------------------------------------------------------------------


def refresh_usage_forever(minutes):
    """Keep model-routing's usage cache fresh for the gauges; reading usage spends no model turn."""
    try:
        spec = importlib.util.spec_from_file_location("check_account_usage", USAGE_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return
    while True:
        try:
            module.read_usage(minutes * 60)
        except Exception:
            pass
        time.sleep(60)


def serve(repo, port, refresh_minutes=5):
    git_cache = {"at": 0, "value": None}
    if refresh_minutes > 0:
        threading.Thread(target=refresh_usage_forever, args=(refresh_minutes,), daemon=True).start()

    class Handler(http.server.BaseHTTPRequestHandler):
        def send(self, status, body, content_type):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path in ("/", "/index.html"):
                return self.send(200, DASHBOARD.read_text(encoding="utf-8"), "text/html; charset=utf-8")
            if url.path == "/board.json":
                board = build_board(repo, with_git=False)
                if time.time() - git_cache["at"] > 15:
                    git_cache.update(at=time.time(), value=git_state(repo))
                board["git"] = git_cache["value"]
                return self.send(200, json.dumps(board), "application/json")
            if url.path == "/file":
                query = urllib.parse.parse_qs(url.query)
                path = resolve_file(repo, (query.get("run") or [""])[0], (query.get("name") or [""])[0])
                if not path:
                    return self.send(404, "not found", "text/plain; charset=utf-8")
                with open(path, encoding="utf-8", errors="replace") as handle:
                    return self.send(200, handle.read(), "text/plain; charset=utf-8")
            return self.send(404, "not found", "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Agent runs dashboard for {repo}: http://127.0.0.1:{port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


# ---- command line -------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="create a run from the task text on stdin, a file or an issue")
    start.add_argument("--title")
    source = start.add_mutually_exclusive_group()
    source.add_argument("--file", help="read the task from this file")
    source.add_argument("--issue", help="import a GitHub or GitLab issue: number or URL")
    phase = commands.add_parser("phase", help="record the phase the run enters")
    phase.add_argument("run")
    phase.add_argument("phase", choices=PHASES)
    phase.add_argument("--plan", help="the plan file, relative to the repo")
    phase.add_argument("--workspace", help="the plan workspace holding progress.md and handoff.md")
    summary = commands.add_parser("summary", help="the cost table for the report")
    summary.add_argument("run")
    commands.add_parser("board", help="print the dashboard data")
    serve_command = commands.add_parser("serve", help="serve the dashboard on 127.0.0.1")
    serve_command.add_argument("--port", type=int, default=8765)
    serve_command.add_argument("--refresh-usage", type=int, default=5, metavar="MINUTES",
                               help="refresh both accounts' usage this often for the gauges; 0 turns it off")
    args = parser.parse_args()

    repo = git_toplevel()
    if not repo:
        print("chief-run: run it inside the project's git repository", file=sys.stderr)
        return 2
    try:
        if args.command == "start":
            if args.issue:
                title, text, origin = import_issue(repo, args.issue)
            elif args.file:
                with open(args.file, encoding="utf-8") as handle:
                    title, text, origin = None, handle.read(), f"file {args.file}"
            else:
                title, text, origin = None, sys.stdin.read(), "chat"
            run_dir = start_run(repo, text, title=args.title or title, source=origin)
            print(json.dumps({"run": run_dir, "id": os.path.basename(run_dir),
                              "tag": f"Run: {run_dir}   Task: <id>   Role: <role>"}))
        elif args.command in ("phase", "summary"):
            run_dir = resolve_run(repo, args.run)
            if not run_dir:
                raise ValueError(f"no run {args.run} under {runs_root(repo)}")
            if args.command == "phase":
                state = set_phase(run_dir, args.phase, plan=args.plan, workspace=args.workspace)
                print(json.dumps({"id": state["id"], "phase": state["phase"]}))
            else:
                print(summary_markdown(repo, run_dir))
        elif args.command == "board":
            print(json.dumps(build_board(repo)))
        else:
            serve(repo, args.port, args.refresh_usage)
    except (ValueError, RuntimeError, OSError) as error:
        print(f"chief-run: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
