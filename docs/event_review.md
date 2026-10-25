# Event review (Step 7)

I checked the program's events against the video by eye, to find out which
events are real, which are false, and why.

## Method

- **Window:** 15–35 s of `sample_videos/vtest.avi` (20 seconds, 15 events).
- **Setup:** `yolo26n`, ByteTrack defaults, zone and line from
  `config/vtest_regions.json`.
- **Process:** `src/review_events.py` saves one image per event showing the
  annotated video 0.5 s before, at, and 0.5 s after the event. I marked each
  one as real, edge case, or unsure.

```powershell
python src/analyze_video.py sample_videos/vtest.avi config/vtest_regions.json
python src/review_events.py 15 35
```

## Results

| Verdict | Count | Events |
|---|---|---|
| Real: the person clearly entered or crossed | 9 | 2, 4, 5, 6, 7, 10, 11, 14, 15 |
| Edge case: the person was hovering at the boundary | 5 | 3, 8, 9, 12, 13 |
| Unsure: overlapping labels, unclear which person | 1 | 1 |

**9 of 15 events (60%) were clearly correct.** Missed events (people who
entered or crossed without an event) were not checked in this pass.

## What it gets right

- People who walk clearly into the zone or across the line are detected,
  with the right ID and direction.
- No events came from non-people (the detector only tracks people).
- Someone already inside the zone when first detected does not create an
  entry, as designed.

## Where it fails

### 1. People standing on the zone edge create entries

![ID 6 group standing on the zone edge, 22.3–23.3 s](images/review_zone_edge_22s.jpg)

At 22.8 s, a group of people is standing still on the top edge of the zone.
Their foot points wobble a few pixels across the edge, so "in zone" jumps
from 0 to 3 and entries are recorded even though nobody walked in. ID 6
produced 5 entries over the whole video this way (4.2, 9.3, 14.7, 16.3, and
22.8 s).

### 2. A person who stops at the line and turns back creates two crossings

![ID 56 at the line, 31.1–32.1 s](images/review_line_turnaround_31s.jpg)

ID 56 walks up to the line, pauses on it, and turns around. The foot point
crosses the line and comes back, giving a `right_to_left` crossing at 31.3 s
and a `left_to_right` crossing at 31.6 s.

### 3. Overlapping people make IDs hard to verify

Event 1 is an entry for ID 7, but the labels overlap so much that the person
appears to be ID 33. This is the same tracking problem described in
`tracking_errors.md`.

## Why it fails

The code follows the event rules exactly. The problem is the rules: a single
frame on the other side of an edge counts as an event, with no tolerance.
Detection boxes jitter by a few pixels every frame, so anyone close to an
edge can trigger events without moving. This was predicted in decision #2.

## Possible fixes (not done yet)

- **Require several frames:** only count an entry after the foot point stays
  inside for, say, 3 frames (0.3 s at 10 fps).
- **Add a buffer band:** for the line, only count a crossing once the person
  is clearly past it (a few pixels beyond), not just touching it.
- **Ignore quick reversals:** don't count a crossing that is undone within a
  short time.

Each fix trades responsiveness for stability: it removes false events but
adds a small delay, and could miss someone who steps in and out quickly.
