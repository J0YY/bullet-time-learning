# Joy's devlog — bullet-time-learning

Read [AGENTS.md](AGENTS.md). Append consequential work under **Log**, newest at
the bottom. Record only Joy's work and observations; preserve failures and limits.

## Project environment

| Item | Verified state / open choice |
| --- | --- |
| Identity | Joy Yang; local account `joyyang`, observed 2026-10-28 |
| Local checkout | `/Users/joyyang/Projects/bullet-time-learning` |
| Repository | `https://github.com/J0YY/bullet-time-learning.git`; public; Joy has admin access |
| Git author | Existing Joy Yang configuration retained |
| Local checks | Python 3.14.3, Git, and authenticated GitHub CLI available |
| Compute host / scheduler | Not selected or validated for this project |
| Remote work root / storage / quota | Not configured |
| Godot / renderer / GPU runtime | Not installed or validated by this setup |
| Model / dependency revisions | Not selected; pin during implementation and native-recipe validation |
| Data / caches / checkpoints | No research artifacts created |
| Launch / monitoring commands | None validated; add exact commands and job IDs after actual use |
| Collaborator access | Check current GitHub access before relying on shared push; see setup audit |

## Log

### 2026-10-28 15:18 EDT — Read specification and initialize repository

- **What:** Read all 12 sections of the supplied bullet-time specification and
  inspected the previous project's ownership, devlogs, shared context, contracts,
  and Git workflow. User requested the same collaboration structure for this
  unrelated project and incremental commits with verification.
- **Observed:** Local folder initially contained only the supplied specification;
  GitHub repository was empty. Joy's existing Git identity and admin access verified.
- **Command:** `git init -b main`; configure supplied HTTPS origin; rename source
  document to `SPEC.md` without changing its bytes.
- **Source:** `Bullet-Time Learning in Video Games Research Specification.md`,
  SHA-256 `e543446ddf6466e07cbf545a402092ebe2f5d6a6a43465472bd41c4e693fb9de`.
- **Decision:** Carry over collaboration conventions only. No previous research,
  compute-host mandate, deadline, approvals, runtime pins, or results adopted.
- **Next:** Complete ownership, handoff contracts, startup/runbook, and setup checks.

### 2026-10-28 EDT — Complete collaboration documents

- **What:** Added agent startup/identity rules, working ownership and first tasks,
  draft data/exposure/run/analysis contracts, shared context, runbook, decision log,
  and a setup risk review. Created an empty attributed template for Sudarshan.
- **Code:** Initial source import committed as `13e951d`; workflow documents form
  the next cohesive commit.
- **Checks:** Read against SPEC §§4–8 and §§10–12; staged whitespace check passed.
  All implementations and contract validations remain explicitly pending.
- **Access observed:** GitHub already has a pending write invitation for
  `deephelms28`, the write collaborator on the reference repository. No invitation
  was sent or changed; acceptance and Sudarshan's own environment are not assumed.
- **Next:** Add automated scaffold checks and CI; audit all files and publish main.

### 2026-10-28 EDT — Add scaffold validation and CI

- **What:** Added standard-library structure/link/provenance/ignore checker, source
  provenance JSON, setup report and read-only GitHub Actions workflow with pinned
  action revisions. The checker's scope is explicitly repository maintenance.
- **Command:** `python3 scripts/check_scaffold.py`; `git diff --check`; complete
  committed-tree whitespace check against the empty Git tree.
- **Result:** Passed: 18 required files, 13 Markdown files, 49 local links and 32
  ignore-rule cases. Original and current SPEC bytes match the source hash.
- **Review:** Self-review against the specification and ownership map; no independent
  reviewer or experimental validation claimed.
- **Next:** Verify rejection paths and a fresh clone, publish main, inspect exact
  remote commit/tree and CI outcome, and finish the handoff record.

### 2026-10-28 EDT — Verify clone, rejection behavior, and GitHub publication

- **What:** Published the first three commits to `main`. Verified fresh local and
  GitHub clones, all tracked bytes, source identity, negative checks, and hosted CI.
- **Code:** `7bfeb7316b1cad8380f64bcdb4eb46ef74e253e7`; import `13e951d`,
  workflow `8d2b61d`. All 18 remote file bytes and tree/HEAD matched local.
- **Result:** Checker passes from both clones and from outside the repository.
  Five temporary-clone regressions rejected; restored clone passes. GitHub run
  `40754638085` completed successfully on Linux/Python 3.12.
- **Audit attempts:** First ignore-regression fixture was ineffective because Git
  retains an ignored parent; removed the rule instead and verified rejection.
  First remote byte comparison included an empty trailing NUL field and raised
  IsADirectoryError; filtered empty fields and reran successfully. No project file
  corruption or experimental impact; details in the setup audit.
