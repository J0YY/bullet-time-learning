# First real development snapshot for S4b

This is a ready scoring/coverage audit for Sudarshan, independent of the full pilot.
It contains one real DINOv2 diagnostic readout, trained for one epoch on 32 collision
training episodes and evaluated on 16 development episodes (eight complete pairs).
The result is **50% balanced accuracy**, Brier **0.26998311140976217**. This is plumbing
evidence, not H3, learning quality, paired-seed inference or CVPR evidence.

Start by checking every hash in `snapshot.json`. Reconstruct expected keys from
`evaluation-inputs.jsonl`, `groups.json`, `labels.jsonl` and the declared fit/run
identity, then compare with `expected.json`; do not derive coverage from observed
CSV rows. The snapshot builder already verified exact equality with the expected
inventory written before inference. `predictions/` and `fit.json` are byte-for-byte
copies of the actual run. The permitted labels/input/group records are an explicit
subset of the original dev drop; their new hashes do not replace original hashes.

Use S4's own implementation to recompute coverage, BA, per-class recall and Brier.
Check duplicate/missing keys and target-reference hashes. First delivery should be
a commit, one command, observed results and discrepancy reproductions under
`reports/independent/`. No GPU, RGB download, renderer or meeting is needed. Tracking,
SSv2 and paired statistics still need the S4a known-answer fixtures described in
[the brief](../../../../docs/independent-review.md).

For comparison only, reproduce Joy's scorer from the repository root:

```sh
.venv/bin/python - <<'PYCODE'
import hashlib, json
from pathlib import Path
from bullet_time.evaluation.scoring import score_directory
p = Path('reports/data/audit-snapshots/diagnostic-dev-v1')
m = json.loads((p / 'snapshot.json').read_text())
for name, expected in m['inventory'].items():
    assert hashlib.sha256((p / name).read_bytes()).hexdigest() == expected, name
r = score_directory(p / 'predictions', p / 'expected.json', p / 'labels.jsonl',
                    p / 'groups.json', split='dev', families=['projectile_arena'])
assert r['complete'] and r['primary'] == m['result']['balanced_accuracy']
assert r['families']['projectile_arena']['brier'] == m['result']['brier']
print(json.dumps(r['families'], indent=2))
PYCODE
```

`historical-score.json` preserves the original full-source scoring report;
`joy-score.json` binds this subset and the current scoring source. Neither is an
independent collaborator review. Model/RGB files are omitted, so this package
cannot reproduce fitting or verify pixel/physics admission. No assessment or final
test is included. Required work continues without waiting for this audit.
