"""SceneSift web interface: pick a video, place the zone and line, analyze, ask.

Usage (run from the project root):
    python src/app.py
Then use the page that opens in your browser (http://127.0.0.1:7860).
"""
import json
import os
from pathlib import Path

import cv2
import gradio as gr

from analyze_video import VIDEO_OUTPUT, analyze
from evidence import frame_at
from questions import answer, load_events, load_occupancy, parse_question

SAMPLE_DIR = Path("sample_videos")
CONFIG_DIR = Path("config")
MAX_EVIDENCE_FRAMES = 9
# Records which video and regions the current outputs were made from, so the
# app can refuse to answer from results that don't match the screen.
ANALYSIS_INFO = Path("outputs/analysis_info.json")

_whisper_model = None  # loaded the first time someone asks by voice


def regions_path(video_path):
    return CONFIG_DIR / f"{Path(video_path).stem}_regions.json"


def draw_regions(frame, regions):
    """Return a copy of the RGB frame with the zone and line drawn on it."""
    image = frame.copy()
    zone, line = regions["zone"], regions["line"]
    for x, y in zone:
        cv2.circle(image, (x, y), 5, (0, 255, 0), -1)
    if len(zone) >= 2:
        points = [tuple(p) for p in zone]
        for a, b in zip(points, points[1:] + points[:1] if len(zone) >= 3 else points[1:]):
            cv2.line(image, a, b, (0, 255, 0), 2)
    for (x, y), label in zip(line, "AB"):
        cv2.circle(image, (x, y), 5, (255, 0, 0), -1)
        cv2.putText(image, label, (x + 6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    if len(line) == 2:
        cv2.line(image, tuple(line[0]), tuple(line[1]), (255, 0, 0), 2)
    return image


def region_problem(regions):
    """Return why the zone and line can't be analyzed yet, or None if they can."""
    zone, line = len(regions["zone"]), len(regions["line"])
    if zone == 0 and line == 0:
        return "Place a zone, a line, or both."
    if 0 < zone < 3:
        return 'The zone needs at least 3 points. Select "Zone" and click more corners, or clear it.'
    if line == 1:
        return 'The line needs 2 points. Select "Line" and click its other end, or clear it.'
    return None


def checklist(regions):
    """Show what's placed. Each part is optional, but at least one is needed."""
    zone, line = len(regions["zone"]), len(regions["line"])

    def mark(count, needed):
        if count == 0:
            return "⬜ not set"
        return f"✅ {count} points" if count >= needed else f"❌ {count} of {needed}+ points"

    return (
        f"**Zone:** {mark(zone, 3)}  ·  **Line:** {mark(line, 2)}\n\n"
        "Each is optional: set a zone, a line, or both."
    )


def load_video(video_path):
    """Show the first frame and any saved zone and line for this video."""
    if not video_path:
        return None, None, {"zone": [], "line": []}, "Choose a video first."
    frame = frame_at(video_path, 0)
    if frame is None:
        return None, None, {"zone": [], "line": []}, f"Could not read {video_path}."
    saved = regions_path(video_path)
    if saved.exists():
        regions = json.loads(saved.read_text())
        status = f"Loaded the saved zone and line from `{saved}`."
    else:
        regions = {"zone": [], "line": []}
        status = "Click on the frame to place the zone and the line."
    return draw_regions(frame, regions), frame, regions, status + "\n\n" + checklist(regions)


def analyzed_with(video_path, regions):
    """Return True if the saved outputs came from this video and these regions."""
    if not ANALYSIS_INFO.exists():
        return False
    info = json.loads(ANALYSIS_INFO.read_text())
    return info == {"video": str(video_path), "regions": regions}


def change_note(video_path, regions):
    if ANALYSIS_INFO.exists() and not analyzed_with(video_path, regions):
        return "⚠️ The zone or line changed since the last analysis. Click **Analyze video** to update the results."
    return ""


def add_point(frame, regions, mode, video_path, evt: gr.SelectData):
    """Add the clicked point to the zone or the line."""
    if frame is None:
        return None, regions, "", ""
    x, y = int(evt.index[0]), int(evt.index[1])
    if mode == "Zone":
        regions["zone"].append([x, y])
    else:
        # A line has two points; a third click starts a new line.
        regions["line"] = (regions["line"] + [[x, y]])[-2:]
    return draw_regions(frame, regions), regions, checklist(regions), change_note(video_path, regions)


def clear(frame, regions, part, video_path):
    regions[part] = []
    image = draw_regions(frame, regions) if frame is not None else None
    return image, regions, checklist(regions), change_note(video_path, regions)


def run_analysis(video_path, regions, progress=gr.Progress()):
    if not video_path:
        return "Choose a video first."
    problem = region_problem(regions)
    if problem:
        return problem

    CONFIG_DIR.mkdir(exist_ok=True)
    regions_path(video_path).write_text(json.dumps(regions))

    def report(done, total):
        progress(done / total if total else 0, desc=f"Analyzing frame {done} of {total}")

    # analyze() also records the video and regions in outputs/analysis_info.json.
    summary = analyze(video_path, regions, progress=report)
    found = []
    if regions["zone"]:
        found.append(f"{summary['entries']} zone entries")
    if regions["line"]:
        found.append(f"{summary['crossings']} line crossings")
    return (f"Done on {summary['device'].upper()}: {summary['frames']} frames, "
            f"{', '.join(found)}. Now ask a question below.")


def transcribe_audio(audio_path):
    global _whisper_model
    from ask_voice import MODEL_NAME, transcribe  # imported here so typed questions start fast
    from faster_whisper import WhisperModel

    if _whisper_model is None:
        _whisper_model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    return transcribe(_whisper_model, audio_path)


def evidence_times(question, events):
    """Return (time, caption) pairs for the frames that support an answer."""
    kind, seconds = parse_question(question)
    if kind == "zone_entries":
        chosen = [e for e in events if e["event"] == "zone_entry"]
        return [(e["time"], f"{e['time']:.1f} s: ID {e['track_id']} entered") for e in chosen]
    if kind == "line_crossings":
        chosen = [e for e in events if e["event"] == "line_crossing"]
        return [
            (e["time"], f"{e['time']:.1f} s: ID {e['track_id']} crossed "
                        f"{e['direction'].replace('_', ' ')}")
            for e in chosen
        ]
    if kind == "occupancy" and seconds is not None:
        return [(seconds, f"{seconds:.1f} s")]
    return []


def ask(text, audio_path, video_path, regions):
    if not os.path.exists(VIDEO_OUTPUT) or not analyzed_with(video_path, regions):
        return "", ("The current video, zone, and line haven't been analyzed yet. "
                    "Click Analyze video first."), []

    if audio_path:
        question = transcribe_audio(audio_path)
        if not question:
            return "", "I didn't hear a question in that recording.", []
        heard = f'**Heard:** "{question}"'
    elif text and text.strip():
        question = text.strip()
        heard = f'**Question:** "{question}"'
    else:
        return "", "Type a question or record one.", []

    events = load_events("outputs/events.csv")
    occupancy = load_occupancy("outputs/occupancy.csv")
    reply = answer(question, events, occupancy, regions)

    times = evidence_times(question, events)
    if len(times) > MAX_EVIDENCE_FRAMES:
        reply += f"\n\n(Showing evidence for the first {MAX_EVIDENCE_FRAMES} of {len(times)}.)"
    gallery = []
    for seconds, caption in times[:MAX_EVIDENCE_FRAMES]:
        frame = frame_at(VIDEO_OUTPUT, seconds)
        if frame is not None:
            gallery.append((frame, caption))
    return heard, reply, gallery


def build_app():
    videos = sorted(str(p) for p in SAMPLE_DIR.iterdir() if p.suffix.lower() in (".avi", ".mp4", ".mov"))

    with gr.Blocks() as app:
        gr.Markdown("# SceneSift\nFind when people enter a zone or cross a line, then ask about it.")
        base_frame = gr.State(None)
        regions = gr.State({"zone": [], "line": []})

        gr.Markdown("## 1. Choose a video")
        video = gr.Dropdown(videos, value=videos[0] if videos else None, label="Video from sample_videos/")

        gr.Markdown("## 2. Place the zone and line\nPick what to place, then click on the frame.")
        mode = gr.Radio(["Zone", "Line"], value="Zone", label="Clicks add points to")
        with gr.Row():
            clear_zone = gr.Button("Clear zone")
            clear_line = gr.Button("Clear line")
        status = gr.Markdown()
        preview = gr.Image(label="Click to place points", interactive=False)

        gr.Markdown("## 3. Analyze")
        analyze_button = gr.Button("Analyze video", variant="primary")
        analysis_status = gr.Markdown()

        gr.Markdown("## 4. Ask a question")
        gr.Markdown(
            'Try: "When did someone enter the zone?", "When did someone cross the line?", '
            'or "How many people were in the zone at 10 seconds?"'
        )
        with gr.Row():
            question = gr.Textbox(label="Type a question")
            audio = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Or record one")
        ask_button = gr.Button("Ask", variant="primary")
        heard = gr.Markdown()
        reply = gr.Textbox(label="Answer", lines=3)
        gallery = gr.Gallery(label="Evidence frames", columns=3)

        video.change(load_video, video, [preview, base_frame, regions, status])
        app.load(load_video, video, [preview, base_frame, regions, status])
        preview.select(add_point, [base_frame, regions, mode, video], [preview, regions, status, analysis_status])
        clear_zone.click(
            lambda f, r, v: clear(f, r, "zone", v), [base_frame, regions, video],
            [preview, regions, status, analysis_status],
        )
        clear_line.click(
            lambda f, r, v: clear(f, r, "line", v), [base_frame, regions, video],
            [preview, regions, status, analysis_status],
        )
        analyze_button.click(run_analysis, [video, regions], analysis_status)
        ask_button.click(ask, [question, audio, video, regions], [heard, reply, gallery])

    return app


if __name__ == "__main__":
    build_app().launch(inbrowser=True)
