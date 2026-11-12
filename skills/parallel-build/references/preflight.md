# The Pre-flight Scan

Part of parallel-build. Run it once, before
dispatching Task 1.

Before dispatching Task 1, scan the plan once for conflicts, writing down
what you checked as you check it:

- tasks that contradict each other or the plan's Global Constraints
- anything the plan explicitly mandates that the review rubric treats as a
  defect (a test that asserts nothing, verbatim duplication of a logic block)

The scan's output is a table, not a verdict. One row for every pair of tasks
that share a file or an interface: the two tasks, what one produces against
what the other consumes, and what you found. One row for every task: whether
its own text agrees with itself — the tests it specifies against the code it
specifies, the files it creates against the files it later touches. "The scan
is clean" without those rows is not a scan you ran.

After the table, group the tasks into waves, starting from the plan's
Parallel layout when it has one: consecutive tasks that pass the
wave test (see SKILL.md's "Parallel waves") share a wave; any task that shares a file or
an interface with a task in the same group starts the next wave. A later
task joins an earlier wave when it passes the wave test against that wave
and consumes nothing the tasks it skips over produce — a docs task written
from the spec and the plan's Interfaces blocks is the usual case, and runs
beside the first wave whose files it does not share. Write the
wave grouping under the table. Tasks the plan orders by dependency stay in
plan order across waves. The final verification task runs alone, last.

Write the table to the ledger. Rule on everything you find before execution
begins — each finding against the plan text that mandates it — and record
each ruling in the ledger. If the scan is clean, proceed without comment.
Rule on each conflict it surfaces — the spec is the binding authority, the
plan is its argument — record the ruling beside its row, and dispatch
Task 1. The review loop remains the net for conflicts that only emerge from
implementation.
