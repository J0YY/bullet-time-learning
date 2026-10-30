# Bullet-Time Learning

**Same Images, Different Experience: World-Time versus Viewpoint Pretraining** — Joy Yang and Sudarshan.

Train models on the same rendered images, organized by world time, camera view,
mixtures, or joint motion. Measure what those relationships add to frozen visual
representations. The [research specification](SPEC.md) defines the study.

**Current state:** Joy's training/consumer/readout pipeline and first Godot arena
are implemented. The [October 30 integration report](reports/arena-integration-20261030.json)
records an immutable eight-grid bundle (2,048 real RGBs), replay/camera/pixel checks,
57 passing tests and a clean separate code review. All eight schedules passed the
actual full VideoMAE-S optimizer/exposure audit. [Producer commands](docs/arena-producer.md) reproduce the drop.
Visual solvability, grouped evaluation sets, operational scoring, independent
collaborator verification, compute allocation and empirical learning results are
still needed; the full study is not frozen.

The [October 28 feasibility audit](reports/cvpr-feasibility-audit-20261028.md)
supports a bounded pilot, identifies missing related work and evaluation details,
and advises against promising the full study for the imminent CVPR 2027 deadline.
The [revised spec](SPEC.md) adopts the audit fixes and a [concrete pilot plan](docs/pilot-plan.md). The original remains in Git at `13e951d:SPEC.md`; the final study is not frozen.

## Start here

1. Read [AGENTS.md](AGENTS.md) and [SHARED_CONTEXT.md](SHARED_CONTEXT.md).
2. Read the full [SPEC.md](SPEC.md) before first substantive work.
3. Check [division-of-labor.md](division-of-labor.md), then your own environment
   and recent log entries: [Joy](joy-devlog.md), [Sudarshan](sudarshan-devlog.md).
4. Follow [RUNBOOK.md](RUNBOOK.md) for session startup, validation, handoffs, and
   publishing to `main`.

As of October 30, Joy owns the complete required pilot pipeline, including game
rendering, data/splits, training, evaluation and operational scoring. Sudarshan owns
[independent verification and research review](docs/independent-review.md), which
can start on fixtures and does not block Joy's development. They exchange immutable
snapshots through [versioned interfaces](docs/interfaces.md), with disjoint code
paths. Sudarshan's acknowledgment has not been recorded. Joy's next independent
queues are tiny J7 measurement sets and the J8 operational scorer; larger data
drops follow the checks in the pilot plan.

```bash
git clone https://github.com/J0YY/bullet-time-learning.git
cd bullet-time-learning
python3 scripts/check_scaffold.py
python3 scripts/check_pilot_plan.py --self-test --check-report
```

The checker uses only Python's standard library and Git. It verifies repository
structure, local documentation links, original-spec provenance, and artifact
ignore rules. The pilot checker verifies count/seed consistency and audit hashes.
Neither validates a renderer, model, or scientific result.
GitHub write permission is required to push; public clone access does not grant it.

## Project map

| File | Purpose |
| --- | --- |
| [SPEC.md](SPEC.md) | Current scientific specification; original retained in Git |
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | Agent instructions and Claude entry point |
| [SHARED_CONTEXT.md](SHARED_CONTEXT.md) | Current status, task registry, and cross-chat handoffs |
| [division-of-labor.md](division-of-labor.md) | Owners, first tasks, dependencies, and acceptance gates |
| [RUNBOOK.md](RUNBOOK.md) | Reproducible collaboration and Git workflow |
| [docs/interfaces.md](docs/interfaces.md) | Versioned data/run/prediction contracts; consumer and first producer tested; grouped evaluation/scoring and independent verification pending |
| [docs/pilot-plan.md](docs/pilot-plan.md) | Concrete pilot data, runs, gates and parallel handoffs |
| [docs/independent-review.md](docs/independent-review.md) | Sudarshan’s first standalone deliverable and snapshot audit |
| [configs/pilot-plan.json](configs/pilot-plan.json) | Machine-readable planning counts/seeds; not a training config |
| [joy-devlog.md](joy-devlog.md) / [sudarshan-devlog.md](sudarshan-devlog.md) | Per-person work and environment records |
| [meta-feedback.md](meta-feedback.md) | Dated review of risks and open choices |
| [reports/decisions.md](reports/decisions.md) | Decision authority, protocol changes, and freeze status |
| [reports/setup-audit.md](reports/setup-audit.md) | Setup provenance, validation evidence, and limits |

The ownership map gives Joy all required producer/consumer/scoring paths and
reserves separate audit paths for Sudarshan. Keep generated RGB, hidden-state
labels, checkpoints, caches, and run outputs outside Git. Version lightweight,
release-appropriate manifests, configuration, provenance, and reports.

This project reuses the collaboration structure of safety-repartitioning. It has
its own science, resource decisions, dependencies, and evidence. The October 28 audit refreshed primary-source literature; no independent collaborator review or empirical validation is implied.

## Implemented Joy consumer and handoff

See [the operator guide](docs/joy-handoff.md) for setup, synthetic checks, actual-update
integration, model references, readout commands and Joy’s next J5–J8 deliveries.
Implementation passes fixture checks; real research gates remain unmeasured.
