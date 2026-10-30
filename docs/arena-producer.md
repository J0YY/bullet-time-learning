# Arena producer: bounded integration milestone

Joy owns this producer and its consumer integration. Sudarshan can independently
verify a snapshot without being a dependency. This implementation covers one
scripted projectile arena, a one-grid preview and eight complete grids. It does
not implement J7 evaluation sets, J8 scoring, a 100/1,000-grid drop, the other two
families, H1–H4, or a learning experiment. Scientific choices in [SPEC](../SPEC.md)
and [the pilot plan](pilot-plan.md) remain in force.

## Reproduce locally

Use the project's pinned Python 3.11 environment. On macOS, install the exact
Godot build into the ignored local cache:

```sh
.venv/bin/python scripts/data/prepare_godot.py
.venv/bin/python scripts/data/build_arena.py --output artifacts/arena-preview-v1 --count 1
.venv/bin/python scripts/data/build_arena.py --output artifacts/arena-eight-v1 --count 8 --reuse-preview artifacts/arena-preview-v1
.venv/bin/python scripts/data/build_arena.py --output artifacts/arena-eight-v1 --verify-only
```

Commit producer changes first. Existing output directories are never overwritten;
failed attempts remain for diagnosis. `--development` explicitly labels an unclean
working-tree debugging capture; it cannot be reused as the accepted preview.
Preview reuse verifies source, plan, runtime and every artifact hash first. It copies
the original 256 RGBs instead of rendering them again. New producer source bytes
require a new preview. Do not put contact sheets or downstream results inside a
completed bundle; its complete file inventory is immutable.

Simulation runs headlessly at fixed 64 Hz. RGB capture needs a native macOS display
and the pinned Compatibility/OpenGL renderer; a headless dummy renderer is rejected.
The archive, executable, engine version and project/source/config bytes are pinned.
Different platforms or renderers require a new pin and validation. Reproduction
across GPU models is not established. No cluster/CUDA runtime is selected here.

## What is generated and checked

The arena uses original procedural primitives/materials under [game/LICENSE](../game/LICENSE).
A scripted launch aims a projectile at four rigid target blocks, with a floor,
walls, pads and obstacle. The integration goal records contact with a target block.
This is a minimal game mechanic, not evidence of rich gameplay or a paper-ready
benchmark. Physics, appearance and camera use separate deterministic seed streams.

Each grid contains 16 physics snapshots at a preregistered stride of 16, 8 or 4
ticks (cycling by grid index) and 16 cameras on a smooth periodic orbit or local
oval. These are **pretraining** cadences, not the 16 Hz evaluation cadence. State
capture is repeated in a fresh process and compared exactly on this runtime.
Snapshots include transforms, velocities, freeze state and observed contacts.

A separate process replays MeshInstance3D transforms without physics nodes or
animation. Every canonical state-camera RGB is captured once, followed by a private
class-mask pass. The renderer waits for the actual post-draw signal before reading
the viewport. Admission checks all 256 before/after state hashes against replayed
transforms and saved states. Four cells are recaptured in another order solely for
validation; these never replace or enter the corpus. Their decoded RGB must match
exactly. There is no temporal AA, motion blur or animation during capture.

Measured camera transforms must match the declared curve and look-at orientation.
The curve closes in position and derivative; its entire height stays conservatively
above the recorded object geometry. Every state must have at least eight cameras
with at least four projectile pixels and twelve target pixels. These prospective
engineering thresholds catch missing/obscured foreground; they do not prove visual
solvability. The numeric echo of a request tolerates at most 1e-12 absolute JSON
round-trip error; saved/replayed transforms and repeated image bytes remain exact.

The producer verifies dimensions, PNG/RGB format, every cell/index, file and decoded
pixel checksums, exact cross-grid RGB duplicates, and configuration/appearance/
trajectory/rollout fingerprints. Fingerprints distinguish sampled instances; they
are **not** a cross-split leakage audit. All eight share one arena and primitive
asset family; related configurations/assets must be grouped before future splits.
Near-duplicate analysis, grouped train/dev/test splits, counterfactual pairs and
sealed evaluation artifacts remain J7 work. No test split exists in this bundle.

## Artifact and consumer boundary

- `rgb-only/pretrain.jsonl` and `rgb-only/rgb/`: the only consumer root. The existing
  allowlisted grid-v1 contract includes only RGB and its indexing/checksums.
- `private/states/`, `private/masks/`: hidden state and mask evidence, outside the
  consumer root. These are local sibling directories, not an OS sandbox or a claim
  of human blinding. Production access isolation still needs validation.
- `requests/`: seeded scene/camera/action inputs and lineage fingerprints.
- `validation/render/`: actual camera/transform evidence and four repeat captures.
- `validation/grids.json`: recomputed admission summaries, always scientific gate false.
- `generation.json`: actual commands, elapsed times, host and source commit.
- `bundle.json`: source pins, plan, engine pin and complete artifact-byte inventory.

The [operator guide](joy-handoff.md) describes the existing RGB consumer and update
audit. For eight grids, its actual optimizer audit compares all six main schedules
plus Shuffled Time and Regrouped using shared pixels, post-collator patch indices,
raw RGB targets, initialization and complete-update budget. A pass means integration
works; it does not establish equivalence, learning, solvability or CVPR feasibility.

Local rendering is checked separately from CI. CI exercises synthetic admission
fixtures and invalid transforms, cameras, cadence, repeated cells, visibility,
headless claims, traces and artifact paths; it does not claim to run macOS Godot.

Measured local evidence is recorded in the [October 30 integration report](../reports/arena-integration-20261030.json). Raw bundles and audit outputs stay outside Git.
