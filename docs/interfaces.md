# Shared interfaces — bullet-time draft v0

**2026-10-28 status:** written contracts only. No schema, producer, loader, trainer,
or analysis implementation has passed integration. Use synthetic fixtures first.
Sudarshan owns canonical data schema; Joy owns run/prediction exports and this
document. Record actual validation separately for each side.

## 1. Grid and evaluation bundle

**Producer:** Sudarshan. **Consumer:** Joy. Proposed version: `bullet-time.grid.v0`.

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
Proposed version: `bullet-time.exposure.v0`.

Scheduler input: grid manifest, condition/Time fraction, pass number, and paired
seed. Define pass numbering explicitly (proposed zero-based). Output: 16 ordered
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
Proposed versions: `bullet-time.run.v0`, `bullet-time.prediction.v0`.

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
Proposed version: `bullet-time.analysis.v0`.

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

### Choices to pin before research data or readout tuning

The [2026-10-28 audit](../reports/cvpr-feasibility-audit-20261028.md) identified
these unresolved details; recording them does not select a new scientific protocol:

- Fix evaluation cadence for physical-second forecasts, or explicitly revise
  permitted timing inputs. Variable pretraining cadence does not define evaluation.
- Specify whether the causal tracking window includes current-frame RGB, reference
  access, coordinate conventions, visibility threshold, and small-object handling.
- Pin the single-image adapter for spatial evaluation of a video backbone.
- Hash distinct external development/final-evaluation partitions. SSv2 official
  test labels are withheld; choose a verified service or a clearly named reserved
  official-validation protocol, without tuning on the final evaluation partition.
- State reference-relative equivalence, plan individual/superiority comparisons,
  and determine joint power and test-sample precision before final testing.

| Contract | Producer implemented | Consumer validated | Independent review |
| --- | --- | --- | --- |
| Grid/evaluation v0 | No | No | Not performed |
| Exposure/update v0 | No | No | Not performed |
| Run/prediction v0 | No | No | Not performed |
| Analysis v0 | No | No | Not performed |

Breaking changes receive a new version and explicit migration. Compatible
clarifications still need log and contract updates. Replace this table with actual
commit/hash-bound evidence as implementation progresses.
