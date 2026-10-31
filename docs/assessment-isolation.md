# Assessment access foundation

No real assessment set or score has been released. Implemented components include
opaque input exports, private label commitments and a **local macOS trusted-job boundary**. Complete
data admission, the locked pilot protocol, stage inventory and release procedure
remain required before using assessment. Direct operational scoring still rejects
assessment before opening labels. Existing predictor eligibility is a necessary
checkpoint check, not authorization to release an assessment set.

## Private labels and public commitments

A binary label's unsalted SHA-256 is guessable from its two possibilities. Label
v2 therefore adds a private 256-bit `commitment_nonce` per record, sampled through
Python `secrets`, independently of public dataset seeds. Public inventory rows carry
the SHA-256 of the canonical **entire** label record. Nonces and targets remain in
private labels. Do not publish old unsalted label hashes alongside the commitment.

```sh
.venv/bin/python scripts/data/seal_assessment.py \
  --private-labels PRIVATE/unsealed-assessment.jsonl --output NEW-SEALED-DROP
```

This producer-only conversion accepts private unsealed v1 assessment records,
validates the actual targets and unique keys, and creates a new directory. It emits
`private/labels.jsonl`, `public/target-commitments.json` and a public sealing receipt
binding actual bytes/code. Private directories/files use modes 700/600. These modes
do not deny access to another process owned by the same local account.

Training/development remain v1; readers reject v1 assessment records and accept
v2 only for assessment. The inference format stays unchanged: combine each public
target commitment with its separately validated family/group and actual predictor
identity to prepare the expected-key inventory. A nonce is never a model feature.
The sealer does not check physical validity, split lineage, full expected coverage
or scientific gates. Assessment generation must keep its reconstruction seed/requests private and use
opaque, label-independent IDs; sealing alone cannot hide a label encoded in a
branch ID or reconstructible from a public seed. The producer-only preparation
command below implements identifier removal. Current train/dev branch IDs are
not an assessment identifier scheme. Retain the sealed output bytes; rerunning the sealer creates
different commitments and must be treated as a different artifact.

## Opaque assessment preparation

```sh
.venv/bin/python scripts/data/prepare_assessment.py \
  --private-source PRIVATE-ASSESSMENT-SOURCE --output NEW-PREPARED-DROP
.venv/bin/python scripts/data/prepare_assessment.py \
  --output NEW-PREPARED-DROP --verify-only
```

The private source must already contain assessment-only game inputs in
`inputs/evaluation.jsonl`, an RGB catalog in `inputs/images.jsonl`, unsealed v1
labels in `private/labels.jsonl`, and complete `groups.json`. This command refuses
train/dev inputs; it does not convert an existing development set into assessment.
Real source generation still needs private randomness, physical/lineage and full
pixel admission. No such source has yet been admitted.

Preparation samples independent 256-bit names for episodes, queries, groups and
images; records are sorted by the new IDs so original branch order is absent.
Queries shared by counterparts stay shared, image reuse and temporal order stay
exact, and tracking keeps its fixed reference. Only RGBs referenced by permitted
inputs are copied. Lossless PNG re-encoding strips text/source metadata while
preserving decoded RGB bytes. Private labels receive randomized commitments after
renaming. Complete pair/target joins and actual RGB hashes are checked through the
existing consumer, including opposite primary labels and same-image-bag equality.

`public/` contains only the opaque input/catalog/group records, used PNGs, target
commitments and `preparation.json`. `private/` retains labels, original-to-opaque
maps and source digests, with a separate inventory. A complete receipt is written
only after validation. Keep rejected partial outputs intact and never mount them
for inference. The verifier checks both inventories and revalidates actual inputs,
pairs and commitments. A new preparation has different IDs/nonces and is a new
artifact, even with identical private source data.

The new receipt schema is `bullet-time.opaque-assessment-preparation.v1`; input,
label and group wire formats remain v2/v2/v1. Its release and scientific-gate flags
are always false. Preparation is not full data admission, protocol locking,
permission isolation, human blinding, or authorization to fit/predict/score.
Deny the original source, prepared private directory and any copies to inference;
fitting must exclude the entire prepared assessment. The staged H3/H4 release
policy still needs a locked implementation before real use.

## Restricted local jobs

```sh
.venv/bin/python scripts/isolated_job.py \
  --deny-root /absolute/assessment/private \
  --probe-file /absolute/assessment/private/labels.jsonl \
  --output /absolute/NEW-job-receipt --cwd /absolute/project \
  --timeout-seconds 60 -- /absolute/project/.venv/bin/python YOUR-COMMAND-ARGS
```

Repeat `--deny-root` and `--probe-file` in matching order for each private boundary.
Fitting must exclude the entire assessment set; authorized inference would exclude
all labels, raw states/masks/requests, the unsealed source, private copies and
previous assessment scores while retaining only permitted inputs. Include every
such location. A boundary around one convenient copy is insufficient.

