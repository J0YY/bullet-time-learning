# Joy pilot implementation audit — 2026-10-28 EDT

**Outcome:** Joy's pilot consumer implementation is complete through the point where
real producer data, physics/visibility evidence and independent analysis are needed.
No experiment, learning/transfer result, final protocol freeze or CVPR readiness is
claimed. Start with the [operator/handoff guide](../docs/joy-handoff.md).

Implementation baseline: `c10b678519d93ea59315886b820337b16dcf3230`.
Reviewed implementation: `981bfa309c9712f829513c998d8e056a0eb1dc43`.
Incremental commits: `d0d9bbe`, `4af1a11`, `1e5fa94`, `b1b711e`, `981bfa3`.
All are normally pushed to `main`; original history is preserved.

## What is implemented and checked

- Strict RGB-only consumer with actual file/decoded-pixel hashes, path confinement
  and complete 16×16 grids. Independent producer code/classes are not imported.
- Eight balanced schedules; shared transforms/masks/raw targets; actual per-image
  post-collator audits; complete-grid weighted optimizer updates and retained tails.
- Pinned released VideoMAE, controlled/native recipes, framewise image-MAE, fixed
  scheduler, deterministic FP32 updates and strict source/data/runtime-bound resume.
- Causal evaluation input v2; whole-pair nested label budgets and separate horizon
  heads; frozen heads and all seven supervised control modes; actual RGB/point
  geometry; train/dev-only fitting and stored assessment eligibility.
- Complete expected-key prediction exports with explicit failures/missing rows,
  distinct fitted diagnostic identities, source/runtime provenance and wrong-source
  rejection. S4 still owns independent metrics, label joins and statistics.
- SSv2 internal training/dev/label partitions and group validation, selected-frame
  PyAV decoding, official hash-pinned DINOv2 and three untrained references.
- Exact 23-training/4-reference/360-frozen-fit/7-diagnostic pilot inventory, bounded
  admission checks, resource extrapolation and concrete producer-facing commands.

## Verification evidence

The final implementation has **45 passing tests** locally (50.95 seconds) and from
the clean remote checkout (57.59 seconds). These include real optimizer, checkpoint,
resume, fit/predict and decoder execution; they are synthetic implementation checks.
A full 224-pixel small VideoMAE forward and the official DINOv2 forward also passed.
DINO source/weight/parameter evidence is in [reference setup](reference-setup-20261028.json).
Model caches and checkpoints stay outside Git.

[Linux CI on the reviewed commit](https://github.com/J0YY/bullet-time-learning/actions/runs/40777906142)
passed both scaffold/planning and implementation jobs. Dependency consistency, Ruff
checks/formatting, original-spec provenance, pilot source-hash freshness and
whole-tree whitespace checks pass. The final documentation completion commit is
published and its own CI checked before handoff.

The original SPEC remains byte-identical at `13e951d:SPEC.md`: 62,247 bytes,
SHA-256 `e543446ddf6466e07cbf545a402092ebe2f5d6a6a43465472bd41c4e693fb9de`.
Current SPEC remains unchanged during this implementation, SHA-256
`ed37f7e10d999bbdddf118455de5146fc952afac1566d15cfab1d7e8bd929c24`.
Sudarshan's devlog is unchanged from baseline. No other person's work is recorded.

## Independent review loop

A separate Codex review inspected the cumulative diff against the same baseline
in each round; implementation and corrections remained in Joy's session.

| Round | Reviewed head | Findings / resolution |
| --- | --- | --- |
| 1 | `1e5fa94` | Two P2 correctness findings: diagnostic modes shared IDs; development-only checkpoints could access assessment. Both fixed and tested. Reviewer also independently ran the then-current 34 tests. |
| 2 | `b1b711e` | One P2: query mapping disagreed with PIL's resize affine. Fixed and checked against actual interior marked RGB pixels. |
| 3 | `981bfa3` | No actionable correctness issues found. |

Rounds 2/3 used a read-only sandbox that prevented selected pytest collection/temp
creation. Their clean/static review does not claim a runtime test pass; the root
session, clean checkout and independent Linux CI provide the runtime evidence.
Three correctness findings were fixed; none remain from the review. This is an
independent **implementation** review, not Sudarshan's acceptance or an empirical
scientific review. The temporary local baseline tag is removed after completion.

## Exact remaining handoffs

| Input / gate | Owner | Smallest next delivery |
| --- | --- | --- |
| Real RGB and renderer/lineage evidence | Sudarshan S1/S2 | First 8 complete grids; then 100 including tail audit, then frozen 1,000. One-grid preview can arrive first. |
| Visual history/order/tracking tasks | Sudarshan S3 | Separate RGB inputs, labels/groups and physics/visibility evidence; initial small bundle can precede all pretraining data. |
| Independent metrics and coverage | Sudarshan S4 | Own known-answer prediction fixtures and evaluator; consume first real Joy export when available. |
| Intended hardware/resources and SSv2 access | Project resource selection plus S external-data provenance | Validated host/storage/access and measured full-model costs before research execution. |
| H1–H4 and empirical recipe calibration | Joint artifact-based integration | Actual sensitive controls, native/controlled learning, useful transfer, grouping sensitivity and precision evidence. |

S1/S3/S4 can proceed independently. There is no shared-schema import, all-data-before-
first-integration requirement, submission-through-Joy requirement or new personal
approval queue. Source fingerprints exclude unimported S-owned code, while input
artifacts remain hash-bound. Use immutable source checkouts for long runs.

V-JEPA, three-family main experiments, extra budget/capacity tests, final statistical
freeze and the paper are later conditional work. A well-tested runner does not
answer whether this idea will yield a publishable result; the pilot's real evidence
must decide that.
