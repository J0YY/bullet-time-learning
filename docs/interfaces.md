# Shared interfaces — versioned pilot contracts

**2026-10-28 status:** Joy's consumer, runner and readouts are implemented and
tested on synthetic fixtures. No real producer/consumer integration or independent
analysis validation has passed. Producer-side schema/data remain pending.
Sudarshan owns canonical data schema; Joy owns run/prediction exports and this
document. Record actual validation separately for each side.

## 1. Grid and evaluation bundle

**Producer:** Sudarshan. **Consumer:** Joy. Working version: `bullet-time.grid.v1`.

| Record | Required fields and meaning |
| --- | --- |
| Bundle | Schema version; generator/code/renderer/engine revisions; config hashes; byte inventory; asset sources/licenses; public/private split; rejection and validation report |
| Grid | `grid_id`, `scene_family`, `rollout_id`, `split`, `asset_group`, scene/configuration/trajectory grouping IDs, simulation/action/appearance/camera seeds, state checksums and timestamps |
| Cell | Grid ID; `world_time_index` and `camera_index` in 0…15; stable image ID; relative RGB path; file SHA-256; decoded RGB SHA-256 with dtype/shape/order convention; dimensions |
| Camera/state sidecar | Camera matrices/path ID, phase/direction metadata and loop checks; state export including transforms, velocities, articulations, lighting/animation, event phase, action script and visibility/contact records |
| Split | Bundle/configuration/rollout/trajectory/asset grouping, split assignments, pair/window linkage, duplicate review, version and manifest hash; development/pilot versus final designation |
| Evaluation | Episode/task/split IDs; ordered observed images and times; query points plus coordinate convention; counterpart-pair ID; continuation-policy ID; horizon; future contacts/tracking/spatial labels in a separate restricted export |

Each accepted grid has exactly 256 unique index pairs and stable image identities.
Repeated pixel content is allowed; unique IDs do not require unique pixel hashes.
All conditions resolve the same IDs to the same bytes. Validate file checksums and
decoded RGB hashes rather than accepting manifest self-attestation. State/camera
replay identity and smooth closure require actual renderer tests.

Pretraining receives only RGB and an allowlisted scheduling manifest. Simulation
metadata and oracle labels are inaccessible to the loader and never input to the
backbone. Retain split/group IDs for auditing only. Evaluation readouts receive RGB
plus the specified query points/reference, never engine identities or velocities.

Separate pretraining, readout training, development, and final-test sets. Group
related windows/rollouts, configurations, trajectories, asset groups, and paired
counterfactuals before splitting. Record familiar-family and held-out-layout/asset
test partitions. Hold out complete families in the separate family replication.
Pilot episodes are not recycled into final test.

**Acceptance:** reject missing/duplicate cells, nonfinite timestamps/coordinates,
inconsistent dimensions, bad hashes, escaping paths, broken pair linkage, and split
leakage. Verify final-frame and full image-multiset equality where required; also
check side information, continuation rules, and oracle labels. Those checks cannot
establish visual solvability without the sequence/control experiments.

## 2. Sequence and update audit

**Producer:** Joy. **Independent checker:** Sudarshan.
Working version: `bullet-time.exposure.v1`.

Scheduler input: grid manifest, condition/Time fraction, pass number, and paired
seed. Define pass numbering explicitly (zero-based). Output: 16 ordered
clips of 16 image IDs per complete grid, plus reproducible scheduling metadata.

| Condition ID | Construction and invariant |
| --- | --- |
| `view` | Rows: fixed world time, all 16 cameras in a recorded randomized cyclic phase/direction |
| `time` | Columns: fixed camera, world time 0…15 |
| `mix25`, `mix50`, `mix75` | Whole-grid View/Time assignments; exactly 1, 2, or 3 Time passes per grid in each four-pass cycle |
| `joint` | 16 phase offsets; cell `(t, (direction*t + phase) % 16)`; recorded balanced directions across grids; world time never wraps |
| `shuffled_time` | Same members as Time clips, reproducibly permuted in order |
| `regrouped` | Partition all 256 cells into 16 clips of 16 distinct cells; no replacement |

