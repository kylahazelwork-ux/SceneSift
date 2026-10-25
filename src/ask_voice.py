"""Ask SceneSift a spoken question from an audio recording.

Transcribes the recording with faster-whisper, then answers the text with the
same logic as ask.py.

Usage (run from the project root, after analyze_video.py):
    python src/ask_voice.py sample_audio/question.m4a
"""
import sys
import time

from faster_whisper import WhisperModel

from questions import answer, load_events, load_occupancy

# "base.en" is a small English-only model: fast on a CPU, good enough for
# short, clear questions. The first run downloads it (about 150 MB).
MODEL_NAME = "base.en"


def transcribe(model, audio_path):
    """Return the text spoken in the audio file."""
    # transcribe() returns a generator: the work happens as we read segments.
    segments, _info = model.transcribe(audio_path, language="en")
    return " ".join(segment.text.strip() for segment in segments)


def main():
    if len(sys.argv) != 2:
        print("Usage: python src/ask_voice.py <path-to-audio-file>")
        sys.exit(1)
    audio_path = sys.argv[1]

    try:
        events = load_events("outputs/events.csv")
        occupancy = load_occupancy("outputs/occupancy.csv")
    except FileNotFoundError:
        print("No analysis found. Run analyze_video.py first.")
        sys.exit(1)

    # int8 stores the model's numbers in a smaller format, which runs faster
    # on a CPU with almost no loss in accuracy.
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")

    start = time.perf_counter()
    try:
        transcript = transcribe(model, audio_path)
    except Exception as error:
        print(f"Error: could not transcribe {audio_path}: {error}")
        sys.exit(1)
    seconds = time.perf_counter() - start

    if not transcript:
        print("I didn't hear a question in that recording.")
        sys.exit(1)

    print(f'Heard: "{transcript}"  (transcribed in {seconds:.1f} s)')
    print(answer(transcript, events, occupancy))


if __name__ == "__main__":
    main()
