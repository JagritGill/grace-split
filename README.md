# grace-split

What changes when the same lateness budget is split between **delaying a watermark**
and **keeping an emitted window open for corrections**? grace-split compares every
integer split exactly for a bounded event-time trace, showing first-result rows,
corrections, dropped records and retained-window counts.

Useful for reviewing a policy assumption before testing a real streaming job.
Python 3.13/3.15 standard library only. No install, service, live stream or framework.
This is a declared mathematical model, not Flink/Beam compatibility.

## Quickstart

From this repository:

```sh
python3 -B -m grace_split examples/tradeoff.json
```

Exact output:

```text
grace-split: window=10 budget=6 events=7
accepted=[1, 2, 3, 4, 6] dropped=[5, 7]
peak retained windows=2; required budget for all=16
selected lag=0 grace=6; revisions=1
lag [0,4]: revisions=1 first_row_sum=16 initial_members=4 eof_windows=1
lag [5,5]: revisions=0 first_row_sum=18 initial_members=5 eof_windows=1
lag [6,6]: revisions=0 first_row_sum=20 initial_members=5 eof_windows=2
least lag without revisions=5
Finite declared model; row positions are not wall-clock latency or engine guarantees.
```

All splits retain records 1,2,3,4,6 and drop records 5,7. At lag 0/grace 6,
window [0,10) first emits at arrival row 2, then needs a correction at row 3.
Lag 5/grace 1 waits until row 4 and includes both members in its initial result.
Lag 6/grace 0 also eliminates that correction, but delays [10,20) until EOF.
The least lag with no corrections is 5 under this trace and policy, not a universal
production setting. Changing the total budget is a different comparison.

```sh
python3 -B -m grace_split examples/tradeoff.json --lag 5 --json --max-revisions 0
python3 -B -m grace_split examples/tradeoff.json --lag 0 --max-revisions 0
python3 -B -m grace_split examples/tradeoff.json --lag 5 --max-dropped 1
python3 -B -m grace_split examples/boundary.json --json
python3 -B -m grace_split examples/first-late.json --json
python3 -B -m grace_split examples/empty.json
```

Commands two and three intentionally exit **1**; the others exit **0**. Boundary
example rejects arrivals exactly at the cleanup threshold. First-late example
distinguishes a window's first accepted late arrival from a revision of an output
that already exists. Empty input produces one region without iterating its billion
possible lag values.

## Exact policy

```json
{"window":10,"budget":6,"events":[1,14,4,18,6,25,3]}
```

One unkeyed stream, one count per input row. Array order is arrival order; duplicate
timestamps count separately. Nonnegative integer event timestamps use an arbitrary
common tick unit. Tumbling windows are [k*window,(k+1)*window), aligned at zero.
Choose integer lag L in [0,B], where budget B is fixed; grace G=B-L.

1. Before each arrival, the watermark is the greatest timestamp previously seen
   minus L. Before the first event it is negative infinity.
2. Reject an arrival if that previous watermark is **>= window_end+G**. Otherwise
   add it to the window count, creating state if needed. If the window already
   emitted, this accepted arrival produces one revision.
3. Update the greatest seen timestamp using this row, then the watermark. Each
   existing un-emitted window fires when watermark **>= its exclusive end**.
   Cleanup follows firing when watermark **>= end+G**. No minus-one convention.
4. At EOF, emit any still-un-emitted windows and remove remaining state. EOF is
   represented by arrival row N+1. This flush is part of the finite model.

A window first created after its firing threshold emits its **initial** result
on that arrival; only later accepted arrivals count as revisions. No sorting,
deduplication, periodic watermark timer, independent progress during idle periods,
early trigger, eviction or processing-time clock. These choices intentionally
do not reproduce all semantics of any streaming framework.

Admission/cleanup depend on `high >= end+B`, so they are invariant across a fixed
budget's splits. Initial firing depends on `high >= end+L`, so its timing and
corrections can differ. [Architecture](docs/architecture.md) explains the exact
breakpoint method and the bounds under which this statement holds.

## Inputs, output and gates

Exactly `window`, `budget`, `events`; no unknown/missing fields. Window integer
1..10^9; budget 0..10^9; zero through 64 event timestamps, each 0..10^12. Booleans,
floats, duplicate keys, non-finite JSON and unsupported types are errors. No
coercion or repair. CLI input must be regular UTF-8 <=32 KiB, without BOM or final
symlink. Use stable trusted local paths; no hostile-filesystem snapshot guarantee.

API:

```python
from grace_split import analyze

trace = {"window": 10, "budget": 6, "events": [1,14,4,18,6,25,3]}
result = analyze(trace, lag=5)
assert result["selected"]["metrics"]["revisions"] == 0
assert result["dropped_records"] == [5, 7]
assert result["least_lag_without_revisions"] == 5
```

Input is not mutated. Invalid input/lag raises `InputError`; API has the same model
bounds without a file-byte limit. JSON schema version 1 includes:

- Common accepted/dropped one-based source rows and per-event admission evidence.
- `required_budget_for_all`: smallest nonnegative integer budget retaining this
  trace under the policy. It can exceed the supported input budget maximum.
- `peak_retained_windows`: peak window-state count immediately after admitting
  an arrival and before that row's watermark cleanup; not a byte/memory estimate.
- `regions`: inclusive integer lag ranges with identical summary outcomes. Grace
  endpoints are shown separately since grace decreases as lag increases.
- Selected split: each created window's accepted rows, initial and final counts,
  first-emission/cleanup rows and kinds, plus all revision source rows.

Summary metrics: `revisions` counts correction outputs; `initial_member_total`
counts accepted members included in initial outputs; `eof_windows` counts windows
whose first output waits until EOF. `first_emission_row_sum` sums first-output row
positions across created windows, including EOF=N+1. It is neither latency nor a
weighted user-experience score. Inspect individual windows for an actual tradeoff.
No output evidence is truncated; input limits bound the report. Supplied event
times and order are exposed, not anonymized.

Exit **0** for a valid report with no exceeded gates; **1** with a report when
`--max-dropped` or `--max-revisions` is exceeded; **2** for invalid input/arguments
without a stdout report. Gates are inclusive integers 0..64 and both must pass if
specified. Revision gate applies to `--lag` (default 0), not all reported regions.

## Verification and limits

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
git diff --check
```

Tests independently replay mutable window state for 1,210 exhaustive models /
3,630 splits, plus 200 seeded traces. They cover equal cleanup thresholds,
first-late creation, empty/duplicate data, maximum bounds and actual CLI failures.
Release-guard mutation tests and example runs supplement the model checks.
CI uses pinned actions on standard hosted Python 3.13/3.15 runners. No static
checker/full linter configured; syntax parsing is not type checking. Disclosure
scans are heuristic, not guarantees.

No partitions, keys, sessions, sliding windows, data values, clocks, failures,
checkpoints, transactions, SDK execution or automatic configuration changes.
No production latency, memory, performance or completeness guarantees. A finite
trace cannot bound future lateness. See [research](docs/related-work.md),
[agent guidance](AGENTS.md), [attribution](NOTICE.md) and [MIT license](LICENSE).
Independently implemented with Codex assistance; no global novelty claim.
Machine-specific verification records remain outside this release.
