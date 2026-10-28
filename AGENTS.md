# AGENTS.md — bullet-time-learning

Instructions for coding agents working with Joy Yang and Sudarshan in this repo.

## Start every session

1. Read [SHARED_CONTEXT.md](SHARED_CONTEXT.md), then identify whose agent you are.
   Prefer the user's statement, then the local account, home path, and Git identity.
   `joyyang` on `/Users/joyyang` identifies Joy here. Sudarshan records his own
   environment when joining. If identity is unclear, ask before writing a devlog.
2. Read your devlog's environment section and latest five entries; skim the other
   person's recent entries. Logs: [Joy](joy-devlog.md), [Sudarshan](sudarshan-devlog.md).
3. Read the full [SPEC.md](SPEC.md) before first substantive work, then the relevant
   sections on later tasks. Check [ownership](division-of-labor.md),
   [interfaces](docs/interfaces.md), and [RUNBOOK.md](RUNBOOK.md).
   Before research implementation, also read the [feasibility audit](reports/cvpr-feasibility-audit-20261028.md)
   for the original findings; the [pilot plan](docs/pilot-plan.md) and revised SPEC
   resolve input/split choices and define current pilot defaults.
4. Inspect Git status, branch, remote, and incoming commits. Preserve other work.
   Register substantial tasks in shared context before editing shared interfaces.

The user's current request determines scope. The research spec describes future
work; reading its build plan does not authorize running the entire study. This
repository starts with a proposal and workflow scaffold, not validated experiments.

## Logs and shared state

- Append consequential changes, decisions, runs, failures, and results as they
  happen to **your own person's devlog only**. Do not invent work, acknowledgment,
  environment validation, or independent review for the other collaborator.
- Keep environment details at the top of your log: host, storage, scheduler,
  software/model pins, validated commands, artifact roots, and access limitations.
  Record no secrets. Empty template maintenance is allowed with explicit provenance;
  it is not work performed by that person.
- Use dated entries with explicit timezones. Shared planning uses America/New_York.
  A run entry includes code/config/input hashes, split, condition/objective/seeds,
  command, job ID if scheduled, output locations, completion state, and next step.
- Re-read shared context before patching it. Update only the affected task/status
  rows and append a concise handoff. Keep historical details in logs/reports.
  Shared context summarizes live state; it does not override the scientific spec.
- User-created task chats can handle scoped work. Do not create new chats, send
  messages, or launch agents merely because the workflow mentions multiple chats.

## Ownership and integration

Joy owns training and integration; Sudarshan owns data and independent analysis.
Follow the exact path map in [division-of-labor.md](division-of-labor.md). Read any
area freely. Coordinate cross-owner implementation changes through a concrete
handoff unless the user's assignment already authorizes them. Ordinary development
against draft fixtures does not require a new bilateral approval gate.

Joy maintains the spec and shared workflow documents. Record scientific changes
with date, reason, authority, affected sections, and downstream impact in
[reports/decisions.md](reports/decisions.md); preserve the original spec in Git.
Contracts remain drafts until the producer and consumer have actually validated
them. Version incompatible changes and record the consumer migration. Never call
one agent's checks an independent collaborator review.

## Scientific invariants

Use SPEC §§4–8 and §§10–12 for details; these guardrails are not a substitute.

1. Render each state-camera cell once; reuse immutable RGB across all conditions.
   A grid is 16 world states × 16 cameras. View, Time, Joint, mixtures and controls
   use every cell exactly once per grid pass. Reject/subset complete shared grids.
2. Mixtures assign each grid to Time 0/1/2/3/4 times in every four-pass cycle. Share
   episode order across paired conditions and balance assignments across families
   and training progress. View randomizes camera phase/direction; Joint covers all
   16 phases, balances both directions, and never wraps world time. Camera loops
   must close smoothly in position, orientation, and motion.
3. Share one augmentation and spatial mask across the full grid and paired arms.
   Keep scheduling, augmentation, masking, and dropout RNG streams separate. Audit
   transformed pixels and actual post-collator visible/target patch indices.
4. Use VideoMAE's own tube mask and raw RGB targets (`normlize_target=False` in
   the referenced implementation), with fixed input normalization. Keep V-JEPA's
   own block masks/predictor and log student/teacher exposure separately. Contextual
   feature targets, hidden activations, and two-frame tubelets are not identical
   across regroupings. Validate controlled recipes against native recipes.
