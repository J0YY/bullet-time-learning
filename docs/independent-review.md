# Sudarshan's independent verification brief

Assigned by Joy on 2026-10-30; acknowledgment and work are not yet recorded.
Use the [ownership map](../division-of-labor.md) and [interfaces](interfaces.md).
Joy now builds the required renderer, data, readouts and operational scorer.
Your deliverable is a separate implementation that can catch their mistakes.

## First delivery: S4a, without waiting for real data

Implement a standalone command under `scripts/analysis/` (planned entry point:
`verify_predictions.py`), optional helpers in `src/bullet_time/analysis/`, and
your own fixtures/tests under `tests/fixtures/analysis/` and `tests/analysis/`.
Keep dependencies in your own analysis environment/config; do not import Joy's
metrics, split validator, fixture generator or package initialization. Read the
wire records directly. Pin dependencies and include a one-command reproduction.

Read `run.json`, `predictions.csv`, the independently specified expected-key
inventory, permitted labels and grouping records. Emit machine-readable scores,
coverage/failures, input/config/source hashes and a concise verification report.
Construct expected keys from declared slots/examples, never just the observed CSV.
No actual model, game bundle, GPU or completed Joy run is needed for this delivery.

Acceptance fixtures must establish:

- Collision balanced accuracy, including opposite-label identical-input pairs:
  constant probability 0.5 gives 50% BA and Brier 0.25; report threshold/tie rule.
- Tracking: equal episode weighting; success requires all three consecutive primary
  reappearance frames to meet visibility and ≤1/8 box-diagonal tolerance, including
  equality at the boundary. Auxiliary occluded queries never enter that endpoint.
- SSv2 top-1 from known answers; unknown or missing video keys cannot silently vanish.
- Duplicate keys, wrong target hashes, cross-split/group joins and nonfinite or
  out-of-range predictions fail validation. Explicit failed/missing rows remain in
  coverage; any incomplete required inventory prevents a complete gate verdict.
- Unequal family sizes produce the specified macro mean, not a pooled micro mean;
  a one-family pilot reports that family alone. Average three readout seeds within
  a checkpoint before pairing pretraining seeds; do not inflate sample size.

Deliver code/tests, a small permitted synthetic fixture bundle, command, source
commit, hashes, actual pass/fail output and known limits in `reports/independent/`.
Write only your own devlog. This is the first useful independent deliverable; it
does not depend on final tables, all pilot arms, data rendering or a meeting.

## Second delivery: S4b against a pinned snapshot

The first [real dev snapshot](../reports/data/audit-snapshots/diagnostic-dev-v1/README.md)
is now available in Git: one diagnostic, 16 predictions, eight complete collision
pairs, permitted labels/groups, fit provenance and reproduce command. Start the
metric/coverage comparison now; RGB/model files and full pilot gates are outside
this small snapshot. No acknowledgment or independent result is inferred.

Joy will publish an eligible snapshot as each stage finishes. It contains the
source commit, schema versions, artifact locations/hashes, run/fit identity mapping,
predictions, independently constructed expected keys, permitted labels/groups,
planned and failed slots, and Joy's operational scoring report when available.
Before real assessment release, use synthetic/train/dev snapshots only. A partial
snapshot may support a component audit but never a complete pilot gate verdict.
Large/restricted artifacts stay outside Git; small public reports record provenance.

Recompute outcomes, inspect coverage and compare the two implementations. Report
each discrepancy with its key, minimal fixture, command, expected/actual result
and affected claim. Extend to paired group resampling, seed/readout hierarchy,
TOST boundaries and conjunction failure, conservative power scenarios, and
independent exposure/lineage checks. Final 30/70-component equivalence claims are
outside the three-seed pilot; toy statistics are not empirical evidence.

If no real snapshot exists, finish these statistical boundary fixtures or S5's
primary-source literature/claim review. Keep reports self-contained and dated.
Joy continues on its own validated operational pipeline while this work proceeds;
actual correctness findings must still be resolved before using affected evidence.
