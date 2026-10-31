# Shared context — bullet-time-learning

Last updated: 2026-10-31 EDT. Read the live files and Git state before acting.

## Authority and status

This is the common handoff record for Joy's and Sudarshan's project chats. Read
[AGENTS.md](AGENTS.md) first; [SPEC.md](SPEC.md) governs science and
[division-of-labor.md](division-of-labor.md) governs ownership. The user's current
request controls scope. Historical log entries do not override newer decisions.

**Stage:** First arena → eight real grids → full-model update audit complete; research gates pending.
The original import remains unchanged in Git at `13e951d:SPEC.md`; current SPEC
adopts the user-requested audit fixes and pilot defaults. Joy's RGB consumer,
scheduler/collator audit, VideoMAE/image-MAE runner, resumable checkpoints and
readout/input/export components run on fixtures. The pinned Godot arena now supplies
2,048 real RGBs; all eight schedules pass the actual full VideoMAE-S update audit.
Operational train/dev scoring and paired analysis now pass synthetic and actual-CLI
integration, with separate code review clean. A small native measurement drop now
passes producer/consumer admission: 72 groups, 120 episodes and 1,800 RGBs. A one-epoch
DINOv2 fit/predict/score integration completed with all 16 dev predictions; 50% BA
is integration evidence only. Larger
drops, assessment release, independent collaborator verification, research compute,
empirical learning and freeze remain pending.

Effective 2026-10-30 at Joy's request, Joy owns the complete required pilot pipeline,
including game/data/rendering/splits, training/readouts and operational analysis.
Sudarshan owns separate independent verification and research review; his completion
is not a pilot-development prerequisite. See the exact path map and first tasks in
[ownership](division-of-labor.md). His acknowledgment/environment remain unrecorded.
GitHub had a pending write invitation for `deephelms28` at setup; acceptance is not
assumed. Local Apple M3 CPU/native renderer is validated for this integration only; research
compute resources remain unselected.

## Research essentials

- Question: what does temporal grouping add beyond viewpoint grouping when every
  model sees the same RGB cells and receives the same budget within an objective?
- Each immutable grid has 16 states × 16 cameras. Six main conditions: View,
  25/50/75% Time mixtures, Time, and Joint. Add Shuffled Time and Regrouped controls
  per objective; image-only and untrained references are separate diagnostics.
- Four-pass whole-grid mixtures; all Joint phases and both directions; shared
  pixels/augmentations and objective-specific masks; complete-grid optimizer,
  scheduler and teacher updates. Contextual targets and tokens need not be identical.
- VideoMAE raw RGB and V-JEPA feature prediction require separate native-recipe
  validation. Random paired initialization is the main causal study.
- Projectile arena, moving-platform course, object-handling room are proposed
  families. Split related rollouts/assets/trajectories/windows/pairs together.
- Frozen readouts evaluate history-dependent collision, causal tracking, spatial
  controls, and external transfer. Visual sequence versus restricted controls must
  establish solvability, including the same-image-bag order diagnostic.
- Three primary endpoints; 30 global equivalence components, or 70 for the stronger
  all-family claim. Margins/sample size remain provisional; no post-result widening
  or seed addition. Uncertain/weak ties are not practical equivalence.

## Task registry

The user creates purpose-specific chats. Register scoped work here; this document
does not launch chats/agents or authorize messages. Avoid copying lengthy logs.

