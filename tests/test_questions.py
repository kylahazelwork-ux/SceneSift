from questions import answer, parse_question, parse_time

EVENTS = [
    {"time": 16.1, "track_id": 37, "event": "zone_entry", "class": "person", "direction": ""},
    {"time": 18.5, "track_id": 31, "event": "line_crossing", "class": "person",
     "direction": "right_to_left"},
    {"time": 22.4, "track_id": 56, "event": "zone_entry", "class": "person", "direction": ""},
]
OCCUPANCY = [(0.0, 2), (0.1, 1), (10.0, 3), (10.1, 0)]


def test_parse_question_types():
    assert parse_question("When did someone enter the zone?") == ("zone_entries", None)
    assert parse_question("When did someone CROSS the line?") == ("line_crossings", None)
    assert parse_question("How many people were in the zone at 10 seconds?") == ("occupancy", 10.0)
    assert parse_question("What's the weather?") == (None, None)


def test_parse_time_formats():
    assert parse_time("at 10 seconds") == 10.0
    assert parse_time("at 10.5 s") == 10.5
    assert parse_time("at 0:30") == 30
    assert parse_time("at 1:05") == 65
    assert parse_time("no time here") is None


def test_answer_zone_entries():
    assert answer("When did someone enter the zone?", EVENTS, OCCUPANCY) == (
        "2 zone entries: 16.1 s (ID 37), 22.4 s (ID 56)"
    )


def test_answer_zone_entries_when_none():
    assert answer("When did someone enter the zone?", [], OCCUPANCY) == "No one entered the zone."


def test_answer_line_crossings():
    assert answer("When did someone cross the line?", EVENTS, OCCUPANCY) == (
        "1 line crossings: 18.5 s (ID 31, right to left)"
    )


def test_answer_occupancy():
    assert answer("How many people were in the zone at 10 seconds?", EVENTS, OCCUPANCY) == (
        "3 people were in the zone at 10.0 s."
    )


def test_answer_occupancy_outside_video():
    assert "outside the video" in answer("How many in the zone at 99 seconds?", EVENTS, OCCUPANCY)


def test_unsupported_question():
    assert answer("Who is the tallest person?", EVENTS, OCCUPANCY).startswith("Sorry")
