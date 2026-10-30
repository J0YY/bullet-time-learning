# Shared context — bullet-time-learning

Last updated: 2026-10-30 EDT. Read the live files and Git state before acting.

## Authority and status

This is the common handoff record for Joy's and Sudarshan's project chats. Read
[AGENTS.md](AGENTS.md) first; [SPEC.md](SPEC.md) governs science and
[division-of-labor.md](division-of-labor.md) governs ownership. The user's current
request controls scope. Historical log entries do not override newer decisions.

**Stage:** Joy consumer complete; required producer/data/scoring reassigned to Joy; research gates pending.
The original import remains unchanged in Git at `13e951d:SPEC.md`; current SPEC
adopts the user-requested audit fixes and pilot defaults. Joy's RGB consumer,
scheduler/collator audit, VideoMAE/image-MAE runner, resumable checkpoints and
readout/input/export components now run on synthetic fixtures. Renderer/game grids,
real producer integration, operational scoring, independent verification, resource
allocation, empirical research results and final protocol freeze remain pending.

Effective 2026-10-30 at Joy's request, Joy owns the complete required pilot pipeline,
including game/data/rendering/splits, training/readouts and operational analysis.
Sudarshan owns separate independent verification and research review; his completion
is not a pilot-development prerequisite. See the exact path map and first tasks in
[ownership](division-of-labor.md). His acknowledgment/environment remain unrecorded.
GitHub had a pending write invitation for `deephelms28` at setup; acceptance is not
assumed. Compute resources are unselected for this project.

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
| REDISTRIBUTE | Joy | User-requested end-to-end pilot ownership and separate nonblocking verification track | Complete; 45 regression tests and workflow/provenance checks pass | Reassignment `2ff0980`; J5–J8 remain unimplemented; no Sudarshan acknowledgment claimed |
| J1 | Joy | Consumer fixtures, all schedules/RNG/update tests, JSON adapter and exports | Complete; 45 tests and Linux CI pass; cumulative review clean in round 3 | Working v1 contracts; no S task or schema import needed |
| J5 (was S1) | Joy | Producer schema/fixtures, Godot/asset pins, grouped splits, scripted arena and replay | In progress: user authorized arena → 8-grid integration milestone | Base `30750b1`; Joy owns game/generation/rendering/splits/data tests; local runtime validation first |
| J6 (was S2) | Joy | Progressive 1 → 8 → 100 → 1,000 real-grid drops | In progress for preview and 8 grids only; larger drops later | Publish immutable RGB and state/camera/lineage evidence at each drop |
| J2 | Joy | Actual-loader/update audit; 100-grid tail check | Fixture/model-update path tested; real data pending | J1 + Joy J6 first 8 grids |
| J7 (was S3) | Joy | Collision/order/tracking sets, oracle/input checks and sealed assessment exports | Pending working J5 scene | Tiny train/dev slices before full corpus; same H3 counts/access rules |
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
compute and submission remain unselected; no experiment has run.

Joy starts J5/J6: one scripted projectile arena and a complete 256-cell preview,
then eight real grids through the existing J2 actual-update audit. J7 measurement
generation and J8 operational scoring are independent follow-on queues owned by
Joy, not collaborator handoffs. All H1–H4 evidence and resource/access gates remain.
Sudarshan starts S4a using [the independent-review brief](docs/independent-review.md);
he can finish fixtures and S5 before any real run exists. Publish eligible snapshots
without waiting for review; fix confirmed correctness findings before using affected
evidence. Missing independent verification stays explicitly pending.

The [operator guide](docs/joy-handoff.md) contains current commands/contracts. The
[October 28 completion audit](reports/joy-implementation-audit-20261028.md) remains
historical evidence for the consumer only; its S-task ownership is superseded here.
No real producer/data/scoring implementation or research experiment is claimed by
this reassignment. Sudarshan's log and all prior history are preserved.

## Update rules

Re-read before each edit. Patch your task/status only, retaining others' concurrent
updates. Record source commit, contracts/hashes, exact checks, limits, next owner,
and whether work is published. Move detailed history to your own devlog or report.
Do not infer acceptance from silence, assign work retrospectively, or record an
independent review that did not occur. Protocol changes belong in the dated
[decision record](reports/decisions.md), with actual authority.
