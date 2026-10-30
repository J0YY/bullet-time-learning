# Pilot v1 — concrete work for Joy and Sudarshan

Selected 2026-10-28 at Joy's request. This is an implementation plan, not completed
research, a main-study freeze, or authorization to launch jobs. [SPEC](../SPEC.md)
governs the science; [planning JSON](../configs/pilot-plan.json) records counts and
seeds. It is not accepted by a training runner. The [ownership map](../division-of-labor.md)
and [wire contracts](interfaces.md) let both people start independently.

## The decision this pilot must support

Can one instrumented projectile arena produce an exact-image comparison with
visually solvable temporal tasks, useful frozen learning/transfer, and affordable
precision? Report feasibility whichever condition wins. No equivalence claim,
CVPR acceptance prediction, V-JEPA matrix, or full 16n-run launch follows from
three pilot seeds. The original full-study design remains conditional in SPEC.

The most important risks are loss of learning under the controlled recipe, tasks
that can be solved from shortcuts or cannot be solved visually, weak synthetic-to-
real transfer, and inadequate seed/episode precision. Each has a concrete check
below. Two more families, V-JEPA, spatial/second-external probes, independent-corpus
replication and capacity sensitivity belong to the later main-protocol stage.

## Start independently, integrate in small drops

**October 30 ownership update:** Joy owns every required pilot component end to
end. Sudarshan owns independent verification and research review, with no required
S-task dependency for pilot development. This changes responsibility, not the
scientific defaults, counts, gate thresholds or launch authority below.

| Work package | Joy's required pipeline | Sudarshan's independent track | Acceptance |
| --- | --- | --- | --- |
| Foundation | J5: Godot/assets, producer/schema, grouped splits and replay; J8: operational scorer fixtures; J1 consumer already implemented | S4a: standalone metrics/coverage verifier on own known-answer predictions | Separate component checks against existing wire contracts |
| First real slice | J6 → J2: one-grid preview, then 8-grid actual update, then 100-grid tail/replay audit | Extend boundary fixtures, exposure checks and S5 literature/claim review | H1/H2 from actual producer and consumer evidence, both Joy-owned |
| Measurements | J7 → J3/J8: collision/order/tracking data, physics checks, visual controls and scoring; Joy also prepares/audits SSv2 | S4b: audit eligible immutable train/dev snapshots when available | H3 sensitive visual tasks, valid input access and complete scoring |
| Bounded learning | J4/J8: resources, native/controlled checks, early screen then gated expansion and full operational report | Recompute eligible metrics, check hierarchy/coverage and report discrepancies | H4 validity/learning/transfer/precision, including failures |

These assignments launch no agents or jobs. Separate producer/consumer validation
remains required even under one owner; it is not independent collaborator review.
S4/S5 may remain pending while Joy progresses through substantiated gates. A
confirmed invariant violation must still be fixed before affected evidence is used.
See the [ownership map](../division-of-labor.md) for disjoint paths, task migration
and the [verification brief](independent-review.md) for the first S4 delivery.

The eight-grid actual update is an integration smoke test, separately costed; it
is not one of the eighteen training slots. The pilot never resumes a 100-grid
prototype as a 1,000-grid run. Each drop is immutable and includes manifest/config/code hashes, validation report,
artifact location and one reproduce command. Publish the small manifest/report to
Git; RGB and hidden labels stay outside it. Deliver the next drop without waiting
for a meeting. Keep the last accepted contract working while adding a new version.
Do not share a writable worktree or a mutable “latest” data directory.

## Data and input choices

Use one projectile-arena family, fixed rigid-body parameters, Godot saved-state
replay, no motion blur/trails/history-dependent effects, and master data seed
20261028. Pin the actual engine, assets and code before generating accepted data.
One grid is 16 world states × 16 cameras, 224 × 224 RGB. Preserve SPEC's three
pretraining cadences; balance 1/4, 1/8, 1/16-second grids as 334/333/333 within the
1,000-grid corpus and report the one-grid rounding imbalance. Evaluation always
uses 16 Hz RGB and 64 Hz physics, never a variable unseen time interval.

| Set | Train | Development | Pilot assessment | Unit and isolation |
| --- | ---: | ---: | ---: | --- |
| Pretraining | 1,000 grids | None | None | Unique rollouts; separate from every readout split |
| Ordinary collision | 600 | 200 | 400 | Episodes: 300/100/200 opposite-outcome pairs at the primary 0.5 s horizon |
| Same-image-bag order diagnostic | 600 | 200 | 400 | Episodes: 300/100/200 distinct forward-generated pairs; separate from ordinary collision |
| Causal tracking | 600 | 200 | 400 | Episodes with one designated occlusion each; 3 scored reappearance frames |