Common episode order, assignment balance across families/progress, independent RNG
streams, and complete four-pass cycles are required. Mask and augmentation seeds
are keyed by paired run, grid, and pass rather than condition. Report construction
and four-pass exposure counts for every arm and both Joint directions.

The real-loader audit records raw image IDs/hashes, transformed pixel hashes,
crop/color parameters, actual post-collator visible/target patch indices, raw pixel
target values for VideoMAE, and separate student/teacher exposure for V-JEPA.
V-JEPA targets are contextual and do not receive an equality assertion.

Compare exposure/masks in canonical `(image_id, spatial_patch)` coordinates after
mapping clip/token positions back to source cells. Equal local token indices alone
do not establish equal source-image masking after regrouping. For raw RGB targets,
compare per-image components, not entire differently paired tubelet tensors.

Update records bind the exact ordered grid set, microbatch contributions and loss
denominators, optimizer/schedule/teacher step counters, and masks to one update ID.
Initially eight complete grids yield 128 clips. Compare actual update boundaries,
not just nominal batch size. Backbone isolation across clips is an implementation
check. Token identity is not required for two-frame tubelets across regroupings.

**Acceptance:** one pass uses every cell once; schedules meet all four-pass counts;
hashes/masks/targets obey their objective-specific invariants; no missing partial
grid or independently advanced teacher step. Synthetic enumeration, renderer replay,
loader audit, and real optimizer validation are distinct evidence levels.

## 3. Run and prediction export

**Producer:** Joy. **Consumer:** Sudarshan.
Working versions: `bullet-time.run.v1`, `bullet-time.prediction.v1`.

| Record | Required fields |
| --- | --- |
| Run plan | Run ID; objective; condition; paired pretraining seed; corpus/split/config/code hashes; intended passes, grids/update and exposure; main/pilot/reference/replication designation |
| Execution | Exact model/objective/engine/software revisions; initialization hash; hyperparameters; precision/hardware; RNG stream seeds; audit hashes; checkpoint identity; optimizer/teacher progress; commands, job IDs, timing, memory, I/O, GPU count and failure state |
| Readout | Checkpoint/run ID; task/head/config revision; label budget and training subset hash; readout seed; frozen-backbone flag; permitted input/sampling protocol; tuning provenance |
| Prediction | Unique key `(run_id, checkpoint_id, task_id, label_budget, readout_seed, episode_or_video_id, query_id, horizon_or_frame)`; split/family/pair grouping; target-reference hash; probability/coordinate/visibility/class output as applicable; status/error |
| Coverage | Inventory of all planned runs/examples, including missing and failed slots; exclusion reasons fixed by policy; artifact hashes/locations and completion state |

Run IDs distinguish native recipes, controlled recipes, image-only references,
untrained references, and independent corpora. No cache reuse across changed
source/config/input identity. Store labels separately and join them only for
authorized evaluation. Final-test outcomes stay unavailable to tuning.

**Acceptance:** complete unique keys, explicit failures, consistent checkpoint/
split hashes, matched example/readout budgets, paired seed mapping, and traceable
resource totals. Do not silently drop failed arms or treat missing predictions as
success. Preserve raw predictions so independent metrics can be recomputed.

## 4. Analysis and table bundle

**Producer:** Sudarshan. **Reproducer:** Joy.
Working version: `bullet-time.analysis.v1`.

Bind each output to the frozen analysis configuration and source-run, prediction,
split and label hashes. Include inclusion/exclusion rules, coverage, counts, family,
objective, condition, pretraining seed, readout seed, corpus, and label budget.

- Primary: collision balanced accuracy; episode reacquisition success; external
  Something-Something V2 top-1 accuracy. Game scores average within family, then
  weight the three families equally. Collision Brier score and spatial performance
  are supporting outcomes, not extra primary endpoints.
- Average three readout seeds within a checkpoint before paired pretraining-seed
  contrasts. Retain both sources of variation and paired episode/video groupings.
  Report per-family effects and test-sample sensitivity separately.
- Record effect sizes, conventional intervals, TOST component intervals/decisions,
  frozen margins, and multiplicity handling. Global conjunction: all 30 primary
  components pass; stronger all-family claim: all 70 pass. Component 90% intervals
  are not simultaneous 95% intervals. Individual/superiority claims use their
  prespecified correction. Failed validity gates constrain interpretation.
