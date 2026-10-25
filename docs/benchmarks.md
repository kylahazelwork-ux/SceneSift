# Benchmarks (Step 11)

How fast SceneSift runs, where the time goes, and what one optimization
changed.

## Setup

- **Laptop:** Intel CPU (22 logical cores), 34 GB RAM, NVIDIA RTX 1000 Ada
  Laptop GPU (6 GB), Windows 11
- **Software:** Python 3.14, PyTorch 2.14.1 (CUDA 13.2 build), ultralytics
  8.4.184 with `yolo26n`, ByteTrack, faster-whisper 1.2.1 (`base.en`, int8)
- **Input:** `sample_videos/vtest.avi`, 768x576, 10 fps, 795 frames (79.5 s),
  zone and line from `config/vtest_regions.json`
- **Tool:** `src/benchmark.py`. Each setting was run twice; ranges show both
  runs. The model is warmed up before timing, and GPU timing waits for the
  GPU to finish each frame.

Run-to-run variation on this laptop is about 25% (heat, power mode,
background apps), so small differences aren't meaningful.

## Video pipeline: detection, tracking, and events

| Setting | Frames/s | vs. real time | Detect + track per frame | Peak RAM | Events matched vs. baseline |
|---|---|---|---|---|---|
| CPU, 640 px (baseline) | 10.5–13.3 | 1.1–1.3x | 72–92 ms | 815 MB | 39/39 |
| **GPU, 640 px (chosen)** | **18.7–21.6** | **1.9–2.2x** | **42–49 ms** | 1460 MB (+71 MB GPU) | **39/39** |
| CPU, 320 px input | 19.3–19.4 | 1.9x | 48 ms | 795 MB | 35/39 |
| CPU, every 2nd frame | 20.1–20.3 | 2.0x | 91–92 ms per processed frame | 816 MB | 33/39 |

"Events matched" counts baseline events with an event of the same type within
1 second. The baseline found 25 zone entries and 14 line crossings.

**End to end** (full `analyze()`, including drawing and writing the annotated
video): GPU 46–55 s vs. CPU 83 s, with identical events. Starting a new
terminal run adds about 5 s to load PyTorch and the GPU libraries.

### Where the time goes (CPU baseline, per frame)

| Stage | Time |
|---|---|
| Read frame | ~3 ms |
| Detection + tracking (YOLO + ByteTrack) | 72–92 ms |
| Event logic (zone and line checks) | 0.2 ms |

Detection and tracking are over 95% of the work, so that's the only place an
optimization makes a real difference.

## Speech and questions

| Measure | Time |
|---|---|
| Whisper model load (once per session) | 1.3 s |
| Transcribing a short spoken question | 1.0–2.5 s |
| Answering from saved events and occupancy | 0.02 ms |

For a spoken question, nearly all the wait is transcription. Answering is
instant because the video was already analyzed.

## The optimization: use the GPU automatically

`analyze_video.py` now runs YOLO on the GPU when PyTorch can see one, and
falls back to the CPU otherwise.

- **Improvement:** about 1.7x faster detection and tracking, and 1.5–1.8x
  faster end to end.
- **Quality:** unchanged. The same 25 entries and 14 crossings.
- **Cost:** about 650 MB more RAM for the GPU libraries, a few seconds of
  startup, and a large one-time install (the CUDA build of PyTorch is about
  2–3 GB).

**Why only 1.7x?** `yolo26n` is tiny, so the GPU sits mostly idle. Per-frame
costs that stay on the CPU (copying the image to the GPU, ByteTrack, drawing,
and Python overhead) limit the speed-up. A larger model would benefit more
from the GPU.

## Options considered but not chosen

- **320 px input:** about as fast as the GPU on any computer, but misses
  about 10% of events (4 of 39). Far-away people become too small to detect.
  Worth it only on a computer without a GPU where speed matters more than
  completeness.
- **Every 2nd frame:** similar speed to 320 px but loses more events (6 of
  39). Fast-moving people jump further between processed frames, so the
  tracker loses them. Zone-entry confirmation was kept at 0.5 s by halving
  `min_frames`, because that setting counts frames, not seconds.

## Reproduce

```powershell
python src/benchmark.py video --device cpu
python src/benchmark.py video --device cuda
python src/benchmark.py video --device cpu --imgsz 320
python src/benchmark.py video --device cpu --frame-step 2
python src/benchmark.py speech sample_audio/enter.m4a
```

The first CPU run at default settings saves `outputs/baseline_events.csv`,
which later runs are compared against. Results are appended to
`outputs/benchmarks.csv`.
