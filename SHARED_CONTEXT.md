# Shared context — bullet-time-learning

Last updated: 2026-10-30 EDT. Read the live files and Git state before acting.

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
Grouped evaluation generation, larger drops, operational scoring, independent
collaborator verification, research compute, empirical learning and freeze remain pending.

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
| J7 (was S3) | Joy | Collision/order/tracking sets, oracle/input checks and sealed assessment exports | Ready on the working J5 scene; unimplemented | Tiny train/dev slices before full corpus; same H3 counts/access rules |
| J8 | Joy | Operational metrics, coverage/failed slots, paired analysis and power scenarios | Ready; unimplemented | Own known-answer fixtures now; eligible J3 exports later; no S4 import |
| J3 | Joy | Causal heads, seven controls, external adapter plus SSv2 acquisition/split audit | Consumer implemented; real J7/external data pending | J7 sets for H3; licensed official-training metadata/videos for external checks |
| S4a/S4b | Sudarshan | Standalone independent verifier, then snapshot metrics/exposure/lineage/statistics audits | Assigned; acknowledgment/work unrecorded | Own fixtures now; eligible immutable snapshots later; not a prerequisite for Joy |
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
Next: Joy J7 tiny measurement sets and J8 operational scoring, with J5 grouped-split
validation and J6/J2 100-grid tail checks before larger drops. These queues have no
collaborator handoff dependency. H1–H4 and research resource/access gates remain.
Sudarshan starts S4a using [the independent-review brief](docs/independent-review.md);
he can finish fixtures and S5 without accessing Joy's artifacts. Publish eligible snapshots
without waiting for review; fix confirmed correctness findings before using affected
evidence. Missing independent verification stays explicitly pending.

The [operator guide](docs/joy-handoff.md) contains current commands/contracts. The
[October 28 completion audit](reports/joy-implementation-audit-20261028.md) remains
historical evidence for the consumer only; its S-task ownership is superseded here.
The real producer and integration are now measured; operational scoring and
scientific experiments remain unimplemented/unrun. Sudarshan's log is preserved.
Implementation and final evidence/handoff are committed on main; publication is
checked before the chat handoff. No collaborator review or acknowledgment is inferred.

## Update rules

Re-read before each edit. Patch your task/status only, retaining others' concurrent
updates. Record source commit, contracts/hashes, exact checks, limits, next owner,
and whether work is published. Move detailed history to your own devlog or report.
Do not infer acceptance from silence, assign work retrospectively, or record an
independent review that did not occur. Protocol changes belong in the dated
[decision record](reports/decisions.md), with actual authority.
