# Working on grace-split

Read [README](README.md), [architecture](docs/architecture.md) and
[related work](docs/related-work.md). Purpose: finite declared-model comparison of
all integer watermark lag/grace splits at a fixed total budget, with exact evidence.
It is not a streaming SDK, live-system analyzer or configuration changer.

`grace_split/core.py`: validation, split-invariant admission, analytical per-window
schedule and exact breakpoint regions. `input.py`: bounded strict JSON file read.
`report.py`: text; `__main__.py`: CLI/gates. `tests/`: independent operational replay,
boundary and CLI regressions. `scripts/`: example/release checks. Standard library.

Release commands from this folder; record actual results when handing off:

```sh
python3 -B -m grace_split examples/tradeoff.json
python3 -B -m grace_split examples/tradeoff.json --lag 5 --max-revisions 0
python3 -B -m grace_split examples/tradeoff.json --lag 0 --max-revisions 0
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
git diff --check
```

Third command intentionally exits 1. Valid reports/pass gates exit 0; exceeded
gates exit 1 with a report; invalid inputs/arguments exit 2 without a report.
No static checker/full linter configured; AST syntax is not type checking.

Invariants: arrival order preserved, duplicates count separately, [start,end)
windows. Admission uses previous watermark, then current row advances max time.
Emit at watermark >= end; cleanup at >= end+grace. No minus-one convention.
Total budget fixes admission/cleanup; lag controls initial firing. First arrival
into an already eligible window is its first output, not a revision. EOF row N+1
flushes initial outputs; row sums are not latency. Region endpoints are inclusive
integer lag values; totals must match independent per-lag operational replay.

Keep oracle state-machine tests independent of binary search/breakpoint helpers.
Add meaningful boundary/CLI regressions for behavior changes. Register new release
files deliberately. Preserve owner edits; inspect current status before work.
No CodeRabbit, external reviewers, dependencies, private traces, real engines,
network execution, paid services, hardware or automatic policy changes. Handoff
exact checks/commit/unrun limits; do not invent CI success or engine compatibility.
Publication authority comes from the task, not this guide.