All numbers are **accepted** examples after data-only admission checks; log attempts
and exclusions. Tracking counts target the primary ≥16-pixel-diagonal stratum;
retain encountered small-object examples separately. Counterfactual pairs, source
rollouts, configurations, trajectory families and asset groups never straddle
splits. Use independent group pools for pretraining/train/dev/assessment, and fail
closed on shared groups. Asset groups mean content/appearance variants that could
leak identity, not common engine code or the primitive mesh library. Audit exact
and near-duplicate renders across splits. Fix grouping definitions and hashes in
J5 before building the sets; naming different files is not independence.

The first 100 accepted grids can become a subset of the 1,000 only if producer,
config and image hashes remain unchanged and all are in the pretraining group
pool. Otherwise regenerate; do not carry a stale smoke bundle into a new version.
The 100-grid audit has twelve 8-grid updates and one final 4-grid update. Keep the
same tail in every condition with correct loss normalization; no dropping it.
The 1,000-grid pilot divides into 125 full updates per pass.

Use 300 labeled episodes per game readout for the pilot (150 complete pairs for
collision/order). Build nested 100/300/600 episode subsets by sorting whole groups
by SHA-256 of `bt-game-label-v1:20261028:<group_id>`; admit complete groups in that
order. In this pilot every independent collision/order group is one pair and every
tracking group one episode. If lineage merges groups, regenerate to these units
or version the count plan; never split a merged group to hit a quota. Train the
supervised solvability diagnostics on all 600. Optional 100/600 frozen learning
curves require additional ledger entries; they are not in the base run count.

Pilot assessment is a development-stage check, not final-test evidence. Tune on
the 200 development episodes; inspect assessment once per declared pilot version.
A failed version stays in the ledger. After outcome-driven repairs, generate a
fresh assessment group pool, retain the old results and label all as pilot work.
Joy's generation/admission process emits a label-free expected-key inventory and
keeps assessment labels out of fitting and inference mounts. A separate scoring
process receives them only after the declared pilot-version lock; verify access
boundaries before use. Same-person operation does not establish human blinding or
independent review. Sudarshan receives only synthetic/train/dev snapshots before
that release. No pilot group may enter a later confirmatory test. Final-test data
do not exist yet; later freezes must bind their hashes and access controls before opening them.

SSv2: use SPEC §7's class-stratified, hashed internal development split from official
training and 10% of the remaining training partition for labels. Reserve official
validation unopened for final evaluation. Joy owns licensed access, the split/
duplicate audit and the implemented deterministic partitioner. Validate the actual
metadata, group integrity and reproducible hashes before learning; S4 can recompute
these later without becoming a personal sign-off gate. Use 16 uniformly spaced
frames, one clip/video and deterministic letterbox as specified. Do not report a guessed global 10% count:
class rounding and any grouped duplicate exclusions determine the actual manifest.

Tracking uses [t−15,…,t], current RGB included, one fixed pre-occlusion reference
RGB/point, no future RGB; the reference must remain in all three scored windows.
Use normalized top-left coordinates, visibility threshold 0.5 and distance ≤1/8 of
the full projected box diagonal in 224-pixel coordinates. Spatial checks later
repeat one image 16 times; no neighboring video frames may enter that control.

## Models, slots and budget

VideoMAE pilot: ViT-S, 12 blocks, width 384, 6 heads, 16-pixel spatial patches,
2-frame tubelets, 90% tube mask, raw RGB targets, shared grid crop/color/masks,
8 complete grids/update. Paired pretraining seeds **17, 29, 43**; readout seeds
**101, 102, 103**. Primary readout: 2 attention layers, width 256. No final-test
selection, cross-clip attention or batch-dependent normalization.

At J1/J4, pin released VideoMAE code and its decoder/optimizer defaults. Export
explicit LR, warmup, decay, precision, decoder dimensions and all overrides in an
executable runtime config before any pilot run. They are deliberately not guessed
from the planning JSON. One common recipe selected on pooled View/Time/Mix50
**development** results applies to all controlled arms. Any tuning trial is a
separate counted run. Pin all runtime/artifact revisions, including external models,
before downloading/executing them. Unresolved pins/resources block execution, not
independent CPU implementation or data-design work.

