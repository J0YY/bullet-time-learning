# Runbook — bullet-time-learning

**Current capability:** documentation/workflow scaffold and its checker. Renderer,
training, readouts, statistics, compute access, and scientific audits are future
work. The [spec](SPEC.md), [ownership map](division-of-labor.md), and
[interfaces](docs/interfaces.md) govern those tasks.

## Start or join

For a new checkout:

```bash
git clone https://github.com/J0YY/bullet-time-learning.git
cd bullet-time-learning
```

Read AGENTS and shared context, identify whose agent you are, read your environment
and latest log entries, then skim the other log and check task ownership. Sudarshan
fills in his own environment and verifies GitHub invitation acceptance when joining.
Each machine uses that person's Git author identity and credentials.

```bash
git status --short --branch
git remote -v
git fetch origin
git log --oneline --decorate -8
git log --oneline HEAD..origin/main
```

If the working tree is clean and local `main` has no unique commits, integrate with
`git merge --ff-only origin/main`. Preserve dirty/concurrent work; do not reset,
clean, auto-stash someone else's files, or overwrite the other devlog.

## Claim a task and implement

Use the first tasks in the ownership map. Re-read shared context, add a registry
row with task ID, person, scope, base commit, dependencies and status. Keep changes
within the assigned paths. Name any proposed cross-owner change in a handoff.

Develop against draft fixtures without waiting for personal acknowledgment. Record
producer and consumer checks honestly. A mock grid or passing combinatorics check
is not rendered-data acceptance. A rendered grid is not an audited model update.
Select and validate compute resources before research jobs; no host is inherited.

## Check and commit as you go

```bash
python3 scripts/check_scaffold.py
python3 scripts/check_pilot_plan.py --self-test --check-report
python3 scripts/audit_spec.py
git diff --check
git diff --stat
```

The scaffold checker runs locally and in CI with Python standard library + Git.
As implementation arrives, run its relevant component and integration tests too.
Record exact checks and their limits in your devlog and the appropriate report.
Before committing, review the diff for secrets, large/raw assets, labels, accidental
foreign-project settings, or invented results.

Stage explicit owned paths (replace the example with actual changed paths):

```bash
git add path/to/owned-file.md
git diff --cached --check
git diff --cached
git commit -m "Describe the concrete change"
```

Use cohesive incremental commits with consequential devlog updates. Commit an
implemented feature with its meaningful tests and handoff evidence where applicable.

## Integrate and publish main

Only publish integrated `main` using normal pushes. Before pushing, require a clean
working tree and re-check incoming commits:

```bash
git fetch origin
git rev-list --left-right --count HEAD...origin/main
```

If behind only, fast-forward. If both sides have unique commits, inspect them and
use `git merge origin/main` to preserve both histories; resolve conflicts with the
current spec/ownership and both logs intact. Re-run affected checks after merging.
Do not rebase published work or force-push. If a push races with the other person,
fetch, integrate, validate, and retry normally.

```bash
git push origin main
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
```

The two commit hashes should match and the working tree should be clean. Check the
GitHub Actions result for that exact commit. During first publication to an empty
repo, `origin/main` does not exist until the first `git push -u origin main`.
Never assume uncommitted local files are visible to the other collaborator.

## Handoff between people or chats

Update your log and the relevant shared-context row with:

```text
Task / person / source commit:
Implemented or changed paths:
Input/output contract versions and artifact hashes:
Commands and observed results:
Evidence level: synthetic | rendered | real-loader | model | final protocol
Limitations, failures, and open dependencies:
Next owner and concrete acceptance check:
Publication: local only | pushed commit; remote validation status:
```

Re-read live shared context immediately before patching; keep updates narrow and
preserve other tasks. Full history belongs in devlogs/reports. User-created task
chats receive scoped objectives and deliverables; this workflow does not itself
authorize creating or messaging chats or contacting collaborators.

## Research execution when implemented

Record each person's actual environment in their devlog. Joy coordinates the resource ledger; each owner validates access and submits
their own authorized work without a per-job handoff through Joy. Choose storage paths, dependency/code
pins, scheduler access and runtime only after project-specific validation. Put
outputs outside Git and keep hidden-state/test artifacts outside loader/tuning
permissions. Log source/config/input hashes, allocation/job IDs, commands, output
paths, throughput, memory, GPU counts and failure states for every run.

Follow [pilot v1](docs/pilot-plan.md). Deliver 1 → 8 → 100 → 1,000 grids. Integrate
one actual update at eight grids, without waiting for the full corpus. Joy builds
consumer fixtures; Sudarshan builds producer and analysis fixtures independently
against [working v1 interfaces](docs/interfaces.md). Send an immutable drop with
hashes and one reproduce command as soon as it passes its producer checks.

After the 100-grid audit, frozen 1,000-grid pretraining bundle and resource
validation, the first three controlled slots
can run to four passes while measurement diagnostics proceed. Require visual
solvability and early stability before expanding to eighteen twenty-pass runs.
The first three resume under their original twenty-pass schedule if hashes match.
The pilot ledger separately includes native/image references, seven supervised
fits and 360 frozen-head fits; no automatic V-JEPA or eighty-pass extension.

Freeze the main protocol only after learning, transfer, measurement, resource and
power evidence. Record frozen hashes/margins/endpoints/stopping rule before test
access. The full two-objective matrix is 16n runs (80 at n=5), excluding supporting
work. Neither that arithmetic nor this setup authorizes a full launch.

## Current automated checks

[scripts/check_scaffold.py](scripts/check_scaffold.py) verifies required files,
relative Markdown file targets outside fenced code, CLAUDE's AGENTS import, original
spec bytes in Git, current spec drift provenance, and artifact ignore behavior.
It uses no model/network calls. [.github/workflows/scaffold.yml](.github/workflows/scaffold.yml)
runs it and whitespace checks on pushes to main and pull requests. This is repository
maintenance CI, not a renderer, GPU, statistical, or independent scientific review.

[scripts/audit_spec.py](scripts/audit_spec.py) additionally enumerates proposed grid
partitions and calculates workload/contrast counts. CI runs its standard-library
mode. Optional `--power` requires locally available SciPy and reproduces the
Gaussian TOST planning examples; it is not a measured project power estimate.
See the [feasibility audit](reports/cvpr-feasibility-audit-20261028.md) before
resolving research input/partition choices or expanding the study.

[scripts/check_pilot_plan.py](scripts/check_pilot_plan.py) checks the declarative
pilot manifest, pair-preserving label budgets, checkpoint/update arithmetic,
forecast steps, included early slots and supporting/readout counts. Its JSON output
binds source hashes; malformed-plan rejection checks are CPU-only. Neither it nor
CI implements the future producer/consumer fixture tests in the interface contract.

After an intentional, reviewed pilot-plan/contract change, regenerate its bound
report with `python3 scripts/check_pilot_plan.py --self-test > reports/pilot-plan-audit.json`,
then run `python3 scripts/check_pilot_plan.py --self-test --check-report`. CI rejects
stale source hashes/accounting. Changing SPEC also requires its new hash and reason
in the decision record; original source provenance remains immutable.
