"""Deterministic selected-frame decoding; no dataset acquisition or split decisions."""

from pathlib import Path
import av
from PIL import Image
from bullet_time.provenance import digest, atomic_json
from .inputs import uniform_frame_indices


def decode_action_video(path):
    path = Path(path).resolve(strict=True)
    source_hash = digest(path.read_bytes())

    def frames():
        with av.open(str(path)) as container:
            if len(container.streams.video) != 1:
                raise ValueError("exactly one video stream required")
            stream = container.streams.video[0]
            stream.thread_count = 1
            previous = None
            for frame in container.decode(stream):
                if frame.pts is None or previous is not None and frame.pts <= previous:
                    raise ValueError("missing or nonincreasing decoded frame timestamps")
                previous = frame.pts
                yield frame

    count = sum(1 for _ in frames())
    indices = uniform_frame_indices(count)
    selected = {}
    for index, frame in enumerate(frames()):
        if index in indices:
            selected[index] = frame.to_ndarray(format="rgb24").copy()
    if digest(path.read_bytes()) != source_hash or len(selected) != len(set(indices)):
        raise ValueError("video changed during decoding")
    provenance = {
        "video_sha256": source_hash,
        "decoded_frame_count": count,
        "selected_frame_indices": list(indices),
        "av_version": av.__version__,
        "ffmpeg_versions": {k: list(v) for k, v in av.library_versions.items()},
        "decode_policy": "single video stream, presentation order, one decoder thread, RGB24",
    }
    return [selected[i] for i in indices], provenance


def extract_action_video(path, output, video_id):
    """Produce a content-hashed RGB catalog; S supplies labels/groups/input split."""
    from bullet_time.provenance import text_id
    import json

    text_id(video_id, "video_id")
    frames, record = decode_action_video(path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    ids = []
    for index, rgb in zip(record["selected_frame_indices"], frames):
        identifier = f"{video_id}/frame-{index}"
        ids.append(identifier)
        if any(r["image_id"] == identifier for r in rows):
            continue
        target = output / f"frame-{index:06d}.png"
        Image.fromarray(rgb).save(target)
        rows.append(
            {
                "image_id": identifier,
                "rgb_path": target.name,
                "file_sha256": digest(target.read_bytes()),
                "rgb_sha256": digest(rgb.tobytes()),
                "height": rgb.shape[0],
                "width": rgb.shape[1],
                "channels": 3,
            }
        )
    (output / "images.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    )
    record.update(
        observed_image_ids=ids, image_manifest_sha256=digest((output / "images.jsonl").read_bytes())
    )
    atomic_json(output / "decode.json", record)
    return record
