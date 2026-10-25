"""Track people in a video and record zone entries, line crossings, and occupancy.

Saves:
    outputs/analyzed.mp4   annotated video with the zone, line, and foot points
    outputs/events.csv     one row per zone entry or line crossing
    outputs/occupancy.csv  number of people in the zone at every frame

Usage (run from the project root):
    python src/analyze_video.py sample_videos/vtest.avi config/vtest_regions.json
"""
import csv
import json
import sys

import cv2
import numpy as np
from ultralytics import YOLO

from events import EventDetector
from geometry import bottom_middle

EVENT_FIELDS = ["time", "track_id", "event", "class", "direction"]


def main():
    if len(sys.argv) != 3:
        print("Usage: python src/analyze_video.py <path-to-video> <path-to-regions-json>")
        sys.exit(1)
    video_path, regions_path = sys.argv[1], sys.argv[2]

    with open(regions_path) as f:
        regions = json.load(f)
    detector = EventDetector(regions["zone"], regions["line"])

    model = YOLO("yolo26n.pt")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video: {video_path}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError("Video has no valid frame rate")

    video_output = "outputs/analyzed.mp4"
    writer = cv2.VideoWriter(
        video_output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not create {video_output}")

    zone_points = np.array(regions["zone"], dtype=np.int32)
    line_a, line_b = (tuple(p) for p in regions["line"])

    all_events = []
    occupancy = []  # (frame, time, people_in_zone)
    frame_number = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp = frame_number / fps

            result = model.track(
                frame, classes=[0], conf=0.25, verbose=False,
                persist=True, tracker="bytetrack.yaml",
            )[0]

            # Convert the model's output into (track_id, class_name, box) tuples.
            tracks = []
            if result.boxes.id is not None:
                ids = result.boxes.id.int().tolist()
                classes = result.boxes.cls.int().tolist()
                boxes = result.boxes.xyxy.tolist()
                for track_id, class_id, box in zip(ids, classes, boxes):
                    tracks.append((track_id, result.names[class_id], box))

            events = detector.update(timestamp, tracks)
            for event in events:
                print(f"{event['time']:6.1f} s  ID {event['track_id']:>3}  "
                      f"{event['event']}  {event['direction'] or ''}")
            all_events.extend(events)

            # Occupancy: tracks in this frame whose foot point is inside the zone.
            in_zone = sum(detector.was_inside[t[0]] for t in tracks)
            occupancy.append((frame_number, round(timestamp, 2), in_zone))

            # Draw boxes and IDs, then the zone, line, foot points, and counts.
            frame = result.plot(boxes=True, labels=True, conf=False)
            cv2.polylines(frame, [zone_points], isClosed=True, color=(0, 255, 0), thickness=2)
            cv2.line(frame, line_a, line_b, color=(0, 0, 255), thickness=2)
            for _, _, box in tracks:
                x, y = bottom_middle(box)
                cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 255), -1)
            cv2.putText(
                frame, f"{timestamp:.1f} s  in zone: {in_zone}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA,
            )

            writer.write(frame)
            frame_number += 1
    finally:
        cap.release()
        writer.release()

    with open("outputs/events.csv", "w", newline="") as f:
        csv_writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        csv_writer.writeheader()
        csv_writer.writerows(all_events)

    with open("outputs/occupancy.csv", "w", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["frame", "time", "people_in_zone"])
        csv_writer.writerows(occupancy)

    entries = sum(e["event"] == "zone_entry" for e in all_events)
    crossings = sum(e["event"] == "line_crossing" for e in all_events)
    print(f"\nProcessed {frame_number} frames")
    print(f"Zone entries: {entries}, line crossings: {crossings}")
    print(f"Saved {video_output}, outputs/events.csv, outputs/occupancy.csv")


if __name__ == "__main__":
    main()
