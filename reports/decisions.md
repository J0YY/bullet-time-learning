# Decisions — bullet-time-learning

## 2026-10-28 — Establish collaboration structure

**Authority:** Joy's request to read the bullet-time spec, set up collaboration
with Sudarshan like safety-repartitioning, commit as work proceeds, and check it.

- Import the supplied specification unchanged as `SPEC.md`.
- Reuse the workflow structure: identity/startup rules, each person's own devlog,
  shared context, ownership map, versioned handoffs, staged work and normal main
  publication. Adapt all scientific instructions to bullet-time.
- Assign Joy training/loading/readouts/integration/resource coordination and
  Sudarshan game/data/rendering/splits/independent analysis as the working plan.
  Sudarshan's acknowledgment remains unrecorded and does not block authorized setup.
- Start resource decisions afresh. No inherited compute host, deadline, experiment,
  allocation, model/software pin, result, protocol freeze, or approval.
- Keep implementation staged behind the spec's actual scientific gates. Setup
  completion is distinct from the first research deliverable.

**Scientific protocol changes:** none. **Final freeze:** none.
See [setup audit](setup-audit.md) for source hash and verification.

## Future decision format

Record date, owner, actual authority, question, selected option and reason,
affected SPEC sections/contracts/configs, supporting evidence, and implications
for existing outputs. Freeze records bind exact source/config/split/analysis hashes,
endpoints, margins, sample size/stopping rule, and test-access timing. Deviations
after freeze identify affected claims and any need for fresh confirmation data.

## 2026-10-28 — Record requested feasibility review without freezing new choices

**Authority:** user requested double-checking the full setup and original spec for
CVPR feasibility and idea quality. [Audit](cvpr-feasibility-audit-20261028.md).

Recorded primary-source findings and reproducible arithmetic; clarified that the
existing 30/70 contrasts are View-relative and added implementation choices to the
draft interface checklist. The scientific specification remains byte-identical to
its original import. Proposed title, evaluation partition/cadence, competence
thresholds, sample size, compute, and venue decisions remain unselected. A review
recommendation is not a user-approved protocol change or submission commitment.

## 2026-10-28 — Revision 1: bounded pilot and audit resolutions

**Owner:** Joy. **Authority:** user explicitly requested updating the spec to address
found issues, a concrete Joy/Sudarshan pilot with minimal mutual bottlenecks,
preserving the original in Git, incremental commits and checks.

**Selected:** working paper title “Same Images, Different Experience: World-Time
versus Viewpoint Pretraining”; retain repository nickname. Add BulletTime/FL4N
comparison and bound novelty to exact-image/fixed-objective regrouping. Fix 64 Hz
physics / 16 Hz forecast and causal tracking evaluation, current-frame/reference
access, coordinates, visibility, small-object rule and repeated-image spatial
adapter. Reserve SSv2 official validation for final evaluation; derive internal
development and label subsets by deterministic hashes from official training.
Use View-relative 30/70-component claims, never same-margin all-pairs equivalence.
Keep joint power and episode precision separate from single-contrast seed examples.

**Pilot:** one projectile family, 1,000 pretraining grids, 600/200/400 episodes per
measurement task, six VideoMAE arms × seeds 17/29/43, twenty passes with a four-pass
screen, 300 game labels and 10% external readout labels; readout seeds 101/102/103.
Separate native/image/untrained/external and supervised diagnostics; numerical
operational gates and count ledger are in [pilot plan](../docs/pilot-plan.md) and
[planning JSON](../configs/pilot-plan.json). These are selected prospective pilot
defaults, not measured performance, final-study margins or authorization to run.
Runtime hyperparameters/software pins and resources must be resolved before jobs.

**Affected:** SPEC §§2, 7–9, 11 and revision header; planning/interface/ownership docs.
**Reason:** resolve the [audit](cvpr-feasibility-audit-20261028.md)'s ambiguities,
prevent overclaiming and expose complete pilot costs/dependencies. Closest-work and
conference findings retain primary-source citations in SPEC; DINOv2 reference is
checked against its official model release. No credible full-study commitment to
the imminent CVPR deadline is adopted.

