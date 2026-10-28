import json
from bullet_time.models.video import ModelConfig
from bullet_time.evaluation.inputs import ImageStore
from .factory import make_corpus

TINY = ModelConfig(
    image_size=32,
    patch_size=8,
    encoder_width=24,
    encoder_depth=1,
    encoder_heads=3,
    decoder_width=24,
    decoder_depth=1,
    decoder_heads=3,
)


def fixtures(root, task="collision"):
    manifest = make_corpus(root, count=1)
    grid = json.loads(manifest.read_text())
    rows = [
        {k: v for k, v in cell.items() if k not in ("world_time_index", "camera_index")}
        for cell in grid["cells"]
    ]
    catalog = root / "images.jsonl"
    catalog.write_text("".join(json.dumps(r) + "\n" for r in rows))
    inputs = root / "inputs.jsonl"
    row = dict(
        schema_version="bullet-time.evaluation.v2",
        episode_id="example",
        query_id="query",
        task_id=task,
        split="train",
        observed_image_ids=[f"0/{i}/0" for i in range(16)],
        observed_frame_indices=list(range(16)),
        query_points=[[0.3, 0.4], [0.5, 0.6]],
        horizon_seconds=0.5,
    )
    inputs.write_text(json.dumps(row) + "\n")
    return inputs, ImageStore(catalog), row