The launcher canonicalizes paths, requires an existing file inside each private
root, and verifies that the sandboxed interpreter cannot open those files. It
then launches the command with the same profile, no inherited stdin, a minimal
environment and denied network access. A native job inherits the boundary in its
children. Logs and a receipt bind the argv, cwd, profile, launcher/backend bytes,
OS, denial probes, timeout, return status and elapsed time. Failed probes prevent
execution. Timeouts terminate the launched process group and remain failures.
Do not pass secrets on argv or write them to command output.

This backend uses the locally available, deprecated `sandbox-exec`; availability
alone is never acceptance. Native tests must pass on the exact execution host.
Linux and missing backends fail closed, with no unconfined fallback. A future CUDA
host needs its own verified read-only input mounts and absent private mounts.
The child has ordinary read access outside explicitly denied roots and is trusted
project code. This is not a general malicious-code sandbox: it does not inventory
pre-existing copies/hardlinks, control another human process or prove human blinding.

## Checks and migration

```sh
.venv/bin/python -m pytest tests/readouts/test_assessment_privacy.py -q
```

Checks cover randomized commitments, actual target/input joins, rejection of old
assessment labels, unchanged train/dev behavior, continued scoring refusal, private
CLI exports, path validation, unsupported-host refusal, native child/symlink denial,
private-link/rename denial and timeout cleanup. Native checks skip on Linux CI;
that skip is not evidence that Linux isolation works.

Shared label validation changes the consumer code identity. Preserve the original
code snapshot when using old fitted checkpoints; new inference cannot silently
reuse a checkpoint fitted under another consumer hash. Historical integration
reports remain valid for their recorded code. No assessment freeze or release is
inferred from any of these engineering checks.

The [October 30 native report](../reports/data/assessment-privacy-20261030.json)
records the actual consumer assembling all three task types while private train/dev
labels were denied. Separate cumulative code review was clean in round 2 after
adding the shared validator to scoring provenance; 106 full-suite tests and 37
focused post-fix tests passed locally. No assessment or independent collaborator
review is claimed.

The opaque export has synthetic tests in `tests/readouts/test_assessment_export.py`
for all three tasks, exact assembled tensors in every allowed mode, private PNG
metadata, randomized IDs/order, complete pairs, malformed inputs, CLI verification
and artifact mutation. These tests create synthetic assessment fixtures only.

## Staged persistence component

Joy selected [two locked stages on the existing pool](assessment-release-proposal.md).
`evaluation/assessment_policy.py` derives the exact 7 H3 / 243 H4 / 117 development-
only head inventories and checks the numerical H3 rules against complete matched
400-episode task pools. `evaluation/assessment_state.py` provides the persistent
version/stage journal; its tests use synthetic commitments only.

The whole-version payload commits protocol, pipeline, source/runtime, admission,
early resume points and every slot's recipe/input inventory. H3 predictor hashes
are required immediately; H4 hashes may append once to their fixed slots. A shared
registry reserves each pool for one version. Stage release commits every delivered
or failed slot before scoring. File locking serializes concurrent operators;
fsynced reservations survive interrupted creation/report publication. Identical
retries return the same state/receipt; changing predictions, recipes, reports or
outcomes fails. Failed/incomplete H3 closes the version; H4 requires H3 completion
and closes it after its own receipt.

This journal validates commitments and state transitions, **not their scientific
contents or underlying artifact bytes**. It never opens labels or runs a scorer,
and every status retains `assessment_authorized=false` and `scientific_gate_pass=false`.
The upcoming admission/scoring adapter must verify actual data and fit contracts,
immutable expected/prediction bytes, complete coverage, quantitative H3 and actual
job-isolation receipts, then supply these commitments/outcomes. Keeping one registry
and a verified pool identity is part of that admission contract; the journal is
not a malicious-user or human-blinding boundary. Direct scoring remains train/dev
only. No real pilot lock, release or inspection is recorded by these tests.

## Fixed recipes and later predictor bytes

`evaluation/assessment_contract.py` builds the fixed recipe from full fit config,
training/development inputs and label/subset identities, consumer admission,
backbone/source/initialization, pass position, and fit/inference runtime. A learned
backbone's future checkpoint hash and fitted outcomes may be absent at planning;
existing reference checkpoint hashes remain fixed. Actual predictor/fit/readout
hashes append as a separate binding. The journal requires H3 predictor bindings
already at the whole-version lock.

A label-free expected-input commitment covers task/query/group/target-reference
identities independently of future predictor IDs and readout seeds/budgets. It is
additional to the recipe's actual input/catalog hashes. Delivered expected keys
must match the declared task, seed, budget and horizon. The verifier checks actual
fit/export joins, eligibility, source consistency, coverage and all artifact bytes
before/after; it never opens labels. Historical real dev exports can exercise this
component without claiming new fits or assessment.

