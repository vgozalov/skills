# Reporting costs

Run `check-account-usage.py` once more, then `python3 <chief skill>/scripts/chief-run.py summary <run id>`. It reads every tagged agent, Claude subagents from Claude Code's transcripts and Codex jobs from their run records, and prices them from `prices.json` in this skill's folder. Do not add tokens up by hand. Give the user:

1. The summary's table: one row per worker with provider, model, role, task, status, tokens and its API-equivalent cost. Codex input includes cached input and output includes reasoning, so neither is added twice; a resumed Codex thread is counted once, on its latest record.
2. The Claude subtotal and the ChatGPT subtotal, then their sum, always labelled "API-equivalent estimate" and never shown without the two subtotals beside it. On a subscription it shows where usage went, not what is billed. A model missing from `prices.json` is reported as unpriced and left out of the sums, never guessed.
3. Each account's 5-hour and weekly use at the start and at the end (the summary prints both from the phase snapshots), and when work switched provider. Window use, not dollars, is what limits a subscription, and the two accounts' percentages are never added together.
4. A comparison with doing the work inline, labelled as an estimate. Delegation saves because each worker starts small, while inline work re-reads one large session on every call; parallelism saves time, not tokens.
5. One line per routing choice that was not obvious, where tier 3 or above was used and what it bought, and what you would route differently next time.

Prices change: when a provider publishes new rates, update `prices.json` (its `_source` lines say where each set came from).
