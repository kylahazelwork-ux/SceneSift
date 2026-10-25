"""Measure SceneSift's speed, memory, and event quality under different settings.

Video pipeline (detection + tracking + events, no video writing):
    python src/benchmark.py video --device cpu
    python src/benchmark.py video --device cuda
    python src/benchmark.py video --device cpu --imgsz 320
    python src/benchmark.py video --device cpu --frame-step 2

Speech and question answering:
    python src/benchmark.py speech sample_audio/enter.m4a

Each video run appends a row to outputs/benchmarks.csv. Event quality is
compared with outputs/baseline_events.csv (copied from the first CPU run at
default settings), counting an event as matched if the same type happens
within MATCH_SECONDS.
"""
import argparse
import csv
import json
import os
import time

import cv2
import psutil
import torch
from ultralytics import YOLO

from events import EventDetector
from questions import answer, load_events, load_occupancy, load_regions

VIDEO = "sample_videos/vtest.avi"
REGIONS = "config/vtest_regions.json"
RESULTS = "outputs/benchmarks.csv"
BASELINE = "outputs/baseline_events.csv"
MATCH_SECONDS = 1.0
ENTRY_SECONDS = 0.5  # zone-entry confirmation time, kept equal across frame steps


def match_events(found, baseline):
    """Return how many baseline events have a same-type event within MATCH_SECONDS."""
    unused = list(found)
    matched = 0
    for b in baseline:
        for f in unused:
            if f["event"] == b["event"] and abs(float(f["time"]) - float(b["time"])) <= MATCH_SECONDS:
                unused.remove(f)
                matched += 1
                break
    return matched


def benchmark_video(device, imgsz, frame_step):
    with open(REGIONS) as f:
        regions = json.load(f)
    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # min_frames counts processed frames. When skipping frames, fewer frames
    # are needed to cover the same 0.5 s, so scale it to keep the time equal.
    min_frames = max(1, round(ENTRY_SECONDS * fps / frame_step))
    detector = EventDetector(regions["zone"], regions["line"], min_frames=min_frames)

    model = YOLO("yolo26n.pt")
    ok, first = cap.read()
    # Warm-up: the first call loads weights onto the device and is much slower.
    model.predict(first, imgsz=imgsz, device=device, verbose=False)
    if device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    process = psutil.Process()
    peak_ram = process.memory_info().rss
    read_time = track_time = event_time = 0.0
    processed = 0
    events = []
    frame_number = 0
    start = time.perf_counter()

    while True:
        t0 = time.perf_counter()
        ok, frame = cap.read()
        t1 = time.perf_counter()
        read_time += t1 - t0
        if not ok:
            break
        if frame_number % frame_step == 0:
            result = model.track(
                frame, classes=[0], conf=0.25, imgsz=imgsz, device=device,
                verbose=False, persist=True, tracker="bytetrack.yaml",
            )[0]
            if device == "cuda":
                torch.cuda.synchronize()  # GPU work is asynchronous; wait so timing is real
            t2 = time.perf_counter()
            track_time += t2 - t1

            tracks = []
            if result.boxes.id is not None:
                for track_id, box in zip(result.boxes.id.int().tolist(), result.boxes.xyxy.tolist()):
                    tracks.append((track_id, "person", box))
            events += detector.update(frame_number / fps, tracks)
            event_time += time.perf_counter() - t2
            processed += 1
            peak_ram = max(peak_ram, process.memory_info().rss)
        frame_number += 1

    wall = time.perf_counter() - start
    cap.release()

    if not os.path.exists(BASELINE) and device == "cpu" and imgsz == 640 and frame_step == 1:
        with open(BASELINE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "track_id", "event", "class", "direction"])
            writer.writeheader()
            writer.writerows(events)
        print(f"Saved this run as the quality baseline: {BASELINE}")

    with open(BASELINE, newline="") as f:
        baseline = list(csv.DictReader(f))

    row = {
        "device": device,
        "imgsz": imgsz,
        "frame_step": frame_step,
        "processing_fps": round(frame_number / wall, 1),
        "x_real_time": round((frame_number / fps) / wall, 2),
        "track_ms_per_frame": round(1000 * track_time / processed, 1),
        "read_ms_per_frame": round(1000 * read_time / frame_number, 1),
        "event_ms_per_frame": round(1000 * event_time / processed, 2),
        "peak_ram_mb": round(peak_ram / 1e6),
        "peak_gpu_mb": round(torch.cuda.max_memory_allocated() / 1e6) if device == "cuda" else "",
        "entries": sum(e["event"] == "zone_entry" for e in events),
        "crossings": sum(e["event"] == "line_crossing" for e in events),
        "baseline_events_matched": f"{match_events(events, baseline)}/{len(baseline)}",
    }

    new_file = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new_file:
            writer.writeheader()
        writer.writerow(row)

    for key, value in row.items():
        print(f"{key:>24}: {value}")


def benchmark_speech(audio_path, runs=3):
    from faster_whisper import WhisperModel

    from ask_voice import MODEL_NAME, transcribe

    start = time.perf_counter()
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    load_seconds = time.perf_counter() - start

    times = []
    for _ in range(runs):
        start = time.perf_counter()
        transcript = transcribe(model, audio_path)
        times.append(time.perf_counter() - start)

    events = load_events("outputs/events.csv")
    occupancy = load_occupancy("outputs/occupancy.csv")
    regions = load_regions("outputs/analysis_info.json")
    start = time.perf_counter()
    for _ in range(1000):
        answer(transcript, events, occupancy, regions)
    answer_ms = (time.perf_counter() - start)  # total seconds for 1000 = ms per answer

    print(f'Transcript: "{transcript}"')
    print(f"Whisper model load: {load_seconds:.2f} s (once per session)")
    print(f"Transcription: {min(times):.2f}-{max(times):.2f} s over {runs} runs")
    print(f"Answering from saved data: {answer_ms:.3f} ms per question")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    video = sub.add_parser("video")
    video.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    video.add_argument("--imgsz", type=int, default=640, help="YOLO input size in pixels")
    video.add_argument("--frame-step", type=int, default=1, help="process every Nth frame")
    speech = sub.add_parser("speech")
    speech.add_argument("audio")
    args = parser.parse_args()

    if args.mode == "video":
        if args.device == "cuda" and not torch.cuda.is_available():
            parser.error("CUDA was requested but PyTorch can't see a GPU")
        benchmark_video(args.device, args.imgsz, args.frame_step)
    else:
        benchmark_speech(args.audio)


if __name__ == "__main__":
    main()
