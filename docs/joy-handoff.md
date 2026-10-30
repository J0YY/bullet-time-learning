# Joy end-to-end pilot operator guide

Joy's consumer, schedules, actual-update audit, training/resume, reference models,
readout/diagnostic fitting, video decoder and prediction export are implemented.
They have synthetic tests; they have **not** established game fidelity, visual
solvability, useful representation learning, transfer or CVPR readiness. Keep the
original SPEC at `13e951d:SPEC.md`; the current scientific scope remains the bounded
[pilot](pilot-plan.md), with the October 30 [ownership](../division-of-labor.md) reassignment.

## Work in parallel

Joy owns all required pilot code/data and operational analysis. Sudarshan's
separate verifier can start on its own fixtures and later audit eligible snapshots;
it is not a prerequisite for Joy's progress. Historical S1/S2/S3 deliveries below
are now Joy's J5/J6/J7; operational scoring is J8. The [arena producer](arena-producer.md)
now supplies the first eight real grids; operational scoring is still pending.

| Owner / task | Work now | Smallest delivery / next dependency |
| --- | --- | --- |
| Joy, J5/J6 | Arena/preview/eight grids complete; group/split validation and larger drops next | 100-grid tail check before frozen 1,000; own producer and consumer checks |
| Joy, J2 | All eight schedules pass actual full-model update on eight real grids | Next: J6 100-grid tail; no collaborator handoff |
| Joy, J7/J3 | Forward-valid collision/order pairs, tracking data and physics checks; fit seven visual controls | Tiny train/dev drops first, full sensitivity sets later; no need to finish all grids first |
| Joy, J8 | Operational metrics, expected keys, coverage/failure ledger and paired analysis | Own known-answer fixtures now; eligible J3 predictions later |
| Sudarshan, S4/S5 | Standalone independent verifier, then snapshot audits; literature/claim review | Own fixtures and documented formats now; see [first deliverable](independent-review.md) |
| Joy, J4 | Resource admission, four-pass screen, then gated expansion | Frozen 1,000 grids + actual H1/H2/resources; H3 and early stability for expansion |

No acknowledgment or completed work is recorded on Sudarshan's behalf. The first
eight real grids are available; evaluation bundles, operational scoring and
independent collaborator verification remain absent.
Compute allocation, intended CUDA hardware, SSv2 access and empirical calibration
remain unverified. Scientific evidence still gates experiments; the other person's
availability does not gate implementation.

## Local setup and synthetic smoke

Run from the repository root with Python 3.11. CPU was checked on macOS arm64.
CUDA is implemented but needs validation on the selected host; MPS is unsupported.
The original model source is retained with its own noncommercial license.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -c requirements-lock.txt -e '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/bullet-time make-fixture --output runs/smoke/data --grids 8
.venv/bin/bullet-time verify-corpus --manifest runs/smoke/data/pretrain.jsonl --image-size 32
.venv/bin/bullet-time audit-update --manifest runs/smoke/data/pretrain.jsonl --model-config configs/models/videomae-test.json --training-config configs/training/pilot-development.json --output runs/smoke/update-audit.json
.venv/bin/bullet-time train --manifest runs/smoke/data/pretrain.jsonl --model-config configs/models/videomae-test.json --training-config configs/training/pilot-development.json --scope synthetic --stop-after-updates 1 --output runs/smoke/first
.venv/bin/bullet-time train --manifest runs/smoke/data/pretrain.jsonl --model-config configs/models/videomae-test.json --training-config configs/training/pilot-development.json --scope synthetic --stop-after-updates 2 --resume runs/smoke/first/step-000001.pt --output runs/smoke/resumed
.venv/bin/bullet-time pilot-slots --output runs/pilot-slots.json
```

Use a new output directory for each attempt. Resume keeps the original fixed
20-pass scheduler and requires identical source/config/data/runtime bindings. An
absolute stop is a segment boundary, not a changed total budget. The runner saves
hashed checkpoints at each completed pass and the requested segment boundary.
`--checkpoint-every-updates N` can select a different recovery interval. Resume is
always from a completed update. Retain the 4/20-pass evaluation checkpoints and
budget intermediate storage on the selected host; do not delete others' artifacts.

The audit executes one actual optimizer update for **each of all eight schedules**,
compares actual transformed per-image pixels, visible/target patch components,
initialization, learning rate, complete-grid membership and optimizer count. Its
losses are synthetic plumbing checks. The native diagnostic deliberately uses
independent clip crops/tube masks and normalized tubelet targets; its targets are
not required to match the controlled arms.

## Bundles Joy now produces and validates

Use [interfaces](interfaces.md) for exact fields, versions and allowed access.

1. Pretraining: `pretrain.jsonl` plus lossless RGB PNGs and a separate `bundle.json`
   inventory/producer provenance. Every grid has all 256 cells. Relative paths and
   both file/decoded-RGB hashes must agree. Send lineage/asset/camera/physics audits
   separately: the pretraining loader has no fields for them. Keep labels and heldout
   data outside its mounted input root; the allowlist is not an operating-system sandbox.
2. Game evaluation: `images.jsonl`, `inputs-train-dev.jsonl` (evaluation v2), private
   `labels-train-dev.jsonl` (labels v1), `groups.json` (evaluation-groups v1), and
   separate J7 physics/visibility evidence. Group whole pairs and related episodes.
   Train/dev counts are 600/200 episodes per task; primary readouts select 300 train
   episodes (150 pairs), diagnostics use all 600. Assessment has 400 and is separate.
3. Tracking: three **consecutive** primary first-reappearance frames and a fixed
   pre-occlusion reference present in every 16-frame causal window. Include at least
   one valid occluded auxiliary query per train/dev episode for visibility training.
   Primary scoring ignores auxiliary queries. Use normalized coordinates after the
   declared letterbox and bounding-box full diagonals on the 224-pixel canvas.
4. J8: expected prediction inventory constructed from planned slots/examples,
   independently of observed predictions, with every key, target-record hash and
   group. Generate assessment inventory in a separate admission process; provide
   only the label-free inventory to fitting/inference. Mount assessment labels
   solely in scoring after the declared version lock. Verify CSV hashes, coverage,
   joins, weighting and gates. S4 may independently reproduce eligible snapshots;
   missing/failed slots must never disappear from either analysis.

The consumer validates identical final RGB and query points across pairs, opposite
primary 0.5-second labels and identical image multisets for the order diagnostic.
These checks cannot prove valid forward dynamics, common continuation rules or
visual solvability. J7 physics evidence plus the seven trained controls are required.
Each horizon has its own head; 0.25/1.0-second secondary heads are additional costs,
not silently included in the 360 primary-horizon fit inventory.

## First real integration and resource measurement

The first eight-grid drop and its measured audit status are in the
[integration report](../reports/arena-integration-20261030.json). Reproduce the
[producer](arena-producer.md), then use the existing full-model consumer audit:

```sh
.venv/bin/bullet-time --threads 4 audit-update \
  --manifest artifacts/arena-eight-v1/rgb-only/pretrain.jsonl \
  --model-config configs/models/videomae-small.json \
  --training-config configs/training/pilot-development.json \
  --output runs/NEW-audit.json
