# SceneSift

SceneSift is a video explorer that detects and tracks people in a prerecorded
video, records when they enter a marked zone or cross a line, and answers
questions about those events with timestamps and video evidence.

## Version 1 scope

**Supports:**
- One prerecorded video at a time
- Detecting and tracking people
- One zone (a marked area) and one line
- Three question types:
  1. Zone entries — "When did someone enter the zone?"
  2. Line crossings — "How many people crossed the line?"
  3. Person counts — "How many people were in the zone at 0:30?"
- Answers include timestamps and a matching frame or short clip

**Not in version 1:**
- Live camera streams
- Multiple zones or lines
- Objects other than people

## Definitions 

- **A person “enters the zone” when:** The bottom-middle of their bounding box moves from outside the marked zone to inside it. Count one entry per transition, not once per frame. Someone first detected inside does not count as an entry.

- **A person “crosses the line” when:** The same tracked person’s bottom-middle point moves from one side of the marked line to the other, passing through the line segment. Record the direction so crossings in opposite directions can be distinguished.

- **“Person count” means:** The number of people whose bottom-middle points are inside the marked zone at a specified video timestamp, rather than the total number of different people across the video.

## Setup (Windows, PowerShell)

Requires Python 3.12 or newer and Git.

```powershell
git clone https://github.com/kylahazelwork-ux/SceneSift.git
cd SceneSift
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If activation fails with "running scripts is disabled", run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

Optional, for an NVIDIA GPU: install the CUDA build of PyTorch. SceneSift uses
the GPU automatically when PyTorch can see one (about 1.7x faster; see
`docs/benchmarks.md`). Pick the build that matches the CUDA version shown by
`nvidia-smi`, for example:

```powershell
python -m pip install --force-reinstall --no-deps torch==2.14.1+cu132 torchvision==0.29.1+cu132 --index-url https://download.pytorch.org/whl/cu132
```

Download the sample video (videos are not stored in Git):

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/vtest.avi -OutFile sample_videos\vtest.avi
```

## Usage

Print a video's resolution, frame rate, and duration, and save its first frame
to `outputs/frame.jpg`:

```powershell
python src/video_info.py sample_videos/vtest.avi
```

Detect people in every frame and save an annotated video to
`outputs/detected.mp4` (boxes, confidence scores, and timestamps):

```powershell
python src/detect_video.py sample_videos/vtest.avi
```

The first run downloads the YOLO model weights (`yolo26n.pt`, about 5 MB).

Analyze a video: track people, record zone entries and line crossings, and save
`outputs/events.csv`, `outputs/occupancy.csv`, and an annotated
`outputs/analyzed.mp4`. The zone and line come from a JSON file:

```powershell
python src/analyze_video.py sample_videos/vtest.avi config/vtest_regions.json
```

Ask questions about the analyzed video (answers come from the saved files, so
the video isn't processed again):

```powershell
python src/ask.py "When did someone enter the zone?"
python src/ask.py "When did someone cross the line?"
python src/ask.py "How many people were in the zone at 0:23?"
python src/ask.py    # interactive mode; type "quit" to stop
```

Run the tests:

```powershell
python -m pytest
```

Ask a spoken question from an audio recording (transcribed locally with
faster-whisper; the first run downloads the `base.en` model, about 150 MB):

```powershell
python src/ask_voice.py sample_audio/question.m4a
```

Record questions with the Windows Sound Recorder app and save them in
`sample_audio/`. Recordings are not stored in Git.
