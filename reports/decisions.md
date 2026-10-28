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
