"""Make one review image per event in a time window, for checking events by eye.

Each image shows the annotated video just before, at, and just after the event.
Also writes a review sheet (CSV) with an empty "verdict" column to fill in.

Usage (run from the project root, after analyze_video.py):
    python src/review_events.py 15 35
"""
import csv
import os
import sys

import cv2

VIDEO = "outputs/analyzed.mp4"
EVENTS = "outputs/events.csv"
REVIEW_DIR = "outputs/review"
OFFSET_SECONDS = 0.5  # how far before and after the event to show
SCALE = 0.6           # shrink frames so three fit side by side


def main():
    if len(sys.argv) != 3:
        print("Usage: python src/review_events.py <start-seconds> <end-seconds>")
        sys.exit(1)
    start, end = float(sys.argv[1]), float(sys.argv[2])

    with open(EVENTS, newline="") as f:
        events = [e for e in csv.DictReader(f) if start <= float(e["time"]) <= end]

    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        print(f"Error: could not open {VIDEO}. Run analyze_video.py first.")
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(seconds):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, round(seconds * fps)))
        ok, frame = cap.read()
        return cv2.resize(frame, None, fx=SCALE, fy=SCALE) if ok else None

    os.makedirs(REVIEW_DIR, exist_ok=True)
    rows = []
    for number, event in enumerate(events, start=1):
        t = float(event["time"])
        frames = [frame_at(t - OFFSET_SECONDS), frame_at(t), frame_at(t + OFFSET_SECONDS)]
        if any(f is None for f in frames):
            continue
        image_name = f"{number:02d}_{t:.1f}s_id{event['track_id']}_{event['event']}.jpg"
        cv2.imwrite(os.path.join(REVIEW_DIR, image_name), cv2.hconcat(frames))
        rows.append({**event, "image": image_name, "verdict": "", "notes": ""})
    cap.release()

    sheet = os.path.join(REVIEW_DIR, "review.csv")
    with open(sheet, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} review images and {sheet}")


if __name__ == "__main__":
    main()
