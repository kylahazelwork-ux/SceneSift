from events import EventDetector

ZONE = [(0, 0), (100, 0), (100, 100), (0, 100)]
LINE = [(200, 0), (200, 100)]  # vertical line at x = 200, A above B


def box_at(x, y):
    """A 10-pixel-wide box whose bottom-middle point is (x, y)."""
    return (x - 5, y - 40, x + 5, y)


def test_entry_when_moving_from_outside_to_inside():
    detector = EventDetector(ZONE, LINE, min_frames=1)
    assert detector.update(0.0, [(1, "person", box_at(150, 50))]) == []
    events = detector.update(0.1, [(1, "person", box_at(50, 50))])
    assert len(events) == 1
    assert events[0]["event"] == "zone_entry"
    assert events[0]["track_id"] == 1
    assert events[0]["time"] == 0.1


def test_no_repeat_entry_while_staying_inside():
    detector = EventDetector(ZONE, LINE, min_frames=1)
    detector.update(0.0, [(1, "person", box_at(150, 50))])
    detector.update(0.1, [(1, "person", box_at(50, 50))])
    assert detector.update(0.2, [(1, "person", box_at(60, 50))]) == []


def test_no_entry_when_first_seen_inside():
    detector = EventDetector(ZONE, LINE)
    assert detector.update(0.0, [(1, "person", box_at(50, 50))]) == []


def test_line_crossing_left_to_right():
    detector = EventDetector(ZONE, LINE)
    detector.update(0.0, [(1, "person", box_at(190, 50))])
    events = detector.update(0.1, [(1, "person", box_at(210, 50))])
    assert len(events) == 1
    assert events[0]["event"] == "line_crossing"
    assert events[0]["direction"] == "left_to_right"


def test_line_crossing_right_to_left():
    detector = EventDetector(ZONE, LINE)
    detector.update(0.0, [(1, "person", box_at(210, 50))])
    events = detector.update(0.1, [(1, "person", box_at(190, 50))])
    assert events[0]["direction"] == "right_to_left"


def test_jitter_at_edge_does_not_create_entry():
    detector = EventDetector(ZONE, LINE)  # default: 5 frames in a row
    events = []
    # Foot point wobbles across the zone's right edge (x = 100) every frame.
    for i, x in enumerate([102, 98, 102, 98, 99, 102, 98]):
        events += detector.update(i / 10, [(1, "person", box_at(x, 50))])
    assert events == []


def test_entry_after_min_frames_inside_reports_confirmation_time():
    detector = EventDetector(ZONE, LINE, min_frames=3)
    detector.update(0.0, [(1, "person", box_at(150, 50))])  # outside
    assert detector.update(0.1, [(1, "person", box_at(90, 50))]) == []
    assert detector.update(0.2, [(1, "person", box_at(80, 50))]) == []
    events = detector.update(0.3, [(1, "person", box_at(70, 50))])
    assert len(events) == 1
    assert events[0]["time"] == 0.3  # when the entry was confirmed


def test_entry_and_occupancy_agree():
    # Regression test: an entry must be counted as inside in the same frame,
    # or "when did they enter?" and "how many were inside?" contradict.
    detector = EventDetector(ZONE, LINE, min_frames=3)
    detector.update(0.0, [(1, "person", box_at(150, 50))])
    for i, x in enumerate([90, 80, 70], start=1):
        events = detector.update(i / 10, [(1, "person", box_at(x, 50))])
        assert detector.was_inside[1] == bool(events)
