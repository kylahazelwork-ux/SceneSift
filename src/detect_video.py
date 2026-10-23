"""Detect people in every frame of a video and save an annotated copy.

Each output frame shows person boxes, labels, confidence scores, and the
frame's timestamp.

Usage (run from the project root):
    python src/detect_video.py sample_videos/vtest.avi
"""
import sys

import cv2
from ultralytics import YOLO


def main():
    if len(sys.argv) != 2:
        print("Usage: python src/detect_video.py <path-to-video>")
        sys.exit(1)
    video_path = sys.argv[1]

    # Load a pretrained model. First run downloads the model file.
    model = YOLO("yolo26n.pt")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video: {video_path}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Timestamps and the output video both need a valid frame rate.
    if fps <= 0:
        cap.release()
        raise ValueError("Video has no valid frame rate")

    output_path = "outputs/detected.mp4"
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not create {output_path}")

    frame_number = 0

    try:
        while True:
            # 1. Read the next frame.
            ok, frame = cap.read()
            if not ok:
                break

            # 2. Detect people in this frame. Class 0 is "person".
            result = model.predict(
                frame, classes=[0], conf=0.25, verbose=False
            )[0]

            # 3. Draw boxes, person labels, and confidence scores.
            frame = result.plot(boxes=True, labels=True, conf=True)

            # 4. Draw the frame's position in the video.
            timestamp = frame_number / fps
            cv2.putText(
                frame,
                f"{timestamp:.2f} s",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            # 5. Write the annotated frame.
            writer.write(frame)
            frame_number += 1
    finally:
        cap.release()
        writer.release()

    print(f"Saved {frame_number} frames to {output_path}")


if __name__ == "__main__":
    main()