| Slot group | Count | Exposure/checkpoints | Role |
| --- | ---: | --- | --- |
| Controlled VideoMAE | 18 | 6 conditions × 3 paired seeds; 20 passes; save 4 and 20 | View, Time, Mix50, Joint, Shuffled Time, Regrouped |
| Native-recipe diagnostics | 2 | View/Time × seed 17; 20 passes, evaluate 20 | Same small backbone/corpus; published masking/normalized targets; record all departures |
| Same-corpus image-MAE | 3 | Seeds 17/29/43; 20 full frame passes; evaluate 20 | Separate image architecture; match 5,120,000 frame presentations/run |
| Untrained video references | 3 checkpoints, 0 training runs | Same initializations as paired video seeds | Frozen readout floor |
| External image reference | 1 checkpoint, 0 pretraining runs here | DINOv2 ViT-S/14 without registers, frozen | Separate external-data competence reference, not a matched causal arm |
| Supervised diagnostic models | 7 fits | Seed 101, train 600/task; select on dev | Sequence collision/order/tracking; final-frame collision/order; invariant bag order; reference+current-frame tracking |

For the seven supervised diagnostic fits, use one selected image-feature backbone
and matched-width heads across the restricted/sequence variants; select the common
capacity/optimization on development data and record actual trainable parameters.
The final-frame controls see only that RGB (repeated if the adapter needs 16 frames)
and the identical query points. The invariant bag model encodes each image
independently with a shared frame encoder, no temporal positions/context, then
mean-pools before its query-conditioned head. Averaging contextual video tokens
is not an invariant bag control. Verify invariance under arbitrary input
permutations, not just the one paired trajectory. Sequence diagnostics may access
ordered frames; the tracking control receives only fixed reference + current RGB.
These supervised models establish measurement sensitivity, not frozen feature
quality. Any architecture/hyperparameter search adds explicitly counted fits.