```

`audit-update` requires exactly eight grids;
`train --scope integration --stop-after-updates 1` bounds a single-arm update.
Do not use a synthetic fixture marker for real data. A 100-grid drop additionally
checks the shared four-grid tail through the runner API/tests before freezing the
1,000-grid corpus. Every later experiment must use that same frozen corpus.

For CUDA, set `CUBLAS_WORKSPACE_CONFIG=:4096:8` before starting Python, set `device`
in a copied training config to the actual device and benchmark there. The runtime
binds device, precision, versions, threads and initialization. CPU fixture speed is
not a GPU estimate. Extract an actual complete update JSON record from `updates.jsonl`
and use `estimate-resources --benchmark FILE --output NEW_FILE`. Its extrapolation
covers only the 18 controlled runs; it explicitly excludes native/image/readout/
rendering/tuning/failure costs. Include those before allocating resources.

Real training scopes require a `bullet-time.admission.v1` JSON receipt with exact
fields `scope`, `corpus_sha256`, `model_config_sha256`, `training_config_sha256`,
`evidence`, `maximum_updates`, `approved_device`, and `schema_version`. Config hashes
use `provenance.identity(asdict(config))`, not raw JSON-file bytes. Evidence entries
are `{gate, path, sha256}`, relative to the receipt. Each source JSON report must
identify its `gate`, `verdict: "pass"`, `synthetic_only: false` and the admitted
`corpus_sha256`, backed by the actual audit described in the pilot. Required gates
are H1/H2/resources; full expansion also requires H3/early_stability. Receipts verify
bindings, **not** whether a scientific conclusion is true; do not manufacture them
from synthetic tests. The early cap is 500 updates (four passes) for seed-17
View/Time/Mix50, keeping the full 2,500-update scheduler. The full cap is 2,500.

## References, supervised controls and readouts

```sh
.venv/bin/bullet-time make-reference --model-config configs/models/videomae-small.json --seed 17 --output checkpoints/untrained-s17.pt
.venv/bin/bullet-time prepare-dinov2 --cache .cache/dinov2 --output checkpoints/dinov2-vits14.pt
```

Repeat the untrained command for seeds 29/43 with new names. DINO preparation
explicitly downloads the official pinned archive/weights and checks committed
SHA-256 values before loading code/parameters. It uses normalized patch features,
no CLS/register tokens, and torch attention with xFormers disabled. The three
untrained checkpoints and DINO reference were already materialized in Joy's local
`checkpoints/references/` (ignored by Git); a fresh clone regenerates them.

`pilot-slots` enumerates every model/training/head config: 23 training runs,
4 nontraining references, 360 frozen heads and seven supervised diagnostic fits.
It launches nothing. Use one selected slot's `model` / `training` / `readout` object
as its JSON config. All seven supervised controls start from the **same DINOv2
image weights**, fine-tuned with the same development recipe/budget. This is a
measurement-validity diagnostic, separate from the randomly initialized causal
pretraining arms. Restricted controls enforce final/current-frame access or
permutation-invariant pooling. If the visual sequence control fails, investigate
optimization/task design within the declared pilot budget before interpreting a
null. Do not quietly replace it with an oracle.

```sh
.venv/bin/bullet-time fit-readout --images INPUT/images.jsonl --inputs INPUT/inputs-train-dev.jsonl --labels PRIVATE/labels-train-dev.jsonl --groups PRIVATE/groups.json --backbone CHECKPOINT.pt --readout-config HEAD.json --output runs/UNIQUE-fit
.venv/bin/bullet-time predict-readout --images INPUT/images.jsonl --inputs INPUT/inputs-assessment.jsonl --checkpoint runs/UNIQUE-fit/readout.pt --expected INPUT/expected.json --split assessment --output runs/UNIQUE-predictions
```

For DINO, add `--external-cache .cache/dinov2` to both commands. Fit uses only train/
dev, freezes the backbone for `kind: "frozen"`, and selects by development loss.
`kind: "diagnostic"` fine-tunes the common image backbone. Inputs, labels, selection,
config, source checkpoint and fit are hash-bound. For frozen heads, the output inventory's `run_id` is the backbone binding hash and
`checkpoint_id` its file SHA-256. For supervised diagnostics, the run ID binds the
parent plus the full diagnostic configuration/mode, and checkpoint ID is the fitted
diagnostic file SHA-256. Use the explicit `prediction_identity` in the fit output/
checkpoint sidecar. `label_budget` is the actual training episode/video count. Human slot names are
planning aliases; map them explicitly to these hashes. The CLI rejects a misnamed
run/checkpoint/budget. Readout seeds are 101/102/103; primary horizon is 0.5 seconds.
Fitting never reads assessment labels. Prediction also checks stored split eligibility
before loading inputs: early/incomplete learned checkpoints and every SSv2 head are
development-only; game assessment requires a completed 20-pass learned checkpoint
or an untrained/external reference. Older synthetic readouts lacking this policy
must be regenerated. The final official SSv2 validation split is
not accepted by this pilot CLI.

## SSv2 preparation

Joy obtains permitted official-training videos/labels and related-video group IDs.
Sudarshan may independently audit the snapshot; access is not delegated to him
as a prerequisite.
`ssv2-partitions --metadata FILE --output FILE` takes a JSON array of
`{video_id: "canonical decimal", class_id: 0..173, official_split: "train"}` and
implements the frozen class-stratified internal dev / remaining-train 10% subset.
This is a deterministic proposal; the complete group audit must agree before use.
If a related group crosses a boundary, fail, version the split and record the
deviation; do not silently reassign individual videos. Official validation is reserved for final work.

`extract-video --video FILE --video-id ID --output NEW_DIRECTORY` decodes the single
video stream in presentation order, with one decoder thread, chooses the fixed 16
uniform indices, and writes hashed RGB PNGs, `images.jsonl` and `decode.json` with
PyAV/FFmpeg/source provenance. Short videos repeat selected IDs. Joy's aggregate
manifest must preserve hashes and relative paths. SSv2 fitting additionally requires
`--partitions PARTITIONS.json --groups VIDEO_GROUP_MAP.json` and exact selected
train/dev inventories. The group map covers every video in the partition proposal.

## Remaining gates

Run scaffold/math/pilot-hash checks and implementation tests before handoff; CI does
both. An independent implementation review is recorded separately from collaborator
acceptance. No toy score is entered into H1–H4, no full study is launched, and no
CVPR acceptance/novelty conclusion follows from this implementation. A credible
result still needs sensitive controls, useful learned/transfer performance, complete
paired coverage and prospective precision/scale evidence. Joy's next required
inputs are J7 evaluation bundles, J8 operational scoring and larger J6 drops with
group/split and 100-grid tail validation.
Independent S4 verification is a separate pending evidence status. Preserve the
assessment isolation and version-lock rules in the ownership map; never call
same-person producer/consumer checks independent collaborator validation.

For long runs, use an immutable checkout of the recorded commit and develop in a
separate checkout. Pretraining/resume and readout inference bind the executing
consumer source plus model pins; inference also records its actual runtime.
Unimported producer/analysis changes do not affect this consumer fingerprint.
Extend it if adding a runtime import, and bind scoring's own code/config separately.
Fit/infer use the same consumer revision; a source change requires running the original revision
or refitting explicitly. See the interface's pixel-center formula when preparing
tracking labels or query points for any resized input.
