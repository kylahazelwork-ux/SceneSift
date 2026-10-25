"""Ask SceneSift questions about an analyzed video.

Run analyze_video.py first. Then either ask one question:
    python src/ask.py "When did someone enter the zone?"
or start an interactive session (type "quit" to stop):
    python src/ask.py
"""
import sys

from questions import answer, load_events, load_occupancy

EVENTS = "outputs/events.csv"
OCCUPANCY = "outputs/occupancy.csv"


def main():
    try:
        events = load_events(EVENTS)
        occupancy = load_occupancy(OCCUPANCY)
    except FileNotFoundError:
        print("No analysis found. Run analyze_video.py first.")
        sys.exit(1)

    if len(sys.argv) > 1:
        print(answer(" ".join(sys.argv[1:]), events, occupancy))
        return

    while True:
        question = input("\nAsk a question (or 'quit'): ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if question:
            print(answer(question, events, occupancy))


if __name__ == "__main__":
    main()
