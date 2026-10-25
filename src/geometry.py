"""Geometry helpers for turning tracked boxes into zone and line events.

Points are (x, y) pixel coordinates. y increases downward.
"""
import cv2
import numpy as np


def bottom_middle(box):
    """Return the bottom-middle point of a box given as (x1, y1, x2, y2).

    (x1, y1) is the top-left corner and (x2, y2) is the bottom-right corner.
    """
    return (box[0] + box[2]) / 2, box[3]


def point_in_zone(point, zone):
    """Return True if the point is inside the zone polygon (or on its edge)."""
    polygon = np.array(zone, dtype=np.float32)
    # pointPolygonTest returns > 0 inside, 0 on the edge, < 0 outside.
    return cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0


def side_of_line(point, a, b):
    """Return which side of the line from a to b the point is on.

    Positive on one side, negative on the other, 0 exactly on the line.
    This is the 2D cross product of (b - a) and (point - a).
    """
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def crosses_segment(p_prev, p_now, a, b):
    """Return True if moving from p_prev to p_now passes through segment a-b.

    Both conditions must hold:
    - p_prev and p_now are on opposite sides of the line through a and b.
    - a and b are on opposite sides of the path from p_prev to p_now,
      so the crossing happens within the segment, not past its ends.
    """
    person_sides = side_of_line(p_prev, a, b) * side_of_line(p_now, a, b)
    segment_sides = side_of_line(a, p_prev, p_now) * side_of_line(b, p_prev, p_now)
    return person_sides < 0 and segment_sides < 0
