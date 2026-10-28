# Division of labor — Joy & Sudarshan

**2026-10-28:** working plan for the requested collaboration setup. No research
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
| Scripts/tests | `scripts/` default, shared fixtures/harness, integration tests; tests for Joy-owned modules | `scripts/data/`, `scripts/analysis/`; tests for Sudarshan-owned modules |
| Execution | Select/validate resources for the project; coordinate rendering/training/evaluation/analysis runs and resource ledger | Supply reproducible generation/rendering/analysis commands and requirements; validate own access if needed |
| Writing | Scientific framing, training/readouts, results integration, manuscript default | Data/statistics sections, `paper/figures/`, `paper/tables/`, references and reproducibility inventory |

Joy is default owner of unassigned paths; record intentional reassignment in
[decisions](reports/decisions.md) and shared context. Each person owns their own
devlog. Shared context is updated by the active task owner with narrow patches.
This plan does not grant either person access to the other's machines/accounts.

## Shared documents and research operations

| Deliverable | Owner | Required input/check |
| --- | --- | --- |
| SPEC, AGENTS, CLAUDE, README, RUNBOOK, this plan, interfaces, setup audit, meta-feedback | Joy | Sudarshan may propose changes; user's assignments authorize scoped edits |
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

These are tasks for the collaborators' future sessions, not automatically launched
agents or chats. Task IDs are stable handoff labels, not completion claims.

| Task | Owner | Deliverable and acceptance | Depends on |
| --- | --- | --- | --- |
| J1: loader foundation | Joy | Package/config/test harness; all eight conditions, four-pass mixtures, shared RNG and complete-grid update contract on synthetic grids; deterministic audit and malformed-input rejection | Draft grid contract; coordinate schema imports with S1 |
| S1: data foundation | Sudarshan | Versioned grid/evaluation schema and synthetic fixtures; grouped split validation; Godot scene/state-capture design and asset provenance | Draft interfaces |
| S2: first rendered scene | Sudarshan | 100 complete grids; replay pixel identity, frozen world state/camera independence, smooth closed camera paths; rejection/visibility/contact report | S1, pinned renderer/runtime and selected resources |
| J2: audited real update | Joy | Real-loader exposure, augmentation, post-collator masks, raw-target and complete-update audit; controlled/native VideoMAE validation design | J1 + S2 delivered bundle |
| S3: measurement data | Sudarshan | Valid forward paired histories, equal-image-bag diagnostic, causal tracking set, labels and split checks | S1/S2 |
| J3: visual solvability | Joy | Supervised sequence/final-frame/bag controls; identical permitted inputs and meaningful diagnostic results | S3 + selected compute/runtime |
| S4: analysis foundation | Sudarshan | Fixture-checked paired effects, family weighting, seed/readout hierarchy, TOST and multiplicity logic, power planning | Draft run export; integrate with J2/J3 outputs |

Joy can build loader fixtures while Sudarshan builds schema/rendering. Avoid both
editing `schema.py`; agree the import boundary through the draft contract. The first
integration checkpoint is the spec's rendered grid + audited update + solvable
history test. Passing synthetic checks alone does not reach it.

## Later stages and gates

| SPEC stage | Joy | Sudarshan | Gate |
| --- | --- | --- | --- |
| 1: controlled images | Actual loader/update audit | Rendering/state/splits and independent audit | Same immutable image exposure, all conditions, valid replay and visibility |
| 2: measurement and pilot | 18 reconstruction pilot runs on 1,000 grids: six conditions × three paired seeds; native/reference/readout work budgeted separately | Solvable paired tasks, metric validation, exclusion/leakage review, conservative variance/power estimates | Sensitive measurements and useful learning; measured compute/storage |
| 3: main freeze | Validate V-JEPA, external transfer, common recipes, readout budget, capacity/budget plan | Three families, finalized splits, margins/claim scope, power and independent-corpus plan | Dated protocol/config/manifest/analysis freeze before final test |
| 4: conditional full study | Two objectives × eight conditions × n paired seeds; references, readouts and replications separately counted | Independent paired analysis, family effects, coverage, tables/figures | All prespecified arms reported; claims bounded by actual evidence |

No calendar deadline, final sample size, compute host, or protocol freeze is set
by this scaffold. The 16n main-run count excludes pilots and supporting work.
Independent-corpus replication and held-out-family evaluation are different checks.
