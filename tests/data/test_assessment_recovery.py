"""Raw-byte receipt fixtures; deliberately not physical/native admission evidence."""

import pytest

from bullet_time.generation import assessment_recovery as recovery
from bullet_time.generation import assessment_capture as capture
from bullet_time.provenance import atomic_json, canonical_bytes


def group(root, gid):
    private, rgb = root / "private" / gid, root / "inputs/rgb" / gid
    private.mkdir(parents=True)
    rgb.mkdir(parents=True)
    request = {"group_id": gid, "task": gid.split("-")[0], "fixture": True}
    atomic_json(private / "request.json", request)
    (private / "render.json").write_text("synthetic raw receipt fixture")
    (rgb / "frame.png").write_bytes(b"synthetic raw bytes; not an admitted image")
    return request


@pytest.fixture
def journal(tmp_path):
    sources, pin = capture.source_files(), {"synthetic_engine": "fixture"}
    recovery.begin(
        tmp_path,
        source_files=sources,
        engine_pin=pin,
        selection_sha256="a" * 64,
        per_task=8,
        source_commit="synthetic",
    )
    return tmp_path, sources, pin


def test_partial_reuse_retains_only_completed_receipts(journal):
    root, sources, pin = journal
    first = group(root, "collision-0123456789abcdef")
    group(root, "order-0123456789abcdef")  # interrupted before group receipt
    recovery.record_group(root, first, {"synthetic_command": True})
    (root / "captures/.interrupted.json").write_text("partial atomic write")
    recovered = recovery.load_reusable(root, pin, sources)
    assert recovered[0] == root and recovered[2] == {first["group_id"]}
    assert not (root / "source.json").exists()
    with pytest.raises(ValueError, match="already exists"):
        recovery.record_group(root, first, {})
    with pytest.raises(ValueError, match="already exists"):
        recovery.begin(
            root,
            source_files=sources,
            engine_pin=pin,
            selection_sha256="a" * 64,
            per_task=8,
            source_commit="synthetic",
        )


@pytest.mark.parametrize("change", ["raw", "request", "header", "receipt", "extra_file", "link"])
def test_partial_capture_tampering_is_not_reusable(journal, change):
    root, sources, pin = journal
    request = group(root, "tracking-0123456789abcdef")
    gid = request["group_id"]
    recovery.record_group(root, request, {"synthetic_command": True})
    if change == "raw":
        (root / "inputs/rgb" / gid / "frame.png").write_bytes(b"changed")
    elif change == "request":
        atomic_json(root / "private" / gid / "request.json", dict(request, fixture=False))
    elif change == "header":
        path = root / "capture.json"
        path.write_bytes(path.read_bytes() + b"\n")
    elif change == "receipt":
        path = root / "captures" / f"{gid}.json"
        path.write_text("{}")
    elif change == "extra_file":
        (root / "private" / gid / "unexpected").write_text("extra")
    else:
        (root / "private" / gid / "alias").symlink_to(root / "capture.json")
    with pytest.raises((ValueError, KeyError)):
        recovery.load_reusable(root, pin, sources)


def test_full_count_prefix_preserves_all_declared_groups(tmp_path):
    counts = {"collision": 200, "order": 200, "tracking": 400}
    rows = [
        dict(task=task, split="assessment", group_id=f"{task}-{index}")
        for task, n in counts.items()
        for index in range(n)
    ]
    (tmp_path / "requests.jsonl").write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in rows))
    assert capture.prefix(tmp_path, 400) == rows
    assert capture._plan(400)["groups_per_task"] == {
        task: {"assessment": n} for task, n in counts.items()
    }
    assert len(capture.prefix(tmp_path, 8)) == 24


@pytest.mark.parametrize("relative", ["private", "inputs", "inputs/rgb"])
def test_interrupted_capture_rejects_linked_parent_components(journal, relative):
    import shutil

    root, sources, pin = journal
    request = group(root, "collision-0123456789abcdef")
    recovery.record_group(root, request, {"synthetic_command": True})
    original = root / relative
    external = root.parent / ("external-" + relative.replace("/", "-"))
    shutil.move(original, external)
    original.symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="components cannot be linked"):
        recovery.load_reusable(root, pin, sources)
    assert external.is_dir() and original.is_symlink()
