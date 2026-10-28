import av
import numpy as np
from bullet_time.evaluation.video_decode import decode_action_video, extract_action_video
from bullet_time.evaluation.inputs import ImageStore, uniform_frame_indices


def test_decode_selected_frames_and_hashed_export(tmp_path):
    path = tmp_path / "synthetic.mp4"
    expected = []
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=16)
        stream.width = 32
        stream.height = 24
        stream.pix_fmt = "yuv420p"
        for i in range(21):
            rgb = np.full((24, 32, 3), i * 10, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    with av.open(str(path)) as container:
        expected = [frame.to_ndarray(format="rgb24") for frame in container.decode(video=0)]
    frames, report = decode_action_video(path)
    assert report["selected_frame_indices"] == list(uniform_frame_indices(21))
    for frame, index in zip(frames, report["selected_frame_indices"]):
        np.testing.assert_array_equal(frame, expected[index])
    record = extract_action_video(path, tmp_path / "selected", "123")
    store = ImageStore(tmp_path / "selected/images.jsonl")
    for identifier, frame in zip(record["observed_image_ids"], frames):
        np.testing.assert_array_equal(store.read(identifier), frame)