**Impact:** no existing research outputs to migrate. The original source metadata
is unchanged; original blob is `13e951dcbc02d94734241034ff85bbc56d530fa6:SPEC.md`.
Current revised SPEC SHA-256: `ed37f7e10d999bbdddf118455de5146fc952afac1566d15cfab1d7e8bd929c24`.
The mathematical audit is regenerated against this revision. Later changes need
new provenance; the final protocol/sample size/compute allocation remain unfrozen.

### Revision 1 implementation boundary and dependency clarification

Working contracts become v1; v0 had no implemented artifacts, so no deployed
migration is required. Preserve producer/consumer validation as pending. Joy owns
consumer fixtures/adapters; Sudarshan owns producer and analysis fixtures/adapters.
Their JSON/CSV boundary does not require shared Python imports or Joy's package
bootstrap. Add explicit owned test directories and a Sudarshan-owned data CI file.
Progressive 1/8/100/1,000-grid drops unblock the first actual update at eight grids.
The early three-slot screen can proceed after H1/H2 while H3 measurements are
built; expanding to all eighteen still requires H3 and early stability. Either
owner can submit their own authorized jobs; Joy coordinates the shared resource
ledger rather than individual submissions. No access or experiment is granted by
these assignments. This clarification changes workflow, not the SPEC bytes above.

The first three screen slots require the same complete 1,000-grid pretraining
bundle as the final pilot. Eight-grid update smoke tests and any 100-grid training
prototypes are separately counted diagnostics, never resumed as pilot slots.
Measurement-set work may overlap this screen. The invariant bag diagnostic must
encode frames independently with no temporal context/positions before mean pooling;
averaging contextual video features would leak order and invalidate the control.

## 2026-10-28 — Joy implementation controls and evaluation v2

**Authority:** active user request to implement Joy's part, rigorously check research
and implementation, and continue until genuinely dependent on Sudarshan. Base
`c10b678`; original SPEC unchanged. Work remains in Joy-owned paths.

- Use isolated Python 3.11 / torch 2.9.1 and pinned VideoMAE source
  `14ef8d856287c94ef1f985fe30f958eb4ec2c55d`, retaining attribution/noncommercial
  license. The wrapper uses the released small encoder/192-wide four-layer decoder.
- Keep grid order fixed inside each four-pass cycle, shuffle between cycles, and
  assign mixture phases by each family's rank. This gives exact four-pass per-grid
  counts and balanced prefixes throughout training, with common update membership.
- Initial controlled pilot has no crop/color jitter. Native diagnostic uses the
  released per-clip multiscale crop, independent tube masks and normalized targets.
  Both keep the explicit pilot optimizer; this is a small-model recipe diagnostic,
  not a reproduction of published large-scale accuracy. Initial development LR
  7.5e-5, warmup 2 passes, AdamW betas .9/.95, decay .05, float32 are candidate
  runtime choices to test on real development data, not a main-study freeze.
- Evaluation input v2 adds explicit frame indices, fixed reference index/identity
  and query ID so consumer causality is checkable. No existing producer artifacts
  migrate silently. Tracking auxiliary occluded train/dev queries prevent training
  visibility only on reappearance positives; the primary three-frame endpoint and
  episode/fit budgets stay unchanged. The first occluded frame is the minimal
  recommended auxiliary query; S3 validates actual visibility and simulator time.
- Actual labels, pair/physics provenance and expected prediction keys stay separate
  from model features. Per-episode readout weighting avoids giving longer tracking
  episodes extra loss weight. Frozen backbone hashes and explicit missing outputs
  are checked. Final-test or official-validation data cannot enter pilot fitting.

**Evidence limits:** synthetic byte/tensor/model tests, not real rendered-data,
learning, transfer or statistical-power evidence. Empirical H1–H4 still require
S2/S3/S4 artifacts and appropriate resources. See the implementation checklist.

### 2026-10-28 EDT — Concrete Joy consumer choices

