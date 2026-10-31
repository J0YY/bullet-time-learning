# Development measurement producer

Joy's J7 implementation builds a bounded train/development drop for the existing
input, label and group contracts. It contains **16 train + 8 dev groups per task**:
48 collision episodes, 48 order episodes and 24 tracking episodes, with 1,800 RGBs
and 384 query/horizon records. These counts are plumbing diagnostics, not the
600/200/400-episode pilot sets, H3 acceptance or a final-test freeze.

```sh
.venv/bin/python scripts/data/build_evaluation.py \
  --godot .cache/godot/4.5.1/Godot.app/Contents/MacOS/Godot \
  --output artifacts/evaluation-development-v1
.venv/bin/python scripts/data/build_evaluation.py \
  --output artifacts/evaluation-development-v1 --verify-only
```

Generation requires a clean committed producer and the pinned native Godot runtime.
An existing output directory is never overwritten. `--development` explicitly
marks dirty-source debugging; such outputs are not accepted drops. A failed attempt
is retained. The initial builder stops on a failed admission instead of silently
shrinking the dataset. Godot script errors fail admission even if the engine exits
with status zero. A new producer version requires a new drop, retaining old bytes.
For an export/admission-only repair, add `--reuse-captures OLD_DROP` to reuse the
verified raw captures in a new output. It requires unchanged renderer/motion/pins,
the same selected requests and every original file hash. All exports and admission
are recomputed; original capture provenance is retained and no old acceptance is
inherited. Changed scene or render code requires new rendering.

## Forward histories and rendered evidence

- **Collision:** a controlled arcade projectile travels toward an immovable target
  sphere, reflects elastically, and continues with no new action or randomness.
  Two different forward launches reach the same query position with opposite
  velocities. One contact lies before the query and the other after it. A forward
  integrator, analytic trajectory and 128/256 Hz refinement must agree; Godot shape
  casts independently check contact times and each 0.25/0.5/1-second label. Histories
  are sampled every four 64 Hz ticks, giving sixteen 16 Hz observations ending at
  tick 60. No irreversible footage is reversed.
- **Order:** an arcade rail carries a projectile around a circle in either direction,
  then releases its tangent velocity at the same query tick. Sixteen canonical
  states are rendered once and referenced in their respective forward orders.
  The full RGB multisets, final RGB and query points therefore match. The shared
  release/reflection rule produces opposite primary contact labels. Actual Godot
  contact probes must agree. Identical bags alone do not establish model solvability.
- **Tracking:** two visually identical drones follow constant trajectories at
  physically separated heights underneath an opaque roof. Orthographic projection,
  shared materials and disabled shadows remove height as a visible identity cue.
  Track a fixed local top-surface point. Rendered object masks must show that point
  at reference frame 16, hide it at 17–24, and reveal it at 25–27. All three primary
  current-inclusive sixteen-frame windows retain reference 16; frame 17 supplies
  an auxiliary invisible example. All four records share one event query ID;
  the prediction frame distinguishes their keys. Isolated full silhouettes supply raster bounding
  box diagonals, including portions hidden by the roof. These fixtures target the
  primary >=16-pixel stratum. Continuous trajectories keep the drones physically
  separated; mask visibility supplies the actual screen-space occlusion evidence.