5. Accumulate over complete, identical grid sets; initially eight grids per update.
   Normalize by contributing clips/patches, not unweighted microbatch means. Advance
   optimizer, schedule, and teacher once per complete update. No cross-clip attention
   or batch-dependent normalization; no condition-specific dropped partial batches.
6. Split scene configurations, trajectories/rollouts, related windows, asset groups,
   and counterfactual pairs together. Keep pilot/development and final test separate.
   Use permitted RGB only for pretraining; labels and hidden state are separate and
   inaccessible to its loader. Query points are allowed for the specified readouts.
7. Forecast pairs require identical final-image hashes, valid forward histories,
   and the same explicit continuation rule. The same-image-bag diagnostic requires
   identical full input multisets and side information. A visual sequence model
   must solve it; final-frame and permutation-invariant controls must fail as
   specified. State-oracle correctness alone is not visual solvability.
8. Tracking uses the current-inclusive 16-frame window [t−15,…,t] and a fixed
   pre-occlusion RGB/point reference retained in all three scored windows. Primary
   reacquisition succeeds on all first three visible frames after occlusion, using
   the specified relative distance tolerance and correct visibility. Weight episodes
   equally. Frozen readout access, examples, tuning budgets, and heads match arms.
9. Primary endpoints are collision balanced accuracy, tracking reacquisition success,
   and Something-Something V2 top-1 accuracy at a frozen label budget. Game endpoints
   average within family, then equally across three families. Pair pretraining seeds;
   average three readout seeds within checkpoint, retaining their variation.
10. Thirty primary equivalence contrasts cover five comparisons with View × two
    objectives × three endpoints. Seventy cover the stronger per-family claim.
    Require every component TOST at alpha .05 to pass for the global conjunction;
    component intervals are 90%, not simultaneous 95%. Handle individual/superiority
    multiplicity separately. Provisional margins and five seeds are not a freeze
    or power calculation. Do not add seeds until a desired conclusion appears.
    These contrasts are relative to View; they do not establish all-pairs equivalence
    at the same margin. Evaluation cadence is 16 Hz on 64 Hz physics; SSv2 pilot
    development comes from official training, with official validation reserved
    for the final evaluation. Verify these choices in the actual implementations.
11. Freeze protocol, splits, margins, readout budget, sample size/stopping rule, and
    analysis before final-test inspection. Keep test inaccessible to tuning code.
    Preserve paired episode/video groups in uncertainty estimates and report family
    effects, coverage, failed arms, exclusions, and resource costs.
12. A tie is not equivalence. Strong null claims also require sensitive visual tests,
    useful learning and transfer, gains from coherent over disrupted grouping, and
    precision/scale evidence. A generic renderer is not by itself gameplay. Refresh
    closest-work evidence before substantial training; setup does not certify novelty.

Flag and resolve conflicts with these invariants before treating affected outputs
as protocol-compliant evidence. Keep proposed, implemented, measured, and frozen
states distinct.

## Engineering and publication

- Follow the small components in SPEC §12. Pin game/renderer, asset provenance,
  model/objective code, dependencies, device, precision, and configs when implemented.
  Checksums identify actual bytes, not just filenames. Synthetic fixtures are labeled.
- Compute host, storage, credentials, and runtime are unselected here. Validate
  project-specific resources before experiments. Do not import previous Athena/ADA
  policies, job wrappers, pins, quotas, results, or dates. Resource estimates in the
  spec are planning arithmetic, not measured benchmarks.
- Keep large/raw/restricted artifacts out of Git; version small public contracts,
  permitted manifests, configs, and reports. No deletion of another person's outputs
  or cancellation of jobs this task did not submit.
- Run appropriate checks and record their limits. `python3 scripts/check_scaffold.py`
  checks this scaffold only. `python3 scripts/check_pilot_plan.py` checks planning
  consistency/counts, not experiments. Add component/integration tests as code is built.
- Commit cohesive work as you go. Publish integrated `main` with normal pushes,
  preserving incoming commits. Do not force-push or publish temporary branches.
  Follow the concurrent-work procedure in the runbook.
- Setup does not authorize paid compute, full experimental execution, submission,
  scheduled automation, or messages to collaborators. Keep message drafts in chat.