- **Authority:** implement Joy's work and rigorously check research controls. SPEC
  remains unchanged. Interfaces clarify consumer-only v2/groups/label formats; S
  producer validation is still pending.
- **Controls:** whole-pair nested label budgets; separate heads per forecast horizon;
  consecutive tracking primary frames and occluded auxiliary visibility queries.
  Actual run/checkpoint/label-budget hashes bind exported predictions.
- **Supervised measurement:** all seven diagnostic fits use the same pinned external
  DINOv2 ViT-S/14 initialization and common development recipe, fine-tuned end to end.
  This strengthens visual solvability checks while remaining separate from the random-
  initialization causal pretraining arms. A failed diagnostic cannot justify a null.
- **External/runtime:** DINO source/weight hashes are committed in models/pins; PyAV
  16.1.0 decodes ordered RGB with recorded FFmpeg versions. CPU source/model/decoder
  tests do not validate selected CUDA hardware or any real data gate.

### 2026-10-28 EDT — Preserve diagnostic identity and assessment eligibility

- **Authority:** independent implementation review under the requested check/fix
  workflow. SPEC science and original import remain unchanged.
- **Correction:** supervised sequence/final/bag/current diagnostics share a parent
  initialization but must not share prediction keys. Their run IDs now bind the
  full diagnostic configuration/mode; checkpoint IDs identify fitted weights.
  Frozen-readout identity keeps its parent/checkpoint convention. Explicit mapping
  is exported for S4; no real producer/analysis artifacts require migration.
- **Access:** readout checkpoints preserve allowed prediction splits. All SSv2 and
  early/incomplete learned models are dev-only; game assessment permits completed
  20-pass learned backbones and declared untrained/external references. Enforcement
  runs before input loading. Unknown progress or missing policy fails closed.
- **Additional guard:** real pilot admission rejects non-arena/mixed-family corpora.
  Receipt provenance still cannot substitute for a substantive scientific audit.

### 2026-10-28 EDT — Align query geometry and executing-source provenance

- **Review correction:** PIL bilinear resizing uses a half-pixel-center affine;
  endpoint-aligned query mapping displaced points on resized inputs. Corrected the
  affine, documented its convention and added interior impulse-image tests in both
  orientations, at identity size and when downsampling. Native 224-square inputs
  remain identity. Edge-center coordinates clip only outside the canvas center range.
- **Completeness check:** fit/inference now record the executing consumer source/pins
  and actual runtime, distinct from the pretrained checkpoint's older source. Reject
  inference under changed consumer code. Exclude independent S-owned code from this
  fingerprint because it is not imported; bind its delivered data/report bytes at the
  interface instead. This preserves parallel collaborator work and reproducibility.

## 2026-10-30 EDT — End-to-end pilot ownership and independent verification

**Owner/authority:** Joy explicitly requested redistributing responsibilities so
progress almost never depends on the other collaborator. Baseline `7d305e0` was
clean and equal to freshly fetched `origin/main`; Sudarshan's devlog had no work
entries. This is evidence of published state only, not a claim about private work.

**Decision:** transfer producer foundation S1 → Joy J5, rendering S2 → J6 and
measurement generation S3 → J7. Joy J8 owns required operational metrics, coverage,
paired statistics and power planning. Joy also owns SSv2 access/split audit, asset
licenses, novelty refresh, resource ledger and release. All required pilot tasks
now have one end-to-end owner; no S4/S5 completion or acknowledgment gates them.
Sudarshan retains separate S4a fixture-based verification, S4b snapshot audits and
S5 literature/claim review, with exact disjoint paths and first-delivery acceptance.
No messages, acknowledgment, execution or verification are attributed to him.

**Reason:** the original layer split left every real-data input and operational
score dependent on a separate person. Keep independent review useful without making
it the only available implementation. Required validity/coverage/access gates stay
unchanged; confirmed correctness findings still block affected evidence.