The renderer records actual object/camera transforms, checks that capture did not
advance state, saves two repeat captures, and verifies their pixels. Projection
converts viewport edge coordinates to the consumer's pixel-center convention.
All geometry/materials are original primitives under [the game license](../game/LICENSE).
The implementation uses Godot's documented
[viewport world lookup](https://docs.godotengine.org/en/4.5/classes/class_viewport.html)
and [shape casts](https://docs.godotengine.org/en/4.5/classes/class_physicsdirectspacestate3d.html).

These controlled arena microtasks are deliberately simple. They do not reproduce
the target-stack dynamics of the pretraining integration, broad gameplay diversity,
varied collision occlusion, held-out game families or real-video transfer. Those
limits must be addressed before a pilot/paper claim. H3 requires learned visual
sequence and restricted controls on the full development sets, not these oracles.

## Splits, files and limits

Content prototypes (trajectory parameters, scene configuration and appearance
palette) receive deterministic pool assignments before rendering. The complete
pair or tracking episode is the group unit. The small drop requires unique
prototypes and matching pool assignments across all tasks; no prototype crosses
train/dev. The general primitive library is shared, while instantiated configurations
and appearance groups are held apart. This is not a claim of held-out game families.

Admission checks exact cross-split RGB duplicates and a stated raster near-duplicate
rule: foreground-mask IoU >=0.98 and union-foreground RGB mean absolute difference
<=1/255; empty foreground uses the whole image. This does not rule out semantic
redundancy. The old eight-grid pretraining integration pool is not a frozen pilot
pool; joint pretraining/evaluation lineage and broader duplicate validation remain
required before pilot admission.

`inputs/` contains only RGB and permitted query/reference records. `private/`
contains labels, states, requests, masks and physics evidence. `groups.json`,
`validation.json`, `generation.json` and `bundle.json` bind counts, commands,
source/runtime and actual file bytes. The consumer revalidates immutable images,
causal windows, complete labels/groups, final-image pairs and order multisets.
Verification reconstructs the selected requests and exports from saved evidence.
Raw artifacts remain outside Git.

These are separate directories, **not an OS access sandbox or human blinding**.
Assessment generation/scoring is unavailable here. The [assessment isolation foundation](assessment-isolation.md)
adds randomized private-label commitments and a locally tested restricted-job launcher.
A future version must integrate those with complete data admission, a locked protocol
and the selected execution host before that stage.

Run the pure-component checks with:

```sh
.venv/bin/python -m pytest tests/data/test_evaluation_motion.py -q
```

Tests cover forward/refined contacts, directed rail histories, constant tracking
motion, prototype separation, point/box raster boundaries and duplicate rejection.
Native rendering and model sensitivity require their own recorded executions.

## Prospective full training/development selection

The full-count planner reserves appearance, trajectory and configuration prototypes
**across all tasks**. It reads the checked-in pilot's data seed (`20261028`) and
episode counts, converts complete pairs to group units, and selects in fixed task/
split order. JSON key order cannot change the selection. The tiny integration
uses its separately documented seed `20261030`; it is not silently enlarged.

```sh
.venv/bin/python scripts/data/plan_evaluation.py --output artifacts/full-development-selection-v1
.venv/bin/python scripts/data/plan_evaluation.py --output artifacts/full-development-selection-v1 --verify-only
```

This writes an immutable **prospective** inventory, with private request records and
a public selection receipt. Source/config/runtime, every selected request byte and
actual attempted/selected counts are bound. Verification reconstructs selection
from the pinned code and pilot counts. Requests include physics/labels and never
belong in a training input mount. Assessment is not selected by this command.

The target is 1,600 groups: 300 train + 100 dev collision pairs, the same order
pairs, and 600 train + 200 dev tracking episodes. That represents 2,400 episodes
and 41,200 prospective RGB images. They become accepted episodes only after
rendering, physical/mask/input validation, pixel duplicate checks and joint
pretraining/evaluation lineage admission. Selection alone does not meet J7 or H3.

An earlier full-count preflight using the development seed found 58 shared
appearance prototypes across independently selected tasks. Global reservation
prevents that conflict without outcome-based selection. The existing tiny renderer
remains bounded to its checked-in 16/8 group plan; it does not yet consume the
full-count selection. Chunked rendering and final cross-split admission are the
next implementation step. No expensive full render is launched by planning.

The [October 30 selection report](../reports/data/full-development-selection-20261030.json)
binds the actual 1,600-group inventory and its successful reconstruction. Separate
review reproduced the complete selection and found no actionable regressions. It
remains prospective; the public report contains no rendered-data acceptance claim.

## Duplicate-check scaling

The checker retains packed foreground masks and a bounded 64-image RGB cache. It
reuses comparisons only for identical RGB-and-mask pairs within a split; every
original image remains counted and present in the data. Vectorized bounding-box/
area bounds prune impossible mask matches. For two empty masks, channel-mean
distance supplies a conservative lower bound before the exact full-image MAE.
Every surviving pair still uses the same exact foreground IoU and union-RGB MAE
rule. Cross-split exact RGB matches remain failures regardless of their masks.

These changes do not loosen thresholds or replace pixel admission with an approximate
search. Reports distinguish original image-pair counts, unique comparison units,
mask candidates, mean-bound skips and actual RGB comparisons. Memory scales with
packed masks and small metadata, plus the fixed cache, rather than retaining every
RGB image. Actual full-set time/memory still require measurement after capture.
