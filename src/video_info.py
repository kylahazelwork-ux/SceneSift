"""Print basic information about a video and save one frame.

Usage (run from the project root):
    python src/video_info.py sample_videos/vtest.avi
"""
import sys

import cv2


def main():
    if len(sys.argv) != 2:
        print("Usage: python src/video_info.py <path-to-video>")
        sys.exit(1)
    video_path = sys.argv[1]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video: {video_path}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Guard against fps of 0, which some broken files report.
    duration_seconds = frame_count / fps if fps > 0 else 0.0

    print(f"Resolution: {width}x{height}")
    print(f"Frame rate: {fps:.2f} fps")
    print(f"Frames:     {frame_count}")
    print(f"Duration:   {duration_seconds:.2f} s")

    # Read the first frame. read() gives back two things: a success flag and the image.
    ok, frame = cap.read()
    if not ok:
        print("Error: could not read a frame")
        sys.exit(1)

    # Save the image to a file. imwrite returns False instead of raising an error.
    output_path = "outputs/frame.jpg"
    saved = cv2.imwrite(output_path, frame)

    if saved:
        print(f"Saved frame to {output_path}")
    else:
        print(f"Error: could not save frame to {output_path}")

    cap.release()


if __name__ == "__main__":
    main()
