"""Deterministic consumer-owned fixtures. Not game renders or scientific evidence."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from bullet_time.provenance import digest


def make_corpus(root, count=2, size=32):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    records = []
    y, x = np.indices((size, size))
    for g in range(count):
        row = {'schema_version': 'bullet-time.grid.v1', 'grid_id': f'synthetic-{g:04}',
               'scene_family': 'fixture_family', 'cells': []}
        for t in range(16):
            for c in range(16):
                rgb = np.stack([(x * 7 + t * 13 + g) % 256, (y * 11 + c * 17) % 256,
                                (x + y + 19 * t + 23 * c) % 256], -1).astype('uint8')
                relative = f'rgb/{g}/{t}_{c}.png'
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(rgb).save(path)
                row['cells'].append(dict(world_time_index=t, camera_index=c,
                    image_id=f'{g}/{t}/{c}', rgb_path=relative, file_sha256=digest(path.read_bytes()),
                    rgb_sha256=digest(rgb.tobytes()), height=size, width=size, channels=3))
        records.append(row)
    manifest = root / 'pretrain.jsonl'
    manifest.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in records))
    (root/'fixture.json').write_text(json.dumps({'synthetic_only': True, 'purpose': 'consumer tests'}))
    return manifest