**Affected:** SPEC §11's owner sentence only; AGENTS, shared context, ownership,
README, RUNBOOK, pilot/interface/operator docs, historical checklist pointer and a
new independent-review brief. Existing task aliases remain in historical records.
No schema fields, versions, seeds, counts, thresholds, objectives or endpoints change.
Planning JSON and all runtime code/configs remain byte-identical to baseline.
Assessment generation/admission emits label-free inventories for fitting/inference;
restricted scoring follows the same declared version lock. These access boundaries
must be implemented/validated before use; same-person operation is not human
blinding or independent collaborator review. Independent-corpus replication and
future final-test freeze requirements are retained.

**Provenance/impact:** original source remains unchanged at `13e951d:SPEC.md`.
Current SPEC SHA-256: `bff787e8650f543b47e2f12bafb1081d62f80c377936a12762693da30ef85112`.
Regenerate spec/pilot arithmetic reports for the documentation hashes; scientific
arithmetic must match the prior report. No existing research output needs migration.
Unimported source exclusions describe execution dependencies, not who owns files;
future runtime imports require source-binding coverage, and scoring binds its own
code/config. No game data, new scientific result, full-study or paid run is created
by this change. Independent verification remains pending rather than waived or
claimed complete.

## 2026-10-30 EDT — Bounded local arena integration implementation

**Authority:** Joy requested the next one-arena, preview, eight-grid consumer-audit
step. Joy's agent selects implementation details within SPEC §§4–5/12; this does
not authorize the larger pilot or alter scientific endpoints/margins.

**Decision:** pin Godot 4.5.1 macOS Compatibility/OpenGL and original procedural
assets. Use 64 Hz Godot rigid-body physics, separate mesh-only rendering, 224 RGB,
16 × 16 grids and strides 16/8/4. Use seeded closed orbits and local ovals. Admit a
whole grid only when every state has at least eight views with ≥4 projectile and
≥12 target class-mask pixels, with exact replay/repeat-pixel checks. These are
prospective engineering defaults, not a visual-solvability threshold or final
freeze. An eight-grid pool cycles the three strides; larger-pilot balancing remains
separate. Preserve failures rather than silently dropping cells or changing arms.

**Scope/limits:** one scripted launch/target-contact mechanic establishes an actual
physics/rendering integration path. It does not establish gameplay breadth, visual
reasoning, sensitive tests or novelty. Instance fingerprints and exact cross-grid
RGB checks do not validate grouped splits or near-duplicate leakage. All grids stay
in a pretraining-only integration pool; the same procedural asset family must stay
together when future splits are designed. Private evidence is outside the consumer
root but not protected by a local OS access sandbox. J7 owns future isolation/tests.

**Affected:** new game, generation/rendering configs, producer code/data scripts,
tests and producer guide. Existing SPEC, pilot science, RGB wire contract and
consumer runtime remain unchanged. Original SPEC remains in Git. No prior research
outputs migrate; accepted bundle bytes bind the source/config/runtime that made them.

## 2026-10-30 EDT — Implement a bounded development measurement drop

- **Authority/reason:** Joy requested J7/J8 implementation and continuation without
  collaborator bottlenecks. Start with small real-rendered measurements before
  committing resources to full visual sensitivity fits.
- **Choice:** 16 train and 8 dev groups per collision/order/tracking task; forward
  elastic projectile reflection, periodic rail release and two constant-velocity
  drones under a roof. Pin 64 Hz control/physics checks and 16 Hz observations;
  retain existing input v2, label v1 and group v1 consumer wires. No assessment.
- **Affected sections:** implementation of SPEC §7 / Stage two and J7's tiny first
  delivery, detailed in [the evaluation producer guide](../docs/evaluation-producer.md).
  Pilot counts, budgets, models, H3 criteria and final-study defaults are unchanged.
- **Impact/limits:** these development microtasks require real rendered visibility,
  independent Godot contacts, lineage/duplicate admission and consumer checks. Their
  simple geometry does not establish gameplay breadth or visual solvability. Full
  J7 sets, joint pretraining lineage, assessment isolation and H3 remain separate
  required work; neither S4 completion nor collaborator acknowledgment is added.

## 2026-10-30 EDT — Randomized assessment labels and local access boundary