The external reference is the released `dinov2_vits14` model; resolve code and
weights to immutable revisions/checksums during environment setup. Apply it
framewise and pass ordered spatial features to the same readout family, recording
tokenization/adaptation differences. [Official DINOv2 models](https://github.com/facebookresearch/dinov2).
Native validation is a small-model diagnostic, not reproduction of published
large-scale accuracy. The two native runs do not establish seed-robust equivalence.

First run View/Time/Mix50 at seed 17 only to the 4-pass checkpoint. These are three
of the eighteen planned slots. Start this early screen after H1/H2, the complete frozen 1,000-grid
pretraining bundle and resource validation, in parallel with measurement-model work; H3 and early stability must
pass before expanding to all eighteen. Use the twenty-pass scheduler from step zero; do
not restart a four-pass cosine schedule as a twenty-pass run. If hashes and recipe
stay fixed, resume them to 20 and fill the other fifteen slots after the early
gates. If the recipe changes, retain the failed trials and rerun affected slots
under a new pilot version. Do not claim eighteen includes discarded experiments.

Frozen-head accounting: four tasks (collision, order diagnostic, tracking, SSv2),
three readout seeds each. Evaluate the first three controlled slots at pass 4
and all eighteen at pass 20: **252 fits**. Native references add 24; image-MAE 36;
untrained 36; external image reference 12. Base total **360 frozen-head fits**, plus
seven supervised fits, feature extraction and any explicitly counted tuning.
Other saved pass-4 checkpoints are loss/throughput diagnostics, not additional
mandatory head fits. Reuse an identical reference head by hash, never retrain it
silently for each arm. Run final game assessment only on pass-20/fixed references;
early-screen heads use development only. SSv2 stays internal-development-only
throughout this pilot. No automatic spatial, linear-head, 80-pass or V-JEPA runs.

For 1,000 grids: 256,000 RGB images = **38.535168 decimal GB** uncompressed;
16,000 clips/pass; 320,000 clips and 2,500 optimizer steps per twenty-pass run.
The eighteen controlled slots total **5,760,000 clips and 45,000 optimizer steps**.
At a measured 100 clips/s this would be 16 GPU-hours, or 80 GPU-hours at 20 clips/s,
for those slots only on one GPU. These are arithmetic scenarios, not benchmarks.
Native/image/supervised models, the 360 heads, rendering, features, checkpoints,
failed/tuning runs and data beyond pretraining all cost extra.

Joy records measured throughput, peak memory, storage expansion and a complete
GPU-hour estimate after the eight-grid smoke update, plus rendering, annotation
and data-storage costs. Sudarshan records costs of his separate verification work.
Before launch, fill a resource ledger with
actual host/access, available storage, maximum authorized GPU-hours and per-stage
stop limits. There is no selected host, financial commitment or approved quota
in this plan. Either person may run their own authorized commands on validated
resources; Joy coordinates the ledger rather than serving as a job-submission gate.

## Acceptance, repair and exit rules

These numerical thresholds are **chosen pilot engineering gates**, not empirical
facts, final equivalence margins, p-values or guarantees of paper quality. A gate
cannot pass on a favorable subset: require all planned slots and expected
predictions for that stage, or mark it incomplete and retain failures. The pilot
has one family, so report arena scores directly; never fill absent families with
zero or call them a three-family average. Lock them before examining this pilot version's assessment data; retain failures.

| Gate | Evidence required | If it fails |
| --- | --- | --- |
| H1/H2: controlled inputs | Zero missing/duplicate index cells, hash mismatches, forbidden metadata inputs or split violations; repeated state/camera renders pixel-identical on pinned runtime; actual source-coordinate mask/target/update audit for all 8 schedules and tail update; camera closure/visibility/contact review | Repair producer/consumer, bump affected artifact version, rerun audit before training |
| H3: history and order sensitivity | Each supervised sequence classifier ≥80% balanced accuracy and ≥20 percentage points above its final-frame control on pilot assessment; order also ≥20 points above the invariant bag model. Complete opposite-label pairs, identical restricted inputs and deterministic predictions must give restricted controls 50% BA (tolerance 0.1 point); invariant bag probabilities must agree within 1e−6 within each pair | Audit labels/inputs/shortcuts, improve data or diagnostic model on dev; retain failure and use fresh assessment after repairs |
| H3: tracking sensitivity | Supervised sequence reacquisition ≥70% and ≥10 points over fixed-reference+current-frame control on assessment; report size/occlusion strata and all exclusions | Repair ambiguous identities/visibility/tolerance or control implementation on dev; do not reinterpret a weak test as no temporal signal |
| Early stability | On first 3 runs through pass 4: finite loss/gradients, observed parameter changes, reproducible resume, loss below initial checkpoint on a fixed pretraining diagnostic subset under identical masks; valid budgets and actual update audit | Stop expansion; repair shared recipe/runtime, retain failed costs |
| H4: learning and recipe | At pass 20, pooled View/Time/Mix50 mean exceeds matched untrained reference by ≥5 points on collision or tracking; controlled View/Time seed-17 scores are no more than 5 game points or 2 SSv2 points below their native counterparts, across the applicable tasks | Diagnose optimization/control adaptation and narrow recipe claim; no main launch on uninformative features |
| H4: external competence | On internal SSv2 dev, external image reference P ≥ untrained U +5 points; pooled controlled score C ≥ U + max(5 points, 0.5×(P−U)). Average readout seeds within checkpoint, then pretraining seeds, then the 3 fixed coherent arms | If P fails, debug head/data; if C fails, report limited transfer and reconsider diversity/initialization as a separately versioned study; do not swap the primary dataset |
| H4: grouping sensitivity | Fixed pooled coherent mean (View/Time/Mix50) exceeds Regrouped by ≥2 points on collision or tracking, or ≥1 point on SSv2, at pass 20 | Record objective-insensitivity as a possible limited finding; do not present a strong null or keep adding runs until a gain appears |
| H4: precision/resources | Paired seed differences plus paired episode-group uncertainty; conservative variance/correlation scenarios and simulated power for the chosen future 30/70-component claim; measured full-cost ledger | Keep main n/margins/budget unselected if unaffordable; no “five is enough” assumption |

The grouping screen is descriptive selection for future feasibility, not a
multiplicity-controlled scientific result. Main superiority contrasts, correction,
practical margins and global power must be frozen later; neither a three-seed
pilot nor screening a best endpoint licenses confirmation. Always report all four
tasks and individual coherent arms, including failures hidden by pooled scores.

For H4, Joy's J8 operational scorer computes metrics from hashed predictions;
Sudarshan's S4 implementation independently checks eligible snapshots when available.
Each first averages readout seeds within checkpoint, then forms paired differences
between pretraining seeds matched across conditions. Pending S4 verification is recorded explicitly, never inferred
from agreement between Joy's own components.
Report per-episode/pair coverage and paired resampling sensitivity. Do not treat
three readout seeds or hundreds of frames as extra pretraining seeds. Include
uncertainty in pilot variance and insufficient episode precision when projecting
main counts; do not assert empirical power from three seeds.

If the bounded pilot passes, write the main-study proposal with remaining families,
V-JEPA/native checks, held-out/independent corpus and scale costs, a refreshed
novelty comparison and frozen analysis/access plan. If it fails, deliver the failure
report and the smallest evidence-backed revision. This plan contains no automatic
repeat-until-pass loop and no commitment to the November 2026 paper deadline.