| ID | Owner | Scope | Status | Base / dependency |
| --- | --- | --- | --- | --- |
| SETUP | Joy | Spec import, collaboration docs, checker/CI, Git publication | Complete; local/clone/CI checks passed | Import `13e951d`; workflow `8d2b61d`; verified implementation `7bfeb73`; see setup audit |
| AUDIT | Joy | User-requested full scaffold/spec and CVPR feasibility/quality review | Complete; clone/math/CI checks passed | Base `d9ec3a8`; substantive audit commit `af32b16`; report and reproducible mathematical checks |
| REVISION | Joy | Revise spec from audit; concrete pilot and independent workstreams; preserve original and verify | Complete; local/fresh-clone/CI checks passed | Spec `9adffbc`; workflow/checks `7e5a6e1`; CI `40765480976` passed; final handoff record follows |
| REDISTRIBUTE | Joy | User-requested end-to-end pilot ownership and separate nonblocking verification track | Complete; 45 regression tests and workflow/provenance checks pass | Reassignment `2ff0980`; implementation progress below; no Sudarshan acknowledgment claimed |
| J1 | Joy | Consumer fixtures, all schedules/RNG/update tests, JSON adapter and exports | Complete; 45 tests and Linux CI pass; cumulative review clean in round 3 | Working v1 contracts; no S task or schema import needed |
| J5 (was S1) | Joy | Producer schema/fixtures, Godot/asset pins, grouped splits, scripted arena and replay | Arena/replay/pins/admission implemented; group/split validation remains | Producer `0693adf`; 57 local tests, separate code review clean; native macOS validated |
| J6 (was S2) | Joy | Progressive 1 → 8 → 100 → 1,000 real-grid drops | Preview + 8 complete (2,048 real RGBs); 100/1,000 pending | Immutable bundles, 32 repeat captures, state/camera/hash evidence; see integration report |
| J2 | Joy | Actual-loader/update audit; 100-grid tail check | All eight schedules pass actual full VideoMAE-S update on 8 real grids; 100-grid tail pending | CPU FP32 seed 17; shared exposure/targets/init/budget; one update each, no learning claim |
| J7 (was S3) | Joy | Collision/order/tracking sets, oracle/input checks and sealed assessment exports | Tiny train/dev drop and privacy foundation verified; full sets and assessment release remain | `c5a175a` native drop; `b530e73` randomized labels/local access boundary; 106 tests plus 37 post-fix checks; privacy review clean round 2 |
| J8 | Joy | Operational metrics, coverage/failed slots, paired analysis and power scenarios | Train/dev scorer, paired-analysis foundation and 54 prospective power scenarios verified; full gate/assessment integration pending | Through `75c22ac`; 87-test full regression plus 33 final focused/CLI checks; separate review clean in round 4; no S4 import |
| J3 | Joy | Causal heads, seven controls, external adapter plus SSv2 acquisition/split audit | Consumer and real J7 fit/predict/score integration complete; full H3/SSv2 pending | `0edab89` one-epoch DINOv2: 95.74 s CPU, 16/16 dev predictions, BA 50%; no H3 pass |
| S4a/S4b | Sudarshan | Standalone independent verifier, then snapshot metrics/exposure/lineage/statistics audits | Assigned; acknowledgment/work unrecorded; first real dev snapshot ready | Own fixtures plus `reports/data/audit-snapshots/diagnostic-dev-v1`; not a prerequisite for Joy |
| S5 | Sudarshan | Primary-source literature and claim review in separate reports | Assigned; acknowledgment/work unrecorded | Spec/public sources; no Joy output prerequisite |
| J4 | Joy | Resource/runtime ledger, early screen and bounded pilot | Runner, candidate configs and slot enumeration implemented; execution not admitted | H1/H2 + complete 1,000-grid bundle + resources for screen; H3 + early stability for expansion |

## Immediate handoff

Read the [revised SPEC](SPEC.md), [pilot plan](docs/pilot-plan.md), and historical
[CVPR feasibility audit](reports/cvpr-feasibility-audit-20261028.md). The selected
pilot is one family, 1,000 grids, six VideoMAE conditions × seeds 17/29/43,
20 passes with a 4-pass screen. Forecast/tracking inputs and SSv2 internal-dev /
reserved-official-validation access are now specified. Main margins, sample size,
research compute and submission remain unselected; only integration updates have run.

The [October 30 integration report](reports/arena-integration-20261030.md) records
the completed arena/preview/eight-grid/full-model milestone. Raw artifacts are local
under `artifacts/arena-preview-v1`, `artifacts/arena-eight-v1` and
`runs/arena-update-v1`; [producer commands](docs/arena-producer.md) reproduce them.
The [measurement report](reports/data/evaluation-integration-20261030.json) records
the admitted `artifacts/evaluation-development-v2` train/dev drop and its limits.
The [real readout report](reports/data/readout-integration-20261030.md) records the
completed bounded integration and measured resource estimates.
Next: full J7 sets/release and J5 grouped-split / J6/J2 100-grid tail work. These queues have no
collaborator handoff dependency. H1–H4 and research resource/access gates remain. An existing CUDA host and storage
path have been requested; local data/validation work continues meanwhile.
Sudarshan starts S4a using [the independent-review brief](docs/independent-review.md);
he can finish fixtures and S5 without accessing Joy's artifacts. Publish eligible snapshots
without waiting for review; fix confirmed correctness findings before using affected
evidence. Missing independent verification stays explicitly pending.