- These 30/70 contrasts establish equivalence **to View**, not equivalence of
  every pair of arms at the same margin. Keep claim text reference-relative.
  An all-pairs design would require a separately declared analysis/power plan.
- Power planning uses conservative pilot variability/correlation assumptions.
  Sample size or valid sequential stopping is fixed before test outcomes, never
  increased until equivalence passes. Keep planning simulations separate from data.
- Emit machine-readable table inputs, analysis version, reproducing command, and
  explicit labels for toy, development, confirmatory, and exploratory outputs.

**Acceptance:** fixture cases cover family weighting, seed hierarchy, paired missing
data, metric boundary cases, interval/margin boundaries, and conjunction failure.
Integration reproduces the actual delivered outputs, not only a producer's demo.

## Version and validation status

### Selected protocol and independent implementation boundary

The [revised SPEC](../SPEC.md) §7 and [pilot plan](pilot-plan.md) now select fixed
64 Hz physics / 16 Hz evaluation, 16 observed frames, a current-inclusive tracking
window and fixed pre-occlusion reference, normalized coordinates, visibility ≥0.5,
small-object stratum, repeated-image spatial adapter, and SSv2 internal development
with reserved official validation. These replace the earlier unresolved checklist.
Pilot seeds/budgets/gates are selected; final-study margins, power, runtime pins,
compute and final freeze remain pending. The 30/70 claims are View-relative.

v1 supersedes the unimplemented v0 draft. There are no deployed v0 artifacts to
migrate. Future incompatible changes need a new version. This is a working format
commitment for independent coding, not a claim that either implementation exists.

Use UTF-8 JSON for manifests and metadata. `pretrain.jsonl` has one grid per line;
`bundle.json` declares version, producer/config hashes and the inventory. The
allowlisted pretraining record is:

```json
{
  "schema_version": "bullet-time.grid.v1",
  "grid_id": "synthetic-example-only",
  "scene_family": "projectile_arena",
  "cells": [
    {
      "world_time_index": 0,
      "camera_index": 0,
      "image_id": "synthetic-example-only/t00/c00",
      "rgb_path": "rgb/synthetic-example-only/t00/c00.png",
      "file_sha256": "REPLACE_WITH_ACTUAL_FILE_SHA256",
      "rgb_sha256": "REPLACE_WITH_ACTUAL_DECODED_RGB_SHA256",
      "height": 224,
      "width": 224,
      "channels": 3
    }
  ]
}
```

This abbreviated example is deliberately **not a valid grid**: producers must
supply all 256 cells, actual 64-character lower-case SHA-256 hashes and RGB bytes.
Decoded hashes cover contiguous uint8 H×W×3 row-major RGB bytes, with no header,
alpha or color-conversion ambiguity; PNG is the initial lossless format. Relative
paths resolve inside the bundle; reject absolute paths, `..` and symlink escapes.
IDs are stable opaque strings, not model inputs. Grid/cell order in the file has
no scientific meaning: sort by stable ID / explicit indices as required and log
actual schedule order. Seeds/pass/condition belong to the run/schedule, not RGB.

All state, timestamps, split lineage, labels and camera sidecars live in separate
auditor files; the pretrainer reads only the allowlisted records and RGB. An
admission validator checks private split lineage before releasing that manifest.
Store training/dev labels separately from pilot assessment and eventual final test;
mount only the permitted split for each job. Enforcement must be tested when built.

Evaluation now uses `bullet-time.evaluation.v2`, detailed in the clarification
below. The earlier unimplemented v1 outline is superseded because IDs alone cannot
verify causal windows. Labels and hidden state remain separate from inputs.