- **Handoff:** SETUP complete; J1 and S1 ready for the respective collaborators.
  Research implementation/compute and Sudarshan's invitation acceptance remain
  unverified. Final evidence/status documentation will be committed and its exact
  remote/CI state checked before responding to the user.

### 2026-10-28 EDT — Audit original specification and CVPR feasibility

- **Authority:** User requested a full double-check of setup and original spec for
  CVPR feasibility/idea quality; existing incremental commit/publication instruction
  remains in effect. Registered AUDIT against `d9ec3a8`; fetched with zero divergence.
- **Work:** Re-read all scaffold files and SPEC; checked primary papers, official
  conference/dataset pages, VideoMAE target code and renderer documentation. Found
  missing BulletTime/FL4N comparisons, reference-relative claim wording, SSv2
  partition/access and evaluation timing/input gaps. Report separates new findings
  from already acknowledged learning/transfer/power risks.
- **Commands:** `python3 scripts/check_scaffold.py`; `python3 scripts/audit_spec.py
  --power > reports/spec-math-audit.json`. Local Python 3.14.3 / SciPy 1.17.1 were
  already available; no install or research compute.
- **Result:** 163 partition checks and 16 four-pass assignments passed; storage,
  run/compute counts and approximate single-contrast power examples verified.
  This is mathematical checking, not rendered-data or model evidence.
- **Source-access limits:** 2027 reviewer-guideline URL inaccessible; use official
  2027 CFP/dates and label 2026 guidance as precedent. Publisher TOST URL timed out;
  checked the same primary article via PMC. Search is bounded, not proof of novelty.
- **Artifacts:** Feasibility report, numerical JSON and audit script; source/contract
  clarifications and review pointers in shared docs. Original SPEC unchanged;
  Sudarshan's log untouched. No independent reviewer acknowledgment claimed.
- **Recommendation:** bounded pilot, with sensitive measurements/useful frozen
  learning and transfer before expansion; full unbuilt study not a credible
  imminent CVPR 2027 commitment. No protocol/venue/compute choice adopted.
- **Next:** Validate final changes, commit/publish and check fresh checkout and CI.

### 2026-10-28 EDT — Verify and publish feasibility audit

- **Code:** Substantive audit committed and published as `af32b16b6f696d961707b819f24a0ecc375ab394`.
- **Checks:** Fresh clone passes scaffold and mathematical checks; stored JSON is
  bound to unchanged SPEC/script hashes. Original SPEC and Sudarshan's log are
  byte-identical to their pre-audit versions. 14 Markdown files, 60 local links,
  32 ignore cases, Python parsing, whitespace and tracked-file checks pass.
- **Math cross-check:** Independent calculation via direct Gaussian Monte Carlo
  (200,000 samples per SD, RNG seed 20261028) agrees with quadrature within 0.004
  for all three five-seed planning cases. This is not measured project power.
- **Publication:** GitHub CI `40758307456` passed on the substantive audit commit.
  Shared AUDIT task marked complete; final completion-record commit will receive
  exact remote/CI verification before handoff. No experimental job or new protocol.

### 2026-10-28 EDT — Revise scientific specification and bound the pilot

- **Authority:** User requests audit fixes, concrete pilot, minimal mutual blockers,
  original retained in Git, incremental commits and checks. Base `6fbfec4` clean and
  synchronized; registered REVISION before editing.
- **Changes:** Revised SPEC title/closest work, fixed forecast/tracking/spatial input
  details, deterministic external split/access, View-relative claims and deadline
  scope. Added concrete pilot plan and declarative count/seed manifest, prospective
  operational gates and full supporting-run/head accounting. Updated live pointers.
- **Evidence:** Existing primary-source audit plus official DINOv2 release checked;
  no data access, model download, training job, new chat or collaborator message.
- **Provenance:** Original remains at `13e951d:SPEC.md`; revision SHA recorded in
  decisions. Sudarshan's log remains untouched. Gates are planning choices, not
  measurements or independent review. Next: align contracts/ownership and verify.

### 2026-10-28 EDT — Decouple workstreams and check pilot accounting

- **First commit:** `9adffbc` preserves the original import while revising current
  SPEC and adding the bounded plan/count manifest. No original history rewritten.
- **Changes:** Versioned unimplemented contracts to working v1 with concrete wire
  formats; no shared Python import prerequisite. Assigned owned fixture/test/CI
  areas, progressive grid drops, early overlap and independent authorized job
  submission. Updated registry, instructions, runbook and review history.
- **Checks added:** Standard-library pilot consistency/forecast/group/update/head
  accounting, twelve malformed-plan rejection cases, source-hash-bound report and
  CI freshness check. It verifies planning only, not future component fixtures.
- **Observed arithmetic:** 18 controlled runs include the three early slots;
  5,760,000 clips, 45,000 updates, 38.535168 GB raw pretraining RGB, 360 frozen-head
  fits plus explicitly separate native/image/supervised work. No run was launched.
