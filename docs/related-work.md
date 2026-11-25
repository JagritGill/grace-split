# Related work and provenance

Research date: November 25, 2026, before source creation. Queries included
`github event time watermark late data simulator visualizer window allowed lateness tool`,
`online watermark late event window debugger trace simulator`,
`"watermark" "allowed lateness" "same" "budget" simulator` and `"grace-split" watermark`.
Local and public personal catalogs showed no matching project. Search is not proof
of worldwide novelty or name availability. Similar tools and concepts are expected.

## Closest alternatives

- [iht/beam-late-data](https://github.com/iht/beam-late-data) tests real Apache Beam
  windows using TestStream and examines dropped records and trigger firings.
  This substantially overlaps our debugging purpose. It uses Java/Maven/Beam;
  our tool evaluates a small explicitly defined mathematical policy, not an SDK.
- [Birdor's event-time simulator](https://birdor.com/en/tools/event-time-window-simulator/)
  has an indexed official description covering watermark bounds, allowed lateness,
  late re-fires, multiple partitions, sessions and Beam panes. Its page body was
  only partially retrievable during research; those comparisons rely on the
  retrieved primary search description, not hands-on use. This is substantial
  overlap, with broader simulation features than our single-stream model.
- [Nodique's watermark simulator](https://nodique.com/tools/watermark-simulator)
  documents one logical stream with max-seen-time minus bound, tumbling windows
  and late drops. It explicitly distinguishes that bound from a separate grace
  period. Our exact comparison holds their sum fixed and exposes how first results
  and revision counts change across every integer split.
- [Timeplus watermark explanation](https://docs.timeplus.com/understanding-watermark)
  includes a step-through tumbling-window simulation. Watermark teaching and
  out-of-order event diagnosis are established capabilities, not original claims.
- [Adaptive-Watermarks](https://github.com/DataSystemsGroupUT/Adaptive-Watermarks/blob/master/README.md)
  compares adaptive and periodic watermark generation using Flink. Its README
  calls a watermark delay parameter allowed lateness, illustrating why this
  project names its own two knobs explicitly and publishes exact rules.

[Flink's windows documentation](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/)
describes retained state and late re-firing. It also documents end-minus-one
timestamp conventions. Our deliberately simpler model fires at watermark >= the
exclusive window end and uses no minus-one adjustment. It must not be presented
as Flink/Beam/Bytewax/Timeplus compatibility. Comparisons use public primary docs
and READMEs; no competitor implementation, test, fixture, prose or diagram copied.
No simulator service, framework installation or private trace was used.

## Deliberate distinction

For one bounded integer event-time trace, hold total budget B fixed and vary
watermark lag L from 0 through B, with post-emission grace G=B-L. In our declared
policy, the accepted records and cleanup rows depend only on B; the initial-result
rows and correction counts depend on L. The tool returns exact intervals of splits
with equal summary outcomes, plus a selected split's per-window evidence. It does
not iterate over a potentially billion-value budget or promise production latency.

Original example: window width 10, budget 6, arrivals [1,14,4,18,6,25,3]. Lag 0
and lag 5 retain the same five records and drop the same two. Lag 5 removes one
revision by postponing the first [0,10) result from arrival row 2 to row 4. Lag 6
postpones another window until the final flush without rescuing more records.
This makes two superficially similar configuration knobs reviewable in one report.

No claim that alternatives cannot perform this comparison, no exhaustive feature
inventory and no global uniqueness claim. Existing portfolio ack-cut audits saved
consumer offsets, fold-ledger resolves wall-clock slots and retry-window models
retry deadlines; none implements this budget split. Established watermark, window,
binary-search and breakpoint ideas are independently implemented with Codex help.
Routine portfolio input/release/CI conventions are credited in [NOTICE](../NOTICE.md).