Prediction handoffs use `predictions.csv` with a header and one row per unique key
from §3; no implicit row order. Add explicit `split`, `scene_family`, `pair_group_id`,
`target_reference_sha256`, `status`, `error`, `contact_probability`, `x`, `y`,
`visibility_probability`, `class_id` as appropriate. Use blank fields for
inapplicable outputs; numeric values must be finite, probabilities in [0,1].
`status` is `ok`, `failed` or `missing`; failures retain the key and reason, with
blank outputs. IDs/seeds/budgets are recorded explicitly; never infer them from a
filename. Keep raw class logits in a separately hashed array if used for calibration.
`run.json` uses `bullet-time.run.v1`, declares `prediction_schema_version` as
`bullet-time.prediction.v1`, records the CSV hash and references a `coverage.json`
with all expected keys. Analysis uses only authorized label exports and verifies
the target-reference hash before joining. Retain group fields for paired resampling.

Producer and consumer each implement their own adapter and fixtures. Joy does not
wait to import Sudarshan's `schema.py`; Sudarshan's data/analysis CLI does not wait
for Joy's package or runner. Before real integration, validate byte hashes, allowed
input access and the actual exported records, not only this illustrative format.

Required fixture cases for future component tests: complete/missing/duplicate grid
cells, wrong RGB hashes and escaping paths; opposite-label identical-input pairs
at 50% BA/Brier 0.25 for p=0.5; tracking success only if all three frames satisfy
visibility/tolerance including equality at the boundary; a failed/missing prediction
that changes coverage; unequal family sizes (macro ≠ micro); three readout seeds
averaged within each pretraining seed; one failed TOST component blocking the global
conjunction. These fixtures are implementation tasks, not artifacts already built.

| Contract | Producer implemented | Consumer validated | Independent review |
| --- | --- | --- | --- |
| Grid v1 / evaluation v2 | No (Sudarshan) | Joy fixtures only; real data pending | Not performed |
| Exposure/update v1 | Joy fixtures/model updates | Independent S checker pending | Not performed |
| Run/prediction v1 | Joy fixture exports | S consumer pending | Not performed |
| Analysis v1 | No | No | Not performed |

Breaking changes receive a new version and explicit migration. Compatible
clarifications still need log and contract updates. Replace this table with actual
commit/hash-bound evidence as implementation progresses.

## Evaluation v2 consumer clarification — 2026-10-28

Joy's implementation found that v1's ordered image IDs alone cannot verify a causal
window. The implemented consumer therefore uses `bullet-time.evaluation.v2` for
evaluation inputs. Grid, exposure and run/prediction versions remain v1. No S3/v1
data producer existed at this change; migrate by adding the explicit fields below,
not by assuming time from filenames. No producer validation is claimed.

- Common required fields: `schema_version`, `episode_id`, `query_id`, `task_id`,
  `split` (`train`, `dev`, `assessment`), `observed_image_ids` (16),
  `observed_frame_indices` (16), `query_points`.
- Collision/order: two query points and `horizon_seconds` (0.25/0.5/1.0). Game frame
  indices must be consecutive at the selected 16 Hz cadence. No timing metadata
  is passed as a feature. SSv2 uses zero query points and ordered sampled indices.
- Tracking: no generic query points; add `prediction_frame`, `reference_frame`,
  `reference_image_id`, `reference_point`. The reference must match the declared
  past observation, remain in every window, and be fixed across the event's three
  primary predictions. Current frame equals the final observed index.
- Tracking may add `prediction_role` (`primary` by default, or `auxiliary`). Exactly
  three primary reappearance predictions are required. Include occluded auxiliary
  training/development queries with the same permitted reference/window so visibility
  does not train on positive examples alone. The recommended minimal addition is
  the first occluded frame per episode; this does not add episodes or change the
  primary three-frame score. Report auxiliary results separately. Fitting rejects
  a tracking split with only one visibility class. S3 owns physical visibility and
  first-reappearance correctness; metadata checks alone cannot establish those.

`images.jsonl` is a separate RGB catalog: `image_id`, `rgb_path`, `file_sha256`,
`rgb_sha256`, `height`, `width`, `channels`. Same lossless RGB/hash/path conventions
as grids. Evaluation pixels are letterboxed deterministically; queries use the
exact transformed coordinate map. Game labels must use those resulting coordinates
and the declared 224-pixel bounding-box diagonal convention.

