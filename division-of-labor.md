# Division of labor — Joy & Sudarshan

**2026-10-30 reassignment, authorized by Joy:** Joy owns the complete required
pilot pipeline. Sudarshan owns a separate verification package and research review.
This replaces the October 28 split by layer. It removes personal handoffs from
the pilot's critical path; it does not remove scientific gates or create results.
Sudarshan's acknowledgment and any unpublished work remain unverified.

## Ownership map

Joy is the default owner of all required implementation, data, analysis and shared
documents. Sudarshan's reserved paths below are an independent implementation,
never an import or required service for Joy's pipeline. Planned paths do not imply
implemented code. Each person owns only their own devlog.

| Area | Joy: complete operational pipeline | Sudarshan: independent verification |
| --- | --- | --- |
| Source | `src/bullet_time/` except `analysis/`; includes `schema.py`, `generation/`, `rendering/`, `splits/`, all `evaluation/` including `metrics.py`; `game/` | `src/bullet_time/analysis/` only; self-contained checker/scorer, no imports from Joy's implementation |
| Configs/build | `configs/` except `analysis/`; package/dependency locks, aggregate CI, `.github/workflows/data.yml` | `configs/analysis/`; optional standalone `.github/workflows/analysis.yml`; no shared package-bootstrap prerequisite |
| Scripts/tests | `scripts/` except `analysis/`; `tests/` except `analysis/` and `fixtures/analysis/`; includes data/producer tests and new `scripts/scoring/`, `tests/scoring/`, `tests/fixtures/scoring/` | `scripts/analysis/`, `tests/analysis/`, `tests/fixtures/analysis/`; own known-answer fixtures |
| Data and resources | All required game/renderer/assets, provenance, manifests, split/duplicate checks, restricted labels, SSv2 preparation, storage/runtime ledger | Read-only immutable snapshots; independent hash, lineage, exposure and coverage checks; own authorized audit environment |
| Reports and writing | `reports/data/`, `reports/analysis/`, manuscript/figures/tables, `docs/novelty-ledger.md`, protocol/power/claims and release | `reports/independent/` for reproducible discrepancies, independent results and literature notes |
| Shared workflow | SPEC, AGENTS, README, RUNBOOK, interfaces, pilot plan, ownership and shared context | Propose changes with concrete evidence; maintain own task rows/log |

Godot/asset selection, licenses, external data access, closest-work refresh,
operational statistics, power planning and final release are explicitly Joy-owned.
They cannot become hidden prerequisites owned only by Sudarshan. Submission,
spending and new compute commitments remain user decisions. Neither assignment
grants access to the other person's machines or credentials.

## Joy's execution queue

J1/J3 consumers and the first arena producer are implemented. The one-grid preview
and eight real grids are recorded in the [integration report](reports/arena-integration-20261030.json).
Grouped evaluation generation, larger drops and operational scoring remain pending.

| Task | Deliverable and acceptance | Dependency / priority |
| --- | --- | --- |
| J5: producer foundation (formerly S1) | Pin Godot/assets; one scripted projectile arena; saved-state replay and smooth camera loop; schema/producer fixtures; group/split rules and license inventory | Start here; written contracts and local runtime validation, no Sudarshan prerequisite |
| J6: progressive grids (formerly S2) | One real 256-cell preview, then 8 complete grids with PNGs, `pretrain.jsonl`, `bundle.json`, hashes and state/camera/split reports; later 100 and frozen 1,000 grids | J5; hand each immutable drop to Joy's own consumer as soon as ready |
| J2: real-update integration | All eight schedules through actual optimizer/exposure audit on 8 grids; 100-grid tail check (12 full updates + 4-grid tail); measured resource costs | J6 first 8, then 100; no need to finish 1,000 first |
| J7: measurement sets (formerly S3) | Collision/order/tracking input, separate label/group and physics evidence; first 16 complete paired groups per collision/order task and 16 tracking episodes, then 600/200/400 accepted episodes per task | Working J5 scene; can start before J6 reaches 1,000; tiny slice is plumbing only |
| J8: operational scoring/statistics | Separate label joins, expected-key inventory, collision/tracking/SSv2 metrics, coverage/failure ledger, paired seed/group analysis and prospective power scenarios | Implement against own known-answer fixtures immediately; consumes J3 exports later; never imports S4 scorer |
| J3: sensitive readouts and external data | Existing seven controls/heads plus real J7 integration; Joy acquires permitted SSv2 training data and validates deterministic grouped split/duplicate rules | Fixtures now, J7 for game sensitivity; licensed metadata/resources for external checks |
| J4: bounded pilot and report | Resource validation; H1/H2; frozen 1,000 grids; three-slot four-pass screen; H3 + early stability before expansion; complete H4 operational report via J8 | Evidence and authorized resources, never S4/S5 completion |

