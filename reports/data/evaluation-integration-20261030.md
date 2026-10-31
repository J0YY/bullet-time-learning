# Small measurement drop — October 30, 2026 EDT

The native train/dev drop at `artifacts/evaluation-development-v2` passes producer
and actual consumer admission. The [machine-readable report](evaluation-integration-20261030.json)
binds its sources, manifests and bundle. Capture used `9a6702b`; repaired export and
admission used `c5a175a`, reusing unchanged raw captures with full provenance.

| Task | Train groups / episodes | Dev groups / episodes | RGBs |
| --- | --- | --- | --- |
| Collision | 16 / 32 | 8 / 16 | 744 |
| Order | 16 / 32 | 8 / 16 | 384 |
| Tracking | 16 / 16 | 8 / 8 | 672 |

Total: 72 groups, 120 episodes, 1,800 RGBs, 384 query/horizon records. The 72 native
capture processes took 258.65 seconds in aggregate on Joy's Apple M3; this excludes
Python selection, validation and re-export overhead. The admitted bundle occupies
16,221,299 bytes. Neither number estimates training performance.

Checks passed for actual saved-state/camera transforms, repeat pixels, paired final
RGB/query identity, order multisets, Godot/analytic contacts, and renderer-derived
tracking visibility and full bounding boxes. Content prototypes remain disjoint.
All 720,000 cross-split image pairs were considered by the duplicate checks; 4,705
reached RGB-distance comparison. No exact or declared raster-near duplicates were
found. Actual consumer checks accepted all labels, groups and causal windows.

The rejected v1 drop is retained: reconstruction initially depended on JSON object
key order, and tracking used frame-specific query IDs. Both were fixed and covered
by direct export-to-consumer checks. The second separate code review was clean;
it reproduced raw admission and all 384 exports. This is not Sudarshan's independent
verification. Commands, raster definitions and boundaries are in
[the producer guide](../../docs/evaluation-producer.md).

These are simple controlled arena microtasks, not a pilot completion, learned
visual-solvability result, transfer result or CVPR-quality certification. Full
600/200/400 sets, broader collision geometry/occlusion, joint pretraining lineage,
assessment isolation/release, learned sensitivity and resource validation remain.
No assessment data or labels were created. The next bounded run is a one-epoch
DINOv2 sequence readout on the small collision set to check real fitting/scoring
and measure local cost; it cannot pass H3 or replace the seven full diagnostics.
