from events import EventDetector

ZONE = [(0, 0), (100, 0), (100, 100), (0, 100)]
LINE = [(200, 0), (200, 100)]  # vertical line at x = 200, A above B


def box_at(x, y):
    """A 10-pixel-wide box whose bottom-middle point is (x, y)."""
    return (x - 5, y - 40, x + 5, y)


def test_entry_when_moving_from_outside_to_inside():
    detector = EventDetector(ZONE, LINE)
    assert detector.update(0.0, [(1, "person", box_at(150, 50))]) == []
    events = detector.update(0.1, [(1, "person", box_at(50, 50))])
    assert len(events) == 1
    assert events[0]["event"] == "zone_entry"
    assert events[0]["track_id"] == 1
    assert events[0]["time"] == 0.1


def test_no_repeat_entry_while_staying_inside():
    detector = EventDetector(ZONE, LINE)
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
