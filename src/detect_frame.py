import cv2
from ultralytics import YOLO


def main():
    # Read just the first frame.
    cap = cv2.VideoCapture("sample_videos/vtest.avi")
    ok, frame = cap.read()
    cap.release()

    if not ok:
        raise RuntimeError("Could not read the first video frame")

    # Load a pretrained model. First run downloads the model file.
    model = YOLO("yolo26n.pt")

    # Class 0 is "person" for this model.
    result = model.predict(
        frame, classes=[0], conf=0.25, verbose=False
    )[0]

    print(f"Detected {len(result.boxes)} people")

    for number, box in enumerate(result.boxes, start=1):
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        confidence = box.conf[0].item()

        print(
            f"Detection {number}: "
            f"box=({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}), "
            f"confidence={confidence:.2f}"
        )


if __name__ == "__main__":
    main()