# First real arena integration — 2026-10-30 EDT

The scripted projectile arena now produces actual Godot RGB and feeds the existing
consumer without a Sudarshan dependency. The full-model audit passed all eight
schedules in 403.81 seconds, completing the authorized preview → eight-grid → actual-update milestone. The measured
[JSON record](arena-integration-20261030.json) carries exact hashes and audit status;
[producer commands](../docs/arena-producer.md) describe reproduction.

## Produced and checked

- Pinned Godot 4.5.1, Compatibility/OpenGL on Apple M3/macOS. Original procedural
  assets, fixed 64 Hz rigid-body simulation and separate mesh-only replay.
- One immutable preview, reused unchanged in eight complete 16-state × 16-camera
  grids: **2,048 RGB images at 224×224**. Both closed camera-curve types and strides
  16/8/4 ticks are represented. This pretraining pool has no test split.
- Fresh-process simulation replay matches exactly for every grid. All 2,048
  frozen-state checks pass; 32 validation recaptures have identical decoded pixels.
- Every state has at least 12 visible camera views, above the prospective minimum
  of eight. Every state has 16 distinct view images; each camera has at least 12
  distinct temporal images. A few identical temporal RGBs remain in their cells;
  complete grids are never selectively trimmed. Exact cross-grid duplicates: zero.
- No production grid was rejected. Development attempts and the corrected JSON
  round-trip boundary are recorded in Joy's log. Target-contact flags describe each
  captured window only; unequal durations make them unsuitable as a success rate.

The preview and overview contact sheets were visually inspected. They are generated
outside the immutable bundles at `artifacts/arena-previews/`. Raw RGB, private
state/masks and full audit events remain local/ignored; the public JSON contains
small reproduction and measurement records only.

## Actual-model integration

The existing audit runs the full configured VideoMAE-S at 224 pixels, 16 frames,
FP32 CPU, four threads, seed 17 and microbatches of two clips. It performs one actual
optimizer update for each of View, 25/50/75% Time, Time, Joint, Shuffled Time and
Regrouped, over the same eight grids. It compares initialization, actual transformed
pixels, post-collator visible/target indices, raw RGB target bytes, contributing
values, learning rate and optimizer/scheduler steps. The JSON record records its
successful completion and measured timings. Each arm consumed 128 clips / 2,048
images / 276,824,064 contributing scalar targets and advanced optimizer/scheduler
once; gradients were finite and nonzero. This is a bounded integration audit, not
an admitted pilot or a learning/equivalence result.

## Verification and remaining work

All 57 tests passed locally (104.32 seconds), including 12 new admission tests.
The separate read-only code review found no actionable issues in one round; it ran
two focused tests and independently verified the accepted preview. Root performed
the full suite and eight-grid generation. CI uses synthetic admission fixtures;
it does not run the native macOS renderer. This is not Sudarshan's verification.

J5 still needs grouped split/lineage validation beyond sampled-instance hashes.
J6/J2 still need the 100-grid tail check and later frozen 1,000-grid corpus. J7 tiny
collision/order/tracking sets and J8 operational scoring can now proceed independently
under Joy's ownership. Independent S4/S5 verification/research review remains useful
and pending; it is not the implementation dependency. Future larger drops need
near-duplicate and group/split audits before scientific use.

No H1–H4 gate, visual task solvability, useful learning, transfer, statistical
precision, cross-platform pixel reproducibility or CVPR readiness is established.
Private files are outside the RGB loader root, but OS-level access isolation has not
been implemented. No full study, paid compute, collaborator message or final-test
inspection was performed. Original/current SPEC and Sudarshan's devlog are preserved.
