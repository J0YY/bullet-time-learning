# Division of labor — Joy & Sudarshan

**2026-10-28 revision:** working assignments for the concrete pilot. No research
implementation or collaborator acknowledgment is implied. This keeps the previous
project's split by layer, with new bullet-time tasks and scientific gates.

## Ownership map

Joy owns training, readouts, integration, and resource planning. Sudarshan owns
game/data generation, rendering, splits, and independent metrics/statistics.
Paths below are planned unless listed as implemented in shared context.

| Area | Joy | Sudarshan |
| --- | --- | --- |
| Source | `src/bullet_time/` default/package root; `loading/`, `training/`, `models/`, `evaluation/` except metrics; CLI/common config/provenance | `src/bullet_time/schema.py`, `generation/`, `rendering/`, `splits/`, `analysis/`, `evaluation/metrics.py`; `game/` |
| Scheduling | View/Time/Joint/mixture/control loaders, RNG streams, grid batching, exposure/update audit | Independent schedule/exposure checker and renderer invariants |
| Models | VideoMAE and V-JEPA adaptations/native checks; image-only and untrained references; supervised diagnostic models | Label/oracle validation and independent outcome calculations |
| Evaluation | Frozen readouts, causal input assembly, prediction exports, external readout adapters | Counterfactual/order/tracking datasets, split design, metric definitions and analysis |
| Configs/build | `pyproject.toml`, dependency locks, CI, `configs/` default, models/training/readouts | `configs/generation/`, `configs/rendering/`, `configs/splits/`, `configs/analysis/` |
| Data | Run/checkpoint/prediction provenance and external dataset consumption | Lightweight `data/manifests/`, `data/splits/`, asset/license inventory and external split provenance |
| Scripts/tests | `scripts/` default, `tests/loading/`, `tests/training/`, `tests/readouts/`, `tests/integration/`, `tests/fixtures/consumer/`; common package/CI bootstrap | `scripts/data/`, `scripts/analysis/`, `tests/data/`, `tests/analysis/`, `tests/fixtures/producer/`, `tests/fixtures/analysis/`; `.github/workflows/data.yml` |
| Execution | Coordinate resource choices/ledger; validate and launch Joy-owned work on authorized resources | Own rendering/analysis environment and commands; validate own access and launch own authorized work without routing submissions through Joy |
| Writing | Scientific framing, training/readouts, results integration, manuscript default | Data/statistics sections, `paper/figures/`, `paper/tables/`, references and reproducibility inventory |

Joy is default owner of unassigned paths; record intentional reassignment in
[decisions](reports/decisions.md) and shared context. Each person owns their own
devlog. Shared context is updated by the active task owner with narrow patches.
This plan does not grant either person access to the other's machines/accounts.

## Shared documents and research operations

| Deliverable | Owner | Required input/check |
| --- | --- | --- |
| SPEC, pilot plan/manifest, AGENTS, CLAUDE, README, RUNBOOK, this plan, interfaces, setup audit, meta-feedback | Joy | Sudarshan may propose changes; user's assignments authorize scoped edits |
| Protocol freeze/deviations and future preregistration | Joy | Sudarshan supplies split hashes, margins/power evidence and analysis plan |
| Godot/asset source selection, license and data card | Sudarshan | Joy checks loader needs, storage, and runtime compatibility |
| Model/objective revisions, native-recipe validation, hardware/software pins | Joy | Sudarshan checks exposure and evidence requirements |
| Closest-work refresh and future `docs/novelty-ledger.md` | Sudarshan | Joy checks overlap with actual implementation and claims |
| External dataset licensing/splits | Sudarshan | Joy validates fixed frozen-readout pipeline and development competence |
| Future `reports/data/` and `reports/analysis/` | Sudarshan | Joy reproduces interfaces and analysis outputs |
| Learning/transfer/resource reports and pilot gate summary | Joy | Sudarshan supplies construction, metric, and power checks |
| Release | Sudarshan: data/asset provenance and analysis reproduction | Joy: runnable pipeline, pins, commands, integration and final claims audit |
| Submission, external spending, new compute commitments | User | Concrete proposal and measured feasibility when needed |