- **Authority/reason:** Joy's continuing J7/J8 assignment requires assessment labels
  to remain unavailable to fitting/inference. A canonical hash of a binary target
  without a secret nonce can be guessed; file separation alone is insufficient.
- **Choice:** private label v2 adds an independent cryptographic 256-bit nonce per
  assessment record. Public provenance hashes the complete salted record. Retain
  train/dev v1. A producer-only sealer makes the private/public exports; no actual
  assessment data existed to migrate. Reject unsalted assessment labels.
- **Local boundary:** a bounded macOS job launcher denies private read/write and
  network access, verifies denial before launching, and retains command/profile/
  runtime/log receipts. It has no unconfined fallback and requires existing private
  roots plus probe files. Linux/CUDA needs a separate validated mount implementation.
- **Affected:** evaluation target validation and interfaces, producer sealing CLI,
  local job launcher and tests. This implements SPEC access/provenance requirements
  without changing scientific endpoints, sample sizes, H3/H4 thresholds or the
  unchanged original SPEC. Fitted consumers must retain their original code snapshot
  or be regenerated under the new source hash. Existing results remain historical.
- **Limits:** restricted trusted jobs are not adversarial-code isolation or human
  blinding. All raw labels, private generation evidence, copies and previous score
  outputs must also be excluded from fitting/inference. Actual assessment generation,
  protocol lock and one-time release remain disabled/pending; a receipt is not a release.

## 2026-10-31 EDT — Exclude cross-split tracking background proximity before rendering

- **Authority/reason:** Joy's continuing J7 data/quality assignment. The first
  eight-group-per-stratum prefix passed, but a targeted native probe found a later
  training/development pair with no visible objects and whole-image MAE 0.00256436,
  below the declared 1/255 limit. The full prospective v1 selection is therefore
  not eligible for a full render/admission. Preserve it and the failed probe.
- **Prospective data-only rule:** for tracking, disallow a new group if a group in
  another split has the same camera bin modulo 16 (half-turn roof/floor symmetry)
  and palette L1 distance ≤4. Record excluded candidate indices and draw complete
  replacement groups in the existing seeded order. Keep seed 20261028, accepted
  count targets and all pixel thresholds. This conservative metadata guard targets
  the observed failure; it is not proof that all other pixel duplicates are absent.
- **Timing/scope:** no model was fitted to this full-selection dataset, no H3/H4
  outcome inspected, and no assessment generated. Reconstruct a new immutable
  selection version and rerun pixel admission; do not retrofit the old snapshot.
  This is implementation of pilot data admission, not a change to SPEC endpoints,
  margins or post-outcome sample-size selection.
- **Raw reuse:** revised prospective selections may reuse a retained group's raw
  captures only when canonical request bytes, native game/rendering source bytes,
  runtime pin and every stored file hash match. Changed/missing requests render
  afresh in a new output; old outputs stay intact. Rebuild/revalidate all exports
  and the complete resulting set. Never mix learned runs across changed corpora.

## 2026-10-31 EDT — Remove reconstructible identifiers from assessment preparation

- **Authority/reason:** Joy's continuing J7 access/quality assignment. The prior
  privacy review found that public branch IDs and deterministic private requests
  can reveal binary targets despite salted label commitments.
- **Implementation:** a producer-only opaque export randomizes episode/query/group/
  image names, sorts public records by those names and strips PNG metadata without
  altering decoded RGB. Retain source maps privately; sample label nonces after
  renaming and preserve actual query, temporal, reference and pair relationships.
- **Affected:** new generation utility/CLI, focused synthetic tests and assessment
  access guide. Input v2, label v2 and group v1 remain unchanged. New preparation
  receipt v1 is explicitly not a release or physical/lineage admission receipt.
- **Limits:** no real assessment generation, model execution, outcome inspection
  or protocol freeze. Private source randomness and verified access boundaries
  remain required; H3/H4 staged-release policy is still unresolved. This changes
  no SPEC endpoint, count, threshold, seed budget or original spec bytes.
