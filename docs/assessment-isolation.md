# Assessment access foundation

No real assessment set or score has been released. This increment implements
private label commitments and a **local macOS trusted-job boundary**. Complete
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
or scientific gates. Future assessment generation must also keep its reconstruction
seed/requests private and use opaque, label-independent IDs; sealing cannot hide a
label already encoded in a branch ID or reconstructible from a public seed. Current
train/dev branch IDs are not an assessment identifier scheme. Retain the sealed output bytes; rerunning the sealer creates
different commitments and must be treated as a different artifact.

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