## Handoffs

Detailed draft contracts live in [docs/interfaces.md](docs/interfaces.md).

1. **Grid and evaluation bundle:** Sudarshan produces; Joy validates delivered bytes,
   loader restrictions, and split admission. RGB is separated from hidden state.
2. **Run, audit, and prediction export:** Joy produces; Sudarshan validates keys,
   coverage, paired seeds, budgets, and per-episode metrics. Include failed slots.
3. **Independent analysis:** Sudarshan produces; Joy reproduces from hashed inputs.
   Keep conventional uncertainty, equivalence decisions, and exploratory results apart.

Start against explicit synthetic fixtures. Implemented producer validation and
consumer validation are separate status fields. No new human sign-off gate is
needed for normal authorized development, and no independent review is assumed.

## First parallel workstreams

These are assignments for future collaborator sessions, not launched agents/chats.
The [pilot plan](docs/pilot-plan.md) defines data counts, run slots and gates.
Grid/exposure/run v1 and evaluation v2 are the working wire boundaries. Joy's
consumer is implemented; producer/analysis integration remains pending.
Neither side waits for the other's Python classes, package install or full corpus.

| Task | Owner | Concrete deliverable / acceptance | True dependency; work while waiting |
| --- | --- | --- | --- |
| J1: consumer foundation | Joy | Deterministic RGB fixtures in own test folder; all 8 schedules, 4-pass mixtures, separate RNGs, masking and 8-grid/tail update tests; JSON adapter and run/prediction writer | No S task; use the written v1 fields; no import from S-owned `schema.py` |
| S1: producer foundation | Sudarshan | Canonical schema/JSON validator, independent producer fixtures, group/split checks, license inventory, state/renderer design | No J task; standalone data CLI / owned environment; no dependency on Joy's package bootstrap |
| S4: analysis foundation | Sudarshan | Independent synthetic predictions, collision/tracking metrics, paired hierarchy/coverage and analysis report; known-answer and malformed cases | No J task; use v1 prediction table and toy data; real integration waits only for first export |
| S2: progressive rendering | Sudarshan | 1 grid preview, then 8 complete grids and validation report, then 100-grid real audit, then 1,000 admitted pretraining grids | S1 + validated renderer/runtime; each drop independently consumable, do not wait for all data |
| J2: real-update integration | Joy | Validate first 8 real grids, actual transformed-image/mask/raw-target/update audit; later 100-grid audit including 4-grid tail | J1 + S2's 8-grid drop only; while waiting finish resumable runner, references and export tests |
| S3: measurement sets | Sudarshan | Collision/order/tracking generators and 600/200/400 accepted episodes per task; labels, equal-image checks and split reports | S1 and working scene, not completed S2 corpus or J2; first small task drop can precede 1,000 grids |
| J3: sensitive readouts | Joy | Causal input assembler, 7 supervised diagnostics, frozen heads and SSv2 adapter; export predictions at first small task drop | Head development uses fixtures now; H3 acceptance needs S3 full sets and resources |
| J4: bounded pilot | Joy | Resource/runtime pins, early 3-slot screen, 18 controlled slots plus listed references, complete coverage/failed-run ledger | H1/H2 + complete 1,000-grid pretraining bundle + resources for screen; H3 + early stability before expansion; each first result unblocks S4 integration |

J1/J3 use consumer-owned fixtures; S1 uses producer-owned fixtures; S4 uses
analysis-owned fixtures. Each person writes their own checks against the common
contract. This avoids one fixture generator becoming everyone's prerequisite and
keeps an independent check from merely copying a producer's logic. Synthetic
fixtures are clearly labeled and never appear as rendered/research evidence.

