# Shared context — bullet-time-learning

Last updated: 2026-10-28 EDT. Read the live files and Git state before acting.

## Authority and status

This is the common handoff record for Joy's and Sudarshan's project chats. Read
[AGENTS.md](AGENTS.md) first; [SPEC.md](SPEC.md) governs science and
[division-of-labor.md](division-of-labor.md) governs ownership. The user's current
request controls scope. Historical log entries do not override newer decisions.

**Stage:** Joy implementation started; producer/data and research validation pending.
The original import remains unchanged in Git at `13e951d:SPEC.md`; current SPEC
adopts the user-requested audit fixes and pilot defaults. Joy's RGB consumer,
scheduler/collator audit, VideoMAE/image-MAE runner, resumable checkpoints and
readout/input/export components now run on synthetic fixtures. Renderer/game grids,
real producer integration, independent analysis, resource allocation, empirical
research results and final protocol freeze remain pending.

Joy owns training/loading/readouts and integration; Sudarshan owns game/data,
rendering, splits, and independent analysis. The detailed path map is the working
assignment. Sudarshan's personal acknowledgment and local environment are unrecorded.
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
| J1 | Joy | Consumer fixtures, all schedules/RNG/update tests, JSON adapter and exports | In progress | Working v1 contracts; no S task or schema import needed |
| S1 | Sudarshan | Producer schema/fixtures, grouped splits, renderer design | Ready, not started | Working v1 contracts; own environment, no Joy package dependency |
| S2 | Sudarshan | Progressive 1 → 8 → 100 → 1,000 real-grid drops | Not started | S1 + renderer/runtime/resources; deliver each drop immediately |
| J2 | Joy | Actual-loader/update audit; 100-grid tail check | Fixture/model-update path tested; real data pending | J1 + S2 first 8 grids; runner/reference work can continue before delivery |
| S3 | Sudarshan | Collision/order/tracking sets and oracle/input checks | Not started | S1 + working scene; does not wait for complete S2 corpus |
| J3 | Joy | Causal heads, seven supervised controls, external adapter | Consumer/readout tests passing; integration work ongoing | Working contracts now; S3 sets for H3 acceptance |
| S4 | Sudarshan | Own synthetic prediction fixtures, independent metrics/statistics | Ready, not started | Working run/prediction v1; first real export later, no need to wait for all runs |
| J4 | Joy | Resource/runtime ledger, early screen and bounded pilot | Runner, candidate configs and slot enumeration implemented; execution not admitted | H1/H2 + complete 1,000-grid bundle + resources for screen; H3 + early stability for expansion |

## Immediate handoff

Read the [revised SPEC](SPEC.md), [pilot plan](docs/pilot-plan.md), and historical
[CVPR feasibility audit](reports/cvpr-feasibility-audit-20261028.md). The selected
pilot is one family, 1,000 grids, six VideoMAE conditions × seeds 17/29/43,
20 passes with a 4-pass screen. Forecast/tracking inputs and SSv2 internal-dev /
reserved-official-validation access are now specified. Main margins, sample size,
compute and submission remain unselected; no experiment has run.

Joy can develop consumers on owned fixtures; Sudarshan can develop producers and
independent analysis on owned fixtures. Deliver 1 → 8 → 100 → 1,000 grids; the first
8 unblock actual update integration. The [ownership map](division-of-labor.md) and [working v1 contracts](docs/interfaces.md)
separate adapters/fixtures, progressive drops and independent job submission. Scientific implementation and producer/consumer integration
remain pending. Start J1 (Joy) and S1/S4 (Sudarshan) independently; J3 can also
begin against fixtures. All 25 files in the substantive revision were verified
byte-for-byte from a fresh GitHub clone; the final completion record is checked
and published before handoff. No acknowledgment is recorded on Sudarshan's behalf.

## Update rules

Re-read before each edit. Patch your task/status only, retaining others' concurrent
updates. Record source commit, contracts/hashes, exact checks, limits, next owner,
and whether work is published. Move detailed history to your own devlog or report.
Do not infer acceptance from silence, assign work retrospectively, or record an
independent review that did not occur. Protocol changes belong in the dated
[decision record](reports/decisions.md), with actual authority.
