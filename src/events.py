"""Turn tracked people into zone-entry and line-crossing events."""
from geometry import bottom_middle, crosses_segment, point_in_zone, side_of_line


class EventDetector:
    """Remembers each track between frames and reports new events.

    Call update() once per frame, in order.
    """

    def __init__(self, zone, line, min_frames=5):
        self.zone = zone
        self.line_a, self.line_b = line
        # A zone change only counts after this many frames in a row on the new
        # side. This stops boxes that jitter across the edge from creating entries.
        self.min_frames = min_frames
        self.last_point = {}  # track_id -> bottom-middle point in the previous frame
        self.was_inside = {}  # track_id -> confirmed inside the zone?
        self.pending = {}     # track_id -> (frames on the new side, time it started)

    def update(self, timestamp, tracks):
        """Process one frame and return a list of events that happened in it.

        tracks is a list of (track_id, class_name, box) tuples, where box is
        (x1, y1, x2, y2).
        """
        events = []

        for track_id, class_name, box in tracks:
            point = bottom_middle(box)
            inside = point_in_zone(point, self.zone)

            # Zone entry: confirmed outside, then inside for min_frames in a row.
            confirmed = self.was_inside.get(track_id)
            if confirmed is None:
                # First sighting: accept the current side without an event
                # (someone first detected inside doesn't count as entering).
                self.was_inside[track_id] = inside
            elif inside == confirmed:
                # Back on the confirmed side: cancel any change in progress.
                self.pending.pop(track_id, None)
            else:
                # On the other side: count frames in a row.
                count, start_time = self.pending.get(track_id, (0, timestamp))
                count += 1
                if count < self.min_frames:
                    self.pending[track_id] = (count, start_time)
                else:
                    # Stayed long enough, so the change is real.
                    self.was_inside[track_id] = inside
                    self.pending.pop(track_id, None)
                    if inside:
                        events.append({
                            # Report when they stepped in, not when it was confirmed.
                            "time": round(start_time, 2),
                            "track_id": track_id,
                            "event": "zone_entry",
                            "class": class_name,
                            "direction": None,
                        })

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
