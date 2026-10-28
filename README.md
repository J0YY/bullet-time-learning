# Bullet-Time Learning

**Does World Motion Add Beyond Camera Motion?** — Joy Yang and Sudarshan.

Train models on the same rendered images, organized by world time, camera view,
mixtures, or joint motion. Measure what those relationships add to frozen visual
representations. The [research specification](SPEC.md) defines the study.

**Current state:** collaboration scaffold only. No game scenes, rendered grids,
training runner, experimental results, validated compute environment, or frozen
protocol exist yet. The first research deliverable is a rendered grid, an audited
training update, and a solvable visual history test—not a full-study launch.

The [October 28 feasibility audit](reports/cvpr-feasibility-audit-20261028.md)
supports a bounded pilot, identifies missing related work and evaluation details,
and advises against promising the full study for the imminent CVPR 2027 deadline.
The original specification remains unchanged; recommendations are not a protocol freeze.

## Start here

1. Read [AGENTS.md](AGENTS.md) and [SHARED_CONTEXT.md](SHARED_CONTEXT.md).
2. Read the full [SPEC.md](SPEC.md) before first substantive work.
3. Check [division-of-labor.md](division-of-labor.md), then your own environment
   and recent log entries: [Joy](joy-devlog.md), [Sudarshan](sudarshan-devlog.md).
4. Follow [RUNBOOK.md](RUNBOOK.md) for session startup, validation, handoffs, and
   publishing to `main`.

Joy owns training, sequence loading, readouts, integration, and execution planning.
Sudarshan owns game/data generation, rendering, splits, and independent analysis.
Both meet at [draft versioned interfaces](docs/interfaces.md). Assignments are a
working plan; Sudarshan's personal acknowledgment has not been recorded.

```bash
git clone https://github.com/J0YY/bullet-time-learning.git
cd bullet-time-learning
python3 scripts/check_scaffold.py
```

The checker uses only Python's standard library and Git. It verifies repository
structure, local documentation links, original-spec provenance, and artifact
ignore rules. It does not validate a renderer, model, or scientific result.
GitHub write permission is required to push; public clone access does not grant it.

## Project map

| File | Purpose |
| --- | --- |
| [SPEC.md](SPEC.md) | Supplied scientific protocol, imported without edits |
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | Agent instructions and Claude entry point |
| [SHARED_CONTEXT.md](SHARED_CONTEXT.md) | Current status, task registry, and cross-chat handoffs |
| [division-of-labor.md](division-of-labor.md) | Owners, first tasks, dependencies, and acceptance gates |
| [RUNBOOK.md](RUNBOOK.md) | Reproducible collaboration and Git workflow |
| [docs/interfaces.md](docs/interfaces.md) | Draft data, run, prediction, and analysis contracts |
| [joy-devlog.md](joy-devlog.md) / [sudarshan-devlog.md](sudarshan-devlog.md) | Per-person work and environment records |
| [meta-feedback.md](meta-feedback.md) | Dated review of risks and open choices |
| [reports/decisions.md](reports/decisions.md) | Decision authority, protocol changes, and freeze status |
| [reports/setup-audit.md](reports/setup-audit.md) | Setup provenance, validation evidence, and limits |

The future source layout is defined in the ownership map; paths are not marked
implemented merely because they are assigned. Keep generated RGB, hidden-state
labels, checkpoints, caches, and run outputs outside Git. Version lightweight,
release-appropriate manifests, configuration, provenance, and reports.

This project reuses the collaboration structure of safety-repartitioning. It has
its own science, resource decisions, dependencies, and evidence. The supplied
literature assessment has not been independently refreshed during setup.