The [operator guide](docs/joy-handoff.md) contains current commands/contracts. The
[October 28 completion audit](reports/joy-implementation-audit-20261028.md) remains
historical evidence for the consumer only; its S-task ownership is superseded here.
The real producer and integration are now measured; operational scoring is implemented
for train/dev with [commands and limits](docs/operational-scoring.md). Scientific
experiments and locked assessment remain unrun. Sudarshan's log is preserved.
Implementation and final evidence/handoff are committed on main; publication is
checked before the chat handoff. No collaborator review or acknowledgment is inferred.

### Active continuation — 2026-10-30 EDT

Joy asked to implement J7/J8 promptly, double-check correctness, push increments and
continue while work can proceed without Sudarshan. Joy's agent owns generation,
evaluation/scoring/statistics, tests/configs and associated shared contracts. Start
with strict operational scoring and tiny forward-valid train/dev examples, then
continue the dependency queue under the unchanged scientific/access/resource gates.
No Sudarshan action is inferred or made a new implementation gate.

Assessment label v2 and a verified local job boundary are implemented; see
[access foundation](docs/assessment-isolation.md). Real assessment release remains
disabled; no protocol freeze, scoring authorization or human blinding is inferred.
Global full J7 train/dev selection is implemented and reconstructed: 1,600 unique
prototype groups / 2,400 prospective episodes / 41,200 planned RGBs, using pilot seed
20261028; see [selection evidence](reports/data/full-development-selection-20261030.json).
This fixes cross-task appearance reuse found by the earlier development-seed stress
check. Its first [native prefix](reports/data/full-selection-preview-20261031.json)
is admitted: six groups / ten episodes / 150 RGBs / 32 query records. The rest of
the full set remains unrendered.
Next: progressive chunk capture and combined pixel/joint-pretraining admission. Joy
owns the generation/config/test changes; no collaborator input is required. The
[bounded raster checker](reports/data/raster-check-20261031.json) passes the unchanged
rule on all 1,800 native images in 3.75 s at 59.1 MB peak RSS; review clean.
Progressive capture and reuse are implemented; review clean in round 2 after a
serialized-catalog fix. The eight-group prefix also passed: 48 groups / 80 episodes /
1,200 RGBs. A targeted native probe then found a cross-split empty-background near
duplicate elsewhere in the full selection. Do not render that full selection.
The prospective background exclusion and exact-request reuse are now verified;
[revised selection/prefix evidence](reports/data/background-guard-integration-20261031.json)
records 24 excluded candidates and all 1,600 replacement-selected groups. The
48-group v2 prefix passes with 47 reused groups and one new capture. Separate
review is clean in round 1; a targeted collision-foreground probe also passes.
Next: render the full v2 train/dev selection using the accepted prefix, then run
combined pixel admission. Pixel thresholds, counts and scientific/resource gates
stay unchanged. Full capture is data preparation, not a learning or assessment run.
The [opaque assessment exporter](reports/data/opaque-assessment-export-20261031.json)
is implemented and verified on synthetic fixtures: exact tensors/pairs preserved,
source identifiers and PNG metadata removed, commitments sealed, and all four
private reads denied in a real restricted consumer job. Separate review is clean
in two rounds. No real assessment exists or is released; data admission and the
locked H3/H4 stage policy remain pending. Full train/dev capture continues.
The first [S4b audit snapshot](reports/data/audit-snapshots/diagnostic-dev-v1/README.md)
is ready in Git with all 16 real dev predictions, labels/groups and fit identities.
Sudarshan can verify it without model/RGB downloads or further Joy deliveries; his
work remains unrecorded and nonblocking.
Joy is testing explicit local MPS support in model/runtime RNG, runner and readout
configuration, with targeted native resume/tail checks. A tiny deterministic probe
passed; this is not a resource admission or pilot launch. Native capture sources
remain unchanged while the full train/dev render runs.

## Update rules

Re-read before each edit. Patch your task/status only, retaining others' concurrent
updates. Record source commit, contracts/hashes, exact checks, limits, next owner,
and whether work is published. Move detailed history to your own devlog or report.
Do not infer acceptance from silence, assign work retrospectively, or record an
independent review that did not occur. Protocol changes belong in the dated
[decision record](reports/decisions.md), with actual authority.
