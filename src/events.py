"""Turn tracked people into zone-entry and line-crossing events."""
from geometry import bottom_middle, crosses_segment, point_in_zone, side_of_line


class EventDetector:
    """Remembers each track between frames and reports new events.

    The zone and the line are each optional (pass None or an empty list to
    skip one). Call update() once per frame, in order.
    """

    def __init__(self, zone, line, min_frames=5):
        self.zone = zone or None
        self.line = line or None
        # A zone change only counts after this many frames in a row on the new
        # side. This stops boxes that jitter across the edge from creating entries.
        self.min_frames = min_frames
        self.last_point = {}  # track_id -> bottom-middle point in the previous frame
        self.was_inside = {}  # track_id -> confirmed inside the zone?
        self.pending = {}     # track_id -> frames in a row on the new side

    def update(self, timestamp, tracks):
        """Process one frame and return a list of events that happened in it.

        tracks is a list of (track_id, class_name, box) tuples, where box is
        (x1, y1, x2, y2).
        """
        events = []
        for track_id, class_name, box in tracks:
            point = bottom_middle(box)
            if self.zone:
                events += self._check_zone(timestamp, track_id, class_name, point)
            if self.line:
                events += self._check_line(timestamp, track_id, class_name, point)
            self.last_point[track_id] = point
        return events

    def in_zone_count(self, tracks):
        """Number of these tracks confirmed inside the zone (0 if no zone)."""
        return sum(self.was_inside.get(track_id, False) for track_id, _, _ in tracks)

    def _check_zone(self, timestamp, track_id, class_name, point):
        """Zone entry: confirmed outside, then inside for min_frames in a row."""
        inside = point_in_zone(point, self.zone)
        confirmed = self.was_inside.get(track_id)
        if confirmed is None:
            # First sighting: accept the current side without an event
            # (someone first detected inside doesn't count as entering).
            self.was_inside[track_id] = inside
            return []
        if inside == confirmed:
            # Back on the confirmed side: cancel any change in progress.
            self.pending.pop(track_id, None)
            return []

        # On the other side: count frames in a row.
        count = self.pending.get(track_id, 0) + 1
        if count < self.min_frames:
            self.pending[track_id] = count
            return []

        # Stayed long enough, so the change is real.
        self.was_inside[track_id] = inside
        self.pending.pop(track_id, None)
        if not inside:
            return []
        return [{
            # Report the confirmation time, so entries always agree with
            # occupancy (which uses confirmed state).
            "time": round(timestamp, 2),
            "track_id": track_id,
            "event": "zone_entry",
            "class": class_name,
            "direction": None,
        }]

    def _check_line(self, timestamp, track_id, class_name, point):
        """Line crossing: the path from the previous point passes through the line."""
        if track_id not in self.last_point:
            return []
        prev = self.last_point[track_id]
        a, b = self.line
        if not crosses_segment(prev, point, a, b):
            return []
        # With A drawn above B, side_of_line is positive on the left of the
        # screen and negative on the right.
        direction = "left_to_right" if side_of_line(prev, a, b) > 0 else "right_to_left"
        return [{
            "time": round(timestamp, 2),
            "track_id": track_id,
            "event": "line_crossing",
            "class": class_name,
            "direction": direction,
        }]