This validates fit/export metadata, not the checkpoint's actual execution or the
scientific/admission claims behind it. The staged adapter still must validate
complete admitted pools, actual checkpoint/job receipts and isolation before
scoring. Status flags remain false. Assessment-only policy, journal and metadata
verification files are excluded from the model's code identity because the model
consumer does not import them; the verifier separately binds its own code and
scoring dependencies. This one-time identity-rule change itself changes the
consumer fingerprint. Preserve old fitted snapshots on their pinned revision.

### Public expected-input compilation

`evaluation/assessment_inputs.py` compiles primary game-task templates from the
opaque public export without opening private labels, source maps or reconstruction
files. It checks actual PNG bytes/decoded RGB, exact permitted-file and image
inventories, opaque identifiers, complete groups, all target commitments (including
auxiliary classification horizons), and three consecutive primary tracking queries.
Half-second classification templates cover every declared episode. Both source bytes
and compiler identity are checked again before returning.

```bash
.venv/bin/python scripts/scoring/assessment_inputs.py \
  --public /absolute/prepared/public \
  --output /absolute/assessment-input-inventory.json
```

The default requires 400 episodes per task; `--allow-partial` is for diagnostic
fixtures only. Output must be new and outside the immutable public directory.
A complete count flag does not establish source-pool freshness, physical/lineage
validity, correct private labels, checkpoint execution or release authorization.
All outputs keep authorization/scientific passage false. Source admission must
verify the declared projectile-arena family. No actual assessment pool is admitted
by these synthetic tests; staged scorer/job integration remains pending.

### Bind a job to declared artifact bytes

`scripts/bound_job.py` wraps the verified local boundary with a prelaunch request
and a completed/failed evidence record. Supply a JSON object mapping canonical
absolute input-file paths to their actual SHA-256 values. Include every relevant
script/source/dependency/config/model/data file; the wrapper cannot infer those
from arbitrary commands. It adds the actual executable automatically. Declare
all expected output filenames relative to a new artifact directory.

```bash
.venv/bin/python scripts/bound_job.py run \
  --inputs /absolute/input-hashes.json \
  --artifact-output /absolute/new-predictions \
  --expected-output run.json --expected-output coverage.json \
  --expected-output predictions.csv \
  --deny-root /absolute/prepared/private \
  --probe-file /absolute/prepared/private/labels.jsonl \
  --output /absolute/new-job-evidence --cwd /absolute/project \
  --timeout-seconds 600 -- /absolute/python /absolute/predict-command.py
```

The command shown is a structural example; the real consumer adapter must provide
its fixed complete command and every required denied root, including reconstruction
copies/prior scores. Fitting also denies public assessment inputs. A single private
root does not prove those broader boundaries. The wrapper rechecks declared input
bytes and code after execution, rejects extra/missing/linked outputs, and records
actual output hashes. An exclusive sibling reservation prevents concurrent jobs claiming the same artifact
destination. Existing artifact/receipt folders and reserved destinations cannot be
reused. Keep the reservation with its artifacts. Preserve
failed directories and receipts. The CLI prints request and evidence identities;
retain both outside the mutable job folder for subsequent verification:

```bash
.venv/bin/python scripts/bound_job.py verify \
  --output /absolute/new-job-evidence \
  --request-sha256 REQUEST_SHA256 --evidence-sha256 EVIDENCE_SHA256
```

Verification checks the actual input/output bytes and command/boundary/probe/log
bindings against those pinned identities. This is a trusted-command evidence
component, not a hostile-code sandbox, complete model/data admission, release
permission or scientific gate. Linux/CUDA still requires a validated boundary.

### Private prospective assessment source selection

`scripts/data/plan_assessment.py` selects 200 collision pairs, 200 order pairs and
400 tracking episodes before rendering. All three tasks use the existing generator
and globally assigned assessment content pools. The master data seed stays 20261028;
a fresh private 256-bit nonce derives a reproducible candidate stream, kept only in
the private selection directory. Opaque public export remains a later step.

Supply a private JSON list of existing receipt objects, each with `path` (absolute
path to the train/dev `bundle.json` or a prior assessment `selection.json`) and
`sha256` (its actual file hash). Include the accepted development bundle and every
prior assessment selection in this pilot lineage. Dependencies of listed prior
selections cannot be omitted. The eventual release adapter must also compare this
list with the whole version registry; this selector alone cannot discover omitted
unlisted versions.

```bash
.venv/bin/python scripts/data/plan_assessment.py \
  --known-sources /absolute/private/known-sources.json \
  --output /absolute/private/new-assessment-selection
.venv/bin/python scripts/data/plan_assessment.py \
  --verify-only --output /absolute/private/new-assessment-selection
```

The selector reconstructs actual known requests, reserves trajectory/appearance/
configuration prototypes across tasks and prior pools, and applies the existing
tracking-background proximity exclusion. It retains complete groups and exact
pilot counts. Keep the entire output private: it contains states, branch outcomes,
original identifiers and reconstruction randomness. The CLI prints only counts and
receipt identity. Verification rejects byte/source/count drift or exposed file modes.
This is a prospective source plan, not rendering, visual sensitivity, cross-pool RGB
or common pretraining lineage admission. Neither command opens a scoring release.
