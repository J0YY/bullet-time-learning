# Real-data readout integration — October 30, 2026 EDT

The pinned DINOv2 sequence diagnostic completed one epoch on the admitted collision
microtask, then exported and scored **all 16 development predictions**. Balanced
accuracy was **50%**. This establishes real fit → inference → scoring execution;
it does not establish learned sensitivity or pass H3. One epoch on 32 training
and 16 development episodes is far below the selected diagnostic workload.

The [report](readout-integration-20261030.json) binds code `0edab89`, actual input/
label/catalog hashes, model source, configuration, fitted checkpoint, prediction
inventory and scorer implementation. Fit took 95.74 seconds on one CPU thread,
FP32, with peak child RSS 2,493,825,024 bytes (about 2.32 GiB). Training and development
losses were 1.3942 and 0.7348. No hyperparameter search or assessment inspection ran.

Commands used the checked-in `configs/readouts/measurement-integration.json`,
`artifacts/evaluation-development-v2`, existing `checkpoints/references/dinov2-vits14.pt`
and `.cache/dinov2`. Outputs are `runs/measurement-fit-v1`,
`runs/measurement-predict-v1`, and `runs/measurement-predict-v1.score.json`.
The fit execution receipt contains the exact command and timing; predictions use
`predict-readout --split dev` with its separately hashed expected-key inventory.

The [local resource calculation](local-resource-plan-20261030.json) combines this
measurement with the earlier full VideoMAE update audit. Linear CPU extrapolation
puts the first three four-pass runs at **16.9–22.7 hours** and the eighteen controlled
twenty-pass runs at **508–681 hours**, before references, readouts, transfer and
most overhead. Scaling this tiny fit by example count gives about 8.9 hours for one
full twenty-epoch collision sequence diagnostic, but different batch sizes and
train/dev proportions may change that substantially. These are planning estimates,
not GPU benchmarks or approved allocations. Do not launch that workload on the
Mac by default; validate an authorized CUDA host and storage first.

Full evaluation sets, stronger varied tasks, assessment isolation/release and H3/H4
remain required. The local pipeline can continue to improve independently of
Sudarshan. His optional independent verification remains unrecorded.
