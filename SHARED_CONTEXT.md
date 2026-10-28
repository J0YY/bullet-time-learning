# Shared context — bullet-time-learning

Last updated: 2026-10-28 EDT. Read the live files and Git state before acting.

## Authority and status

This is the common handoff record for Joy's and Sudarshan's project chats. Read
[AGENTS.md](AGENTS.md) first; [SPEC.md](SPEC.md) governs science and
[division-of-labor.md](division-of-labor.md) governs ownership. The user's current
request controls scope. Historical log entries do not override newer decisions.

**Stage:** collaboration scaffold. The complete research specification has been
read and imported unchanged. No renderer, grids, loader, training, evaluation,
analysis, resource allocation, results, or protocol freeze exist yet.

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
| SETUP | Joy | Spec import, collaboration docs, checker/CI, Git publication | In progress; final audit pending | Empty repository; initial import `13e951d` |
| J1 | Joy | Sequence loader and audit foundation on fixtures | Ready, not started | Draft interfaces; coordinate schema with S1 |
| S1 | Sudarshan | Data schema, fixtures, split validator, renderer design | Ready, not started | Draft interfaces |
| S2 | Sudarshan | First scene and 100 rendered grids | Not started | S1; renderer/runtime/resources |
| J2 | Joy | Actual-loader and training-update audit | Not started | J1 + S2 |
| S3 | Sudarshan | Paired history/order/tracking data | Not started | S1/S2 |
| J3 | Joy | Visual-solvability controls | Not started | S3; resources/runtime |
| S4 | Sudarshan | Independent metrics/statistics fixtures | Ready, not started | Draft run export; later J2/J3 integration |

## Immediate handoff

Joy can start J1; Sudarshan can start S1 and record his own environment. The
[draft interfaces](docs/interfaces.md) specify the shared boundary. Next joint
checkpoint: rendered grid + audited update + solvable visual history test. All
scientific implementation and producer/consumer validation are still pending.

## Update rules

Re-read before each edit. Patch your task/status only, retaining others' concurrent
updates. Record source commit, contracts/hashes, exact checks, limits, next owner,
and whether work is published. Move detailed history to your own devlog or report.
Do not infer acceptance from silence, assign work retrospectively, or record an
independent review that did not occur. Protocol changes belong in the dated
[decision record](reports/decisions.md), with actual authority.