The current J5/J6/J2 milestone and measured audit status are in
[shared context](SHARED_CONTEXT.md). Next independent queues: **J7 tiny measurement
sets and J8 operational scoring**, alongside planning the 100-grid tail check.
Use the [operator guide](docs/joy-handoff.md) and [producer guide](docs/arena-producer.md). The existing [pilot plan](docs/pilot-plan.md) still controls counts,
seeds, budgets and launch gates. This queue does not launch jobs automatically.

## Sudarshan's independent workstream

| Task | Concrete deliverable | Dependency |
| --- | --- | --- |
| S4a: independent scorer foundation | Standalone CLI, own known-answer fixtures/tests, collision BA, three-frame tracking reacquisition, SSv2 top-1 and strict missing/duplicate/hash/label-join checks; reproducible report | Versioned CSV/JSON contracts only; no renderer, model checkpoint, Joy scorer or actual run needed |
| S4b: evidence audit | Recompute metrics from a pinned export; compare with Joy's J8 report; check exposure/splits, paired hierarchy/uncertainty and failure coverage; provide minimal reproductions for discrepancies | First eligible immutable snapshot, not all runs; until available, extend synthetic boundary/statistical tests |
| S5: literature/claim review | Cited closest-work comparison and concrete claim/measurement risks in `reports/independent/`; distinguish implemented, measured and proposed work | Public primary sources and current spec; no Joy output required |

First delivery is S4a, with a commit, command, fixture hashes, observed results and
limits. Exact acceptance and snapshot contents are in
[the independent-review brief](docs/independent-review.md). S4/S5 strengthen the
project but are not pilot-development prerequisites. Required novelty/analysis
work still has a Joy-owned implementation if these deliveries never arrive.

## Integration without a personal approval queue

1. Joy validates producer and consumer components separately against unchanged
   JSON/CSV contracts and records actual evidence for each. Same-person checks are
   self-validation, not independent collaborator review.
2. Joy publishes immutable manifests/reports and eligible prediction snapshots
   as milestones finish. Sudarshan pulls a pinned snapshot and works on his own
   schedule; neither pipeline waits for the other's acknowledgment or shared class.
3. Sudarshan returns a discrepancy report keyed by commit, artifact hash, expected
   result and reproduction command. Joy triages it in the next integration pass.
   A confirmed invariant violation blocks affected evidence until fixed; silence
   is neither acceptance nor a reason to halt unrelated valid work.
4. Use disjoint paths and separate checkouts; normal fetch/merge/push only. A new
   task claims explicit files in shared context before editing. In-progress work
   discovered later is preserved and integrated deliberately, never overwritten.
5. Keep the last accepted artifact/version usable. Required-field/semantic changes
   need a new contract version and compatibility export/migration; ownership alone
   changes no wire version. A malformed artifact fails locally with a concrete
   diagnosis, without stopping work on fixtures or another valid artifact.

S1 → J5, S2 → J6, S3 → J7 are historical task aliases, not active assignments to
Sudarshan. Required scoring previously in S4 moves to J8; S4 now names independent
verification only. Earlier logs/reports preserve the old assignments as history.

## Data isolation and honest evidence

Joy prepares assessment data through a separate generation/admission process that
emits hashed, label-free expected inventories. Training/tuning and inference jobs
receive only allowed inputs; the scoring process alone receives assessment labels
after the declared pilot-version lock. Verify the mounts/permissions and access
tests before real assessment. A hash allowlist or same-person workflow is not
proof of human blinding or independent review. Do not use assessment outcomes for
tuning; a repaired pilot version needs a fresh assessment group pool.

Sudarshan initially receives synthetic or train/dev audit snapshots only. Assessment
access, for either person, follows the same locked-version evaluation policy.
SSv2 official validation and eventual final tests remain unavailable to tuning.
Final confirmatory freezes/access rules remain required and unimplemented.

H1–H4 evidence, complete coverage, sensitive visual controls, prospective precision
and cost checks remain mandatory. Missing independent verification is recorded as
pending; neither Joy's implementation nor another agent on Joy's work is Sudarshan's
review. Independent-corpus and held-out-family replications stay required for the
claims that use them. There is no promise of a bottleneck-free study: data validity,
resources and scientific feasibility still limit progress, but no required pilot
component has an unavailable collaborator as its sole owner.
