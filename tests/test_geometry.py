from geometry import bottom_middle, crosses_segment, point_in_zone, side_of_line

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_bottom_middle():
    assert bottom_middle((10, 20, 30, 80)) == (20, 80)


def test_point_in_zone_inside_and_outside():
    assert point_in_zone((5, 5), SQUARE)
    assert not point_in_zone((15, 5), SQUARE)


def test_side_of_line_opposite_signs():
    a, b = (0, 0), (0, 10)  # a vertical line
    assert side_of_line((-5, 5), a, b) * side_of_line((5, 5), a, b) < 0


def test_crosses_segment_through_middle():
    assert crosses_segment((-5, 5), (5, 5), (0, 0), (0, 10))


def test_does_not_cross_past_end_of_segment():
    # Same sideways move, but below the bottom end of the segment.
    assert not crosses_segment((-5, 20), (5, 20), (0, 0), (0, 10))


def test_does_not_cross_when_staying_on_one_side():
    assert not crosses_segment((-5, 2), (-1, 8), (0, 0), (0, 10))
