"""Answer typed questions using saved events and occupancy, without the video.

Supported questions:
    "When did someone enter the zone?"
    "When did someone cross the line?"
    "How many people were in the zone at 10 seconds?"
"""
import csv
import json
import re

UNSUPPORTED = (
    "Sorry, I can't answer that yet. Try:\n"
    '  "When did someone enter the zone?"\n'
    '  "When did someone cross the line?"\n'
    '  "How many people were in the zone at 10 seconds?"'
)


def load_events(path):
    """Read events.csv into a list of dicts with numbers converted."""
    with open(path, newline="") as f:
        return [
            {**row, "time": float(row["time"]), "track_id": int(row["track_id"])}
            for row in csv.DictReader(f)
        ]


def load_occupancy(path):
    """Read occupancy.csv into a list of (time, people_in_zone) tuples."""
    with open(path, newline="") as f:
        return [(float(row["time"]), int(row["people_in_zone"])) for row in csv.DictReader(f)]


def parse_time(text):
    """Find a time in the text, like "10 seconds", "10.5 s", or "0:30".

    Returns seconds as a float, or None if there's no time.
    """
    # "1:05" means 1 minute 5 seconds.
    match = re.search(r"(\d+):(\d{2})", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    # A number followed by "s", "sec", "second", or "seconds".
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b", text)
    if match:
        return float(match.group(1))
    return None


def parse_question(text):
    """Work out which question was asked.

    Returns (kind, time) where kind is "zone_entries", "line_crossings",
    "occupancy", or None if the question isn't supported.
    """
    text = text.lower()
    if "how many" in text and "zone" in text:
        return "occupancy", parse_time(text)
    if "enter" in text and "zone" in text:
        return "zone_entries", None
    if "cross" in text and "line" in text:
        return "line_crossings", None
    return None, None


def answer_zone_entries(events):
    """Answer "When did someone enter the zone?"."""
    entries = [e for e in events if e["event"] == "zone_entry"]
    if not entries:
        return "No one entered the zone."
    parts = [f"{e['time']:.1f} s (ID {e['track_id']})" for e in entries]
    return f"{len(entries)} zone entries: " + ", ".join(parts)


def answer_line_crossings(events):
    """Answer "When did someone cross the line?"."""
    crossings = [e for e in events if e["event"] == "line_crossing"]
    if not crossings:
        return "No one crossed the line."
    parts = [
        f"{e['time']:.1f} s (ID {e['track_id']}, {e['direction'].replace('_', ' ')})"
        for e in crossings
    ]
    return f"{len(crossings)} line crossings: " + ", ".join(parts)


def answer_occupancy(occupancy, seconds):
    """Answer "How many people were in the zone at <time>?"."""
    if seconds is None:
        return 'Please include a time, like "at 10 seconds" or "at 0:30".'
    video_end = occupancy[-1][0]
    if seconds < 0 or seconds > video_end:
        return f"That time is outside the video, which is {video_end:.1f} s long."
    # Use the recorded frame closest to the requested time.
    time, count = min(occupancy, key=lambda row: abs(row[0] - seconds))
    person = "person was" if count == 1 else "people were"
    return f"{count} {person} in the zone at {time:.1f} s."


def load_regions(path):
    """Read which zone and line the analysis used, or None if unknown."""
    try:
        with open(path) as f:
            return json.load(f)["regions"]
    except FileNotFoundError:
        return None


def answer(question, events, occupancy, regions=None):
    """Return a text answer to a typed question.

    regions, if given, is the zone and line the analysis used. It lets the
    answer say "no line was set" instead of a misleading "no one crossed".
    """
    kind, seconds = parse_question(question)
    if regions is not None:
        if kind in ("zone_entries", "occupancy") and not regions.get("zone"):
            return "No zone was set for this analysis, so I can't answer questions about a zone."
        if kind == "line_crossings" and not regions.get("line"):
            return "No line was set for this analysis, so I can't answer questions about a line."
    if kind == "zone_entries":
        return answer_zone_entries(events)
    if kind == "line_crossings":
        return answer_line_crossings(events)
    if kind == "occupancy":
        return answer_occupancy(occupancy, seconds)
    return UNSUPPORTED
