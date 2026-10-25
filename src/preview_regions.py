"""Draw the zone and line from a regions file on a video's first frame.

Use this to check where the zone and line are before running analysis.

Usage (run from the project root):
    python src/preview_regions.py sample_videos/vtest.avi config/vtest_regions.json
"""
import json
import sys

import cv2
import numpy as np


def main():
    if len(sys.argv) != 3:
        print("Usage: python src/preview_regions.py <path-to-video> <path-to-regions-json>")
        sys.exit(1)
    video_path, regions_path = sys.argv[1], sys.argv[2]

    with open(regions_path) as f:
        regions = json.load(f)

    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print(f"Error: could not read a frame from: {video_path}")
        sys.exit(1)

    # Zone: a closed green outline. polylines expects a numpy array of int32 points.
    zone = np.array(regions["zone"], dtype=np.int32)
    cv2.polylines(frame, [zone], isClosed=True, color=(0, 255, 0), thickness=2)

    # Line: red, with its two endpoints labeled A and B so direction is visible.
    (ax, ay), (bx, by) = regions["line"]
    cv2.line(frame, (ax, ay), (bx, by), color=(0, 0, 255), thickness=2)
    cv2.putText(frame, "A", (ax + 5, ay), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(frame, "B", (bx + 5, by), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    output_path = "outputs/regions_preview.jpg"
    if cv2.imwrite(output_path, frame):
        print(f"Saved preview to {output_path}")
    else:
        print(f"Error: could not save preview to {output_path}")


if __name__ == "__main__":
    main()