- **Next:** Full document/semantic review, source provenance and fresh-checkout
  verification, incremental commit/push, exact-head remote/CI confirmation.

### 2026-10-28 EDT — Verify revised spec, pilot and parallel handoff

- **Commits:** `9adffbc` scientific revision/plan; `7e5a6e1` decoupled workflow,
  concrete interfaces and planning checks, both published normally to main.
- **Verification:** Local and fresh local/remote clones pass scaffold, all 163 grid
  partition checks and pilot accounting/freshness checks. Twelve malformed-plan
  cases are rejected. Python parsing and whole-tree whitespace checks pass;
  mathematical audit including optional SciPy TOST calculations reproduces.
- **Provenance:** Original import SHA/62,247 bytes verified in Git. Current SPEC
  hash matches decisions and audits. Sudarshan's devlog is byte-identical to base.
  All 25 tracked files matched the remote clone; it was clean after checks.
- **CI:** `40765480976` succeeded on exact commit
  `7e5a6e152b72dc6a6eaec043f211ebefa713faec`. Final completion-record commit is
  verified/published and its own CI checked before the user handoff.
- **Final review clarification:** Pilot gates require complete applicable slots
  and prediction coverage; missing failures cannot be silently excluded. One-family
  pilot reports arena scores directly, not a fictitious three-family mean.
- **Result / next owner:** REVISION complete. Joy starts J1/J3 on consumer fixtures;
  Sudarshan starts S1/S4 on producer/analysis fixtures independently. First real
  update waits only for eight grids; actual pilot screen needs frozen 1,000 grids.
  No rendered-data, training, empirical feasibility, final freeze, collaborator
  acknowledgment or submission commitment is claimed. No research jobs launched.

### 2026-10-28 EDT — Begin Joy implementation against fixed pilot contracts

- **Authority / baseline:** Active user goal requests implementing Joy's part,
  rigorous research/implementation checks, and continuing until Sudarshan blocks
  remaining work. Clean synchronized baseline `c10b678`; J1 marked in progress.
- **Runtime:** Isolated `.venv` with Python 3.11, torch 2.9.1, torchvision 0.24.1,
  timm 1.0.22, NumPy 2.3.5, Pillow 12.0.0 and pytest 8.4.2. CPU tests are local
  implementation validation, not research training or a compute allocation.
- **Implementation:** Allowlisted immutable RGB consumer with byte/hash/path checks;
  eight deterministic schedules, four-pass family/prefix balance and retained tail;
  shared grid transforms/tube masks, raw/native targets and source-image-coordinate
  audit derived from actual collator tensors. Separate consumer fixtures.
- **Source:** Released VideoMAE commit `14ef8d856287c94ef1f985fe30f958eb4ec2c55d`
  vendored with attribution/noncommercial license and explicit import/registration/
  whitespace changes. Model wrapper and empirical native comparison still pending.
- **Checks:** Six loading/partition/target tests passed, including malformed data,
  symlink escape, actual target corruption, all eight arm comparisons and balanced
  mixture prefixes. No game data, research result or independent review claimed.
- **Next:** Complete-grid runner/resume, executable model configs, readout/input/
  export paths, then cumulative independent review under the review-loop skill.

### 2026-10-28 EDT — Implement model updates, resume and readout boundaries

- **Work:** Released small VideoMAE wrapper; controlled/native crop-mask-target
  paths, framewise image-MAE reference, weighted complete-grid/tail updates, CPU/
  CUDA deterministic settings, hash-bound checkpoints and strict resume. Added
  evaluation v2 input/reference access, frozen attention heads, seven diagnostic
  modes, train/dev-only fitting, explicit prediction coverage, SSv2 deterministic
  split/frame adapters, pilot inventory/resource extrapolation and executable CLI.
- **Research checks:** Native targets remain deliberately contextual across paired
  frames; controlled target audit compares actual per-source-image components.
  Bag controls encode images independently before mean pooling; final-frame controls
  enforce access at assembler and model. Tracking auxiliary occluded targets avoid
  all-positive visibility training; primary scoring remains three reappearances.
- **Validation:** 21 tests passed (20.85 s), including full 224 small-model forward,
  gradient/microbatch invariance, retained tail, exact dropout resume, changed-input
  rejection, framewise exposure, frozen-state preservation, withheld-split rejection,
  incomplete prediction coverage, SSv2 partition isolation and an 8-grid CLI update/
  checkpoint/resume. An initial hidden-temp-filename torch.save failure was fixed
  using a file handle and verified by the resume tests.
- **Limits / next:** No real renderer or pilot experiment. Finish strict label-
  budget/horizon selection, external model/decoder path, CLI readout integration,
  handoff/CI and cumulative independent review before declaring Joy unblocked work
  exhausted. Data/runtime receipts bind evidence but are not scientific proof by
  themselves; source reports need actual H1–H4 validation.
