import cv2
import numpy as np

from evidence import frame_at


def make_video(path, colors, fps=10):
    """Write a tiny video where frame i is filled with colors[i] (BGR)."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (32, 32))
    for color in colors:
        writer.write(np.full((32, 32, 3), color, dtype=np.uint8))
    writer.release()


def test_frame_at_returns_the_right_frame(tmp_path):
    path = tmp_path / "test.avi"
    make_video(path, [(0, 0, 0), (0, 0, 0), (255, 255, 255), (0, 0, 0)])
    frame = frame_at(str(path), 0.2)  # frame 2 at 10 fps is white
    assert frame is not None
    assert frame.mean() > 200


def test_frame_at_converts_bgr_to_rgb(tmp_path):
    path = tmp_path / "test.avi"
    make_video(path, [(255, 0, 0)] * 3)  # pure blue in OpenCV's BGR order
    frame = frame_at(str(path), 0.0)
    # In RGB order, blue is the last channel.
    assert frame[16, 16, 2] > 200
    assert frame[16, 16, 0] < 50


def test_frame_at_past_the_end_returns_none(tmp_path):
    path = tmp_path / "test.avi"
    make_video(path, [(0, 0, 0)] * 3)
    assert frame_at(str(path), 99.0) is None
