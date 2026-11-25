# Architecture and tradeoffs

[core.py](../grace_split/core.py) is pure bounded analysis;
[input.py](../grace_split/input.py) performs strict bounded file parsing.
[report.py](../grace_split/report.py) and [CLI](../grace_split/__main__.py) present
the results and apply gates. [Core tests](../tests/test_core.py) implement an
independent operational replay. [Release checks](../scripts/check_release.py)
verify the publishable inventory, links, syntax and heuristic disclosure patterns.

## Common retention and split-dependent firing

Let H be the greatest event timestamp seen before an arrival, E its window's
exclusive end, B the total budget, L the lag and G=B-L the grace. Rejection is
H-L >= E+G, equivalently H >= E+B. The minimum budget to admit that row is
max(0,H-E+1) for integer parameters; the first row needs zero. This calculation
uses all earlier input timestamps and does not depend on the chosen split.

The production implementation first builds the nondecreasing prefix maxima and
accepted row groups per window. It computes cleanup as the first prefix row at
or after window creation reaching E+B, or EOF. Lifetimes from creation through
cleanup inclusive give peak state at the precisely documented pre-cleanup point.
No record payloads or real state backend are represented.

For a split, the first output occurs at the first prefix row at or after creation
reaching E+L, or EOF. Binary search finds that row. Accepted source rows through
it belong to the initial result; later accepted rows each produce a revision.
Creation cannot be skipped: an already-eligible window has no earlier output
until its first accepted event arrives. Cleanup cannot precede first output,
since L<=B. The operational test oracle directly simulates these transitions
instead of using this analytical schedule.

## Exact region construction

For a prefix maximum H and created window E, the Boolean H>=E+L changes as
integer L crosses H-E+1. Collect such boundaries within [1,B], plus 0 and B+1.
Only prefix rows from each window's creation onward are relevant. Between adjacent
boundaries the analytical schedule is constant. Evaluate one split per interval,
then coalesce adjacent intervals with identical summary metrics. The first-output
rows are nondecreasing with lag, so an unchanged sum does not hide one window
moving earlier while another moves later. Selected detailed evidence is computed
directly rather than reconstructed from summary metrics.

At L=B, grace is zero: cleanup follows first firing, so no accepted arrival can
revise that output. Thus a no-revision region always exists, even for empty input.
This is a theorem of this declared policy, not a guarantee about streaming engines.

## Complexity and tradeoffs

N<=64 events create at most N windows and at most N^2+1 candidate regions. Prefix
construction is linear; sorting/grouping and binary searches are bounded. Each
region evaluates at most N windows with O(log N) searches, giving worst-case
O(N^3 log(N+1)) time and O(N^2) report/working storage. No loop depends on the
numeric budget, timestamp magnitude, every tick, or a billion possible splits.
The CLI additionally limits input to 32 KiB. No report truncation is necessary.

The cap favors inspectable complete evidence over production-scale processing.
Row positions measure progress through a supplied sequence, not elapsed time.
Peak window count excludes byte sizes and downstream correction state. Final
counts are a consequence of the declared admission rules, not a universal engine
result. Flink's end-minus-one convention and framework-specific triggers are
explicitly outside scope. See [README](../README.md) for policy/limits and
[related work](related-work.md) for substantial existing capabilities.
