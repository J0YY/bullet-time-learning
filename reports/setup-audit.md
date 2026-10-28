# Setup audit — bullet-time-learning

**Scope:** user-requested collaboration structure, original-spec import, incremental
commits and verification. This is a self-review of repository setup. It is not an
independent scientific review, literature refresh, renderer/model validation, or
evidence of feasibility.

## Source and authority

- Source filename: `Bullet-Time Learning in Video Games Research Specification.md`.
- Imported to `SPEC.md` with all **62,247 bytes unchanged**.
- SHA-256: `e543446ddf6466e07cbf545a402092ebe2f5d6a6a43465472bd41c4e693fb9de`.
- Original import commit: `13e951dcbc02d94734241034ff85bbc56d530fa6`.
- Machine-readable provenance: [spec-source.json](spec-source.json).
- Origin: `https://github.com/J0YY/bullet-time-learning.git`; empty before setup.
- User authorized adapting the prior project's collaboration structure, committing
  as work proceeds, and checking the finished work.

The original document is renamed to the canonical `SPEC.md` to avoid divergent
copies. Its Git attribute preserves source bytes and intentional Markdown spacing.
Future scientific edits need dated decision provenance; the checker requires the
new SPEC SHA-256 in the decision record while preserving the original Git blob.

## Reused structure and excluded carryover

Inspected the reference project's AGENTS, README, ownership plan, RUNBOOK, shared
context, interface document, devlogs, meta-feedback and Git conventions. Reused
identity detection, own-devlog attribution, shared-context startup, ownership by
layer, versioned producer/consumer handoffs and normal main publication.

Rewrote scientific guardrails and tasks against all 12 bullet-time SPEC sections.
No former research code, dataset, result, cluster restriction, GPU job wrapper,
runtime/model pin, deadline, freeze, or collaborator approval was imported.
The old checkout was read only and was not edited.

## Ownership and state review

- Every planned code/config/test/document/release area has an owner or Joy's
  explicit default. Sudarshan's data and analysis boundaries are named precisely.
- Startup, narrow shared-context updates, handoff evidence, concurrent main
  integration, and publication checks are documented.
- All four contracts are marked draft/unimplemented/unvalidated. Renderer,
  loader/update, solvability, transfer, and power checks remain distinct gates.
- Eight arms per objective, 18 reconstruction pilot runs, 16n main runs, 30 primary
  and 70 stronger equivalence components agree with the spec; supporting runs are
  explicitly additional. No sample size, margin, host, or freeze is finalized.
- Sudarshan's devlog is an empty template attributed to this setup. GitHub currently
  lists a pending `write` invitation for `deephelms28`, the write collaborator on
  the reference repository. Setup did not issue/change it or assume acceptance.

## Validation record

- `python3 scripts/check_scaffold.py`: passed locally on Python 3.14.3;
  18 required files, 13 Markdown files, 49 local file links, 32 ignore-rule cases,
  CLAUDE import and original/current SPEC provenance verified.
- `git diff --check` and complete committed-tree whitespace check: passed.
- Verified current upstream action tag revisions before pinning checkout/setup-python
  in CI. CI uses Python 3.12, read-only repository permission, and no third-party
  Python dependencies or experimental execution.
- Self-reviewed ownership, interface status, scientific guardrails and stage
  arithmetic against the supplied spec. No independent review was performed.
- Clean-checkout reproduction, rejection-path checks and remote CI/publication
  verification are pending and will be recorded after execution.

## Remaining research work

Begin J1/S1 from the [ownership plan](../division-of-labor.md), then integrate the
first rendered grid, audited update, and visual history test. Compute/runtime,
asset licensing, actual data contracts, native-recipe validation, transfer and
precision remain future work. See [meta-feedback](../meta-feedback.md).
