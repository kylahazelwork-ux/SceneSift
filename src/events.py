"""Turn tracked people into zone-entry and line-crossing events."""
from geometry import bottom_middle, crosses_segment, point_in_zone, side_of_line


class EventDetector:
    """Remembers each track between frames and reports new events.

    Call update() once per frame, in order.
    """

    def __init__(self, zone, line):
        self.zone = zone
        self.line_a, self.line_b = line
        self.last_point = {}  # track_id -> bottom-middle point in the previous frame
        self.was_inside = {}  # track_id -> was that point inside the zone?

    def update(self, timestamp, tracks):
        """Process one frame and return a list of events that happened in it.

        tracks is a list of (track_id, class_name, box) tuples, where box is
        (x1, y1, x2, y2).
        """
        events = []

        for track_id, class_name, box in tracks:
            point = bottom_middle(box)
            inside = point_in_zone(point, self.zone)

            # Zone entry: outside in the previous frame, inside now.
            # A track seen for the first time has no previous frame, so it
            # can't enter (someone first detected inside doesn't count).
            if inside and self.was_inside.get(track_id) is False:
                events.append({
                    "time": round(timestamp, 2),
                    "track_id": track_id,
                    "event": "zone_entry",
                    "class": class_name,
                    "direction": None,
                })

            self.was_inside[track_id] = inside

            # Line crossing: the path from the previous point to this one
            # passes through the line segment.
            if track_id in self.last_point:
                prev = self.last_point[track_id]
                if crosses_segment(prev, point, self.line_a, self.line_b):
                    # With A drawn above B, side_of_line is positive on the
                    # left of the screen and negative on the right.
                    if side_of_line(prev, self.line_a, self.line_b) > 0:
                        direction = "left_to_right"
                    else:
                        direction = "right_to_left"
                    events.append({
                        "time": round(timestamp, 2),
                        "track_id": track_id,
                        "event": "line_crossing",
                        "class": class_name,
                        "direction": direction,
                    })

            self.last_point[track_id] = point

        return events
