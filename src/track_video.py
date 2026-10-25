"""Track people across video frames with ByteTrack and save an annotated copy.

Each output frame shows person boxes, tracking IDs, labels, confidence scores, and the
frame's timestamp. Prints each track's first and last sighting after processing.

Usage (run from the project root):
    python src/track_video.py sample_videos/vtest.avi
"""
import sys

import cv2
from ultralytics import YOLO


def main():
    if len(sys.argv) != 2:
        print("Usage: python src/track_video.py <path-to-video>")
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

    output_path = "outputs/tracked.mp4"
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
    first_seen = {}
    last_seen = {}

    try:
        while True:
            # 1. Read the next frame.
            ok, frame = cap.read()
            if not ok:
                break

            # 2. Track people, keeping tracker state between frames.
            result = model.track(
                frame, classes=[0], conf=0.25, verbose=False,
                persist=True, tracker="bytetrack.yaml",
            )[0]

            # 3. Draw boxes, tracking IDs, person labels, and confidence scores.
            frame = result.plot(boxes=True, labels=True, conf=True)

            # 4. Draw the frame's position in the video.
            timestamp = frame_number / fps
            ids = result.boxes.id.int().tolist() if result.boxes.id is not None else []
            for track_id in ids:
                if track_id not in first_seen:
                    first_seen[track_id] = timestamp
                last_seen[track_id] = timestamp

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
    print(f"Unique track IDs: {len(first_seen)}")
    for track_id in sorted(first_seen):
        duration = last_seen[track_id] - first_seen[track_id]
        short = "  <-- short" if duration < 1.0 else ""
        print(
            f"ID {track_id}: first={first_seen[track_id]:.1f} s, "
            f"last={last_seen[track_id]:.1f} s, "
            f"duration={duration:.1f} s{short}"
        )


if __name__ == "__main__":
    main()