The consumer's private label format is `bullet-time.labels.v1`: `schema_version`,
`task_id`, `episode_id`, `query_id`, `horizon_or_frame` (canonical string), `split`,
`target`. Targets are `{contact: 0|1}`, `{class_id: integer}`, or for tracking
`{x, y, visible: 0|1, bbox_diagonal_pixels, prediction_role}`. These labels are never
forwarded as model inputs. Source/pair/physics annotations remain a separate S3
admission/analysis export. `horizon_or_frame` is `"0.5"` etc., tracking frame string,
or `"clip"` for SSv2. Hash the canonical full label record for prediction provenance.

Prediction CSV adds the compatible `prediction_role` column, allowing S4 to keep
auxiliary visibility queries out of the three-frame primary score. An independent
expected-key inventory is mandatory; missing predictions become explicit missing
rows and cannot produce a complete gate. Assessment inference uses a label-free
expected inventory whose target hashes were prepared by the authorized auditor.

Consumer implementations: [inputs](../src/bullet_time/evaluation/inputs.py),
[targets/fitting](../src/bullet_time/evaluation/training.py),
[exports](../src/bullet_time/evaluation/export.py). Their synthetic tests do not
constitute producer integration, a benchmark, or independent scientific review.

## Consumer grouping and run binding clarification — 2026-10-28

Game `groups.json` is `{schema_version: "bullet-time.evaluation-groups.v1", records: [...]}`.
Each record has exactly `episode_id`, `task_id`, `group_id`, `split`. Group IDs and
episode IDs cannot cross splits. Collision/order groups contain exactly two episodes;
tracking groups contain one in the current pilot. If a producer needs larger related
groups, version/reconcile the contract rather than breaking those units. The input
must cover every declared episode in its included task/splits. Label subsets select
whole groups with the SPEC hash ordering; train budgets are explicit episode counts.
Collision/order heads are fitted separately at each horizon; primary is 0.5 seconds.

SSv2 groups use a JSON object mapping every partition video ID to a related-group ID.
The consumer verifies the partition hash, disjoint/nested inventories and related
group integrity. Source partition metadata and official-training-only access remain
S-owned validation responsibilities.

For frozen-readout prediction inventories, `run_id` is the actual backbone binding
SHA-256 and `checkpoint_id` is its checkpoint file SHA-256. Supervised diagnostics
use a distinct `run_id` hashing the parent backbone and full diagnostic configuration
(including mode), and `checkpoint_id` is the **fitted diagnostic** file SHA-256.
Read the explicit `prediction_identity` returned by fit and saved in its sidecar;
never substitute the common DINO initialization IDs. Human plan slot names need
an explicit mapping to these hashes. `label_budget` is the actual training episode/
video count and `readout_seed` must match the fitted head. The checkpoint carries
its source and fit hash. Inference rejects conflicting metadata; S4 independently
checks the label/group joins. See [operator guide](joy-handoff.md) for examples.

Readout checkpoints preserve `allowed_prediction_splits`. Every SSv2 pilot head
and every incomplete/early learned checkpoint is development-only. A completed
20-pass learned backbone or an untrained/external reference can support game
assessment. The predictor checks eligibility before loading any requested input;
unknown/missing progress fails closed. This is additional to S-owned split/lineage
admission and the inaccessible final-test mount. Old synthetic readout checkpoints
without this policy must be regenerated.

Evaluation points follow the **actual PIL bilinear pixel-center affine**. With
source width/height `w,h`, resized dimensions `nw,nh`, padding `left,top`, and
canvas `size`, map source normalized point `(u,v)` to
`(left + (u*(w-1)+0.5)*nw/w - 0.5)/(size-1)` and the analogous y expression.
Clip only values outside [0,1] to the nearest representable canvas pixel center.
An interior marked-pixel regression checks this against RGB resampling; aligning
only the first/last centers would be wrong for PIL resize. S3's transformed labels
must use the same declared geometry. For native 224-square game frames it is identity.

Fit and prediction reports record their executing consumer source/pin hash and
runtime, separately from the older backbone source. Inference requires the same
consumer source as the fit; execute from that recorded revision or refit after a
code change. S-owned generation/schema/splits/analysis/metrics are not imported by
the consumer and are excluded from its source fingerprint, so parallel producer
work cannot invalidate Joy's checkpoints. Their delivered data/report hashes are
validated at the artifact boundary instead.
