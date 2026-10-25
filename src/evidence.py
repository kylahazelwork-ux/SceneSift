"""Get frames from a video to show as evidence for an answer."""
import cv2


def frame_at(video_path, seconds):
    """Return the frame at the given time as an RGB image, or None.

    OpenCV reads images as BGR (blue, green, red), but web pages and Gradio
    expect RGB, so the frame must be converted before it's returned.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Jump straight to the frame instead of reading every frame before it.
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
    ok, frame = cap.read()
    cap.release()

    if not ok:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