### Only these integration handoffs require the other stream

| Handoff | Producer → consumer | Smallest useful drop | Acceptance owner |
| --- | --- | --- | --- |
| H1 | S2 → J2 | 8 complete real grids, immutable RGB inventory, split/state audit; 1-grid preview earlier | Joy: actual update audit; Sudarshan: renderer evidence |
| H2 | S2 → J2 | 100-grid bundle + tail-update/replay/loop evidence | Each validates own side; Joy records integrated evidence |
| H3 | S3 → J3 | First 16 paired collision/order groups and 16 tracking episodes for format plumbing, then full split sets for gates | Joy: visual solvability; Sudarshan: labels/groups/allowed inputs |
| H4a | J2/J3/J4 → S4 | First complete task export for one checkpoint and all 3 readout seeds, plus explicit planned-slot inventory | Sudarshan: schema/coverage/metrics; full paired study analysis waits for all runs |
| H4b | S4 → Joy | Reproducible metrics/uncertainty + source hashes and failure ledger | Joy reproduces; both record limits in their own logs |

The H3 tiny drop is plumbing only and must already have correct group assignments;
it does not qualify for the numeric sensitivity gates. Sudarshan can continue
rendering and analysis while Joy consumes a drop. Joy can continue models/readouts
while waiting for the next data volume. Data generation and metric development
stay on Sudarshan's side; model/input/export code stays on Joy's side.

### Avoid routine coordination becoming a bottleneck

- JSON/CSV files are the interoperability boundary. A canonical Python schema can
  help but is not a required import. Each side owns its adapter and component tests.
- Add optional fields compatibly; readers ignore documented optional additions.
  Required-field/semantic changes get a new version and a producer compatibility
  export until the consumer migrates. Do not silently mutate an accepted bundle.
- Each owner can run and commit their own component checks. Joy owns aggregate CI;
  Sudarshan may maintain the separate data job. Shared CI configuration is not a
  prerequisite for running data/analysis checks locally.
- Resource coordination is a shared ledger, not a requirement that Joy submit
  Sudarshan's jobs. Each uses their own validated access within authorized limits.
- Use separate local checkouts and explicit owned paths. Fetch/merge/push normally;
  no shared worktree, force push, or unannounced cross-owner rewrite.
- Record an actionable blocker after a focused session: failing artifact/hash,
  expected contract, smallest needed fix and fallback task. Continue independent
  work. Do not turn a task handoff into a meeting or personal-approval queue.
- Scientific revisions that affect both streams go through the dated decision
  record and versioned contract. Ordinary implementation does not need joint sign-off;
  claiming real integration does need actual producer/consumer evidence.

## Later stages and gates

| SPEC stage | Joy | Sudarshan | Gate |
| --- | --- | --- | --- |
| 1: controlled images | Actual loader/update audit | Rendering/state/splits and independent audit | Same immutable image exposure, all conditions, valid replay and visibility |
| 2: measurement and pilot | 18 reconstruction pilot runs on 1,000 grids: six conditions × three paired seeds; native/reference/readout work budgeted separately | Solvable paired tasks, metric validation, exclusion/leakage review, conservative variance/power estimates | Sensitive measurements and useful learning; measured compute/storage |
| 3: main freeze | Validate V-JEPA, external transfer, common recipes, readout budget, capacity/budget plan | Three families, finalized splits, margins/claim scope, power and independent-corpus plan | Dated protocol/config/manifest/analysis freeze before final test |
| 4: conditional full study | Two objectives × eight conditions × n paired seeds; references, readouts and replications separately counted | Independent paired analysis, family effects, coverage, tables/figures | All prespecified arms reported; claims bounded by actual evidence |

The pilot has concrete stage gates and selected defaults, but no promised calendar
completion, final-study sample size, compute host, or final protocol freeze. The 16n main-run count excludes pilots and supporting work.
Independent-corpus replication and held-out-family evaluation are different checks.
