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
