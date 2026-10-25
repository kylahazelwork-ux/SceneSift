"""Track people in a video and record zone entries, line crossings, and occupancy.

Saves:
    outputs/analyzed.mp4   annotated video with the zone, line, and foot points
    outputs/events.csv     one row per zone entry or line crossing
    outputs/occupancy.csv  number of people in the zone at every frame
    outputs/analysis_info.json  which video, zone, and line were used

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
VIDEO_OUTPUT = "outputs/analyzed.mp4"
EVENTS_OUTPUT = "outputs/events.csv"
OCCUPANCY_OUTPUT = "outputs/occupancy.csv"
INFO_OUTPUT = "outputs/analysis_info.json"


def analyze(video_path, regions, progress=None, print_events=False):
    """Analyze a video and save the annotated video, events, and occupancy.

    regions is a dict with "zone" (list of [x, y] points) and "line" (two
    [x, y] points). Either one can be empty, but not both. progress, if given, is called as progress(done, total)
    after each frame. Returns a dict summarizing the results.
    """
    zone, line = regions.get("zone") or [], regions.get("line") or []
    if not zone and not line:
        raise ValueError("Set a zone, a line, or both")
    detector = EventDetector(zone, line)

    model = YOLO("yolo26n.pt")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0:
        cap.release()
        raise ValueError("Video has no valid frame rate")

    writer = cv2.VideoWriter(
        VIDEO_OUTPUT, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not create {VIDEO_OUTPUT}")

    zone_points = np.array(zone, dtype=np.int32) if zone else None

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
            if print_events:
                for event in events:
                    print(f"{event['time']:6.1f} s  ID {event['track_id']:>3}  "
                          f"{event['event']}  {event['direction'] or ''}")
            all_events.extend(events)

            # Occupancy: tracks in this frame whose foot point is inside the zone.
            in_zone = detector.in_zone_count(tracks)
            if zone:
                occupancy.append((frame_number, round(timestamp, 2), in_zone))

            # Draw boxes and IDs, then the zone, line, foot points, and counts.
            frame = result.plot(boxes=True, labels=True, conf=False)
            if zone:
                cv2.polylines(frame, [zone_points], isClosed=True, color=(0, 255, 0), thickness=2)
            if line:
                cv2.line(frame, tuple(line[0]), tuple(line[1]), color=(0, 0, 255), thickness=2)
            for _, _, box in tracks:
                x, y = bottom_middle(box)
                cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 255), -1)
            label = f"{timestamp:.1f} s  in zone: {in_zone}" if zone else f"{timestamp:.1f} s"
            cv2.putText(
                frame, label, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA,
            )

            writer.write(frame)
            frame_number += 1
            if progress:
                progress(frame_number, total_frames)
    finally:
        cap.release()
        writer.release()

    with open(EVENTS_OUTPUT, "w", newline="") as f:
        csv_writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        csv_writer.writeheader()
        csv_writer.writerows(all_events)

    with open(OCCUPANCY_OUTPUT, "w", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["frame", "time", "people_in_zone"])
        csv_writer.writerows(occupancy)

    # Record what was analyzed, so answers can say "no line was set" instead of
    # "no one crossed", and the app can detect out-of-date results.
    with open(INFO_OUTPUT, "w") as f:
        json.dump({"video": str(video_path), "regions": {"zone": zone, "line": line}}, f)

    return {
        "frames": frame_number,
        "entries": sum(e["event"] == "zone_entry" for e in all_events),
        "crossings": sum(e["event"] == "line_crossing" for e in all_events),
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python src/analyze_video.py <path-to-video> <path-to-regions-json>")
        sys.exit(1)
    video_path, regions_path = sys.argv[1], sys.argv[2]

    with open(regions_path) as f:
        regions = json.load(f)

    try:
        summary = analyze(video_path, regions, print_events=True)
    except FileNotFoundError as error:
        print(f"Error: {error}")
        sys.exit(1)

    print(f"\nProcessed {summary['frames']} frames")
    print(f"Zone entries: {summary['entries']}, line crossings: {summary['crossings']}")
    print(f"Saved {VIDEO_OUTPUT}, {EVENTS_OUTPUT}, {OCCUPANCY_OUTPUT}")


if __name__ == "__main__":
    main()
