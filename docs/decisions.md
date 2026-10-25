# Design decisions

A log of the choices made while building SceneSift: what was chosen, why,
and what was rejected. Newest entries go at the bottom.

Each entry answers:
- **Decision:** what I chose
- **Why:** the reason
- **Alternatives:** what I considered and why I didn't pick it
- **Revisit if:** what would make me change my mind

---

## 1. Use the bottom-middle of the bounding box as a person's position

- **Decision:** A person's location is the bottom-middle point of their
  detection box.
- **Why:** That point is roughly where their feet touch the ground. Zones and
  lines are drawn on the floor, so foot position decides whether someone is
  really inside the zone.
- **Alternatives:** The box center sits around waist height. With an angled
  camera, it can look like it's inside a floor zone when the person is
  actually standing in front of it.
- **Revisit if:** People are often partly hidden at the bottom (for example,
  behind a table), so their feet aren't visible.

## 2. Count zone entries on transitions, not frames

- **Decision:** An entry is recorded only when a tracked person's position
  changes from outside the zone to inside it. Someone who is already inside
  when they're first detected doesn't count as entering.
- **Why:** The video has 10 frames per second. Counting every frame a person
  is inside would turn one person standing in the zone for 3 seconds into 30
  entries.
- **Alternatives:** Counting frames inside the zone answers "how long was the
  zone occupied?", which is a different question.
- **Revisit if:** Detection boxes jitter near the zone edge and cause the
  point to flicker in and out, producing false entries. The likely fix is
  requiring the point to stay inside for several frames before counting it.

## 3. Define person count as zone occupancy at a moment in time

- **Decision:** "How many people?" means how many people are inside the zone
  at a specific timestamp.
- **Why:** Occupancy only needs the detections in one frame. Counting total
  unique visitors depends on track IDs staying correct for the whole video,
  and IDs often break when people overlap or are briefly hidden.
- **Alternatives:** Counting unique track IDs across the video. It's useful,
  but it would overcount every time the tracker lost a person and gave them
  a new ID.
- **Revisit if:** Tracking proves reliable enough in Step 7 to support a
  "total visitors" question.

## 4. Keep videos, outputs, and model weights out of Git

- **Decision:** `.gitignore` excludes sample videos, generated outputs, and
  `.pt` model files. The README explains how to download them instead.
- **Why:** Git stores every version of every file forever. Large binary files
  would permanently bloat the repository and slow down every clone, even if
  they were deleted later.
- **Alternatives:** Git LFS (Large File Storage) can store big files outside
  normal history. It adds setup and has storage limits, which is more than
  this project needs.
- **Revisit if:** The project needs custom test videos or trained models that
  can't be downloaded from a public source.

## 5. Check OpenCV return values explicitly

- **Decision:** Every OpenCV call that can fail is checked (`isOpened()`,
  `read()`'s `ok` flag, `imwrite`'s return value), and the program stops
  with a clear message if it fails.
- **Why:** OpenCV fails silently. Opening a missing file or saving to a
  folder that doesn't exist returns `False` instead of raising an error.
  Without checks, the program would continue and fail later in a confusing
  way.
- **Alternatives:** Relying on Python exceptions. That doesn't work here,
  because OpenCV doesn't raise them for these failures.
- **Revisit if:** The checks get repeated in many scripts. Then they should
  move into shared helper functions.

## 6. Use a pretrained YOLO nano model (`yolo26n`)

- **Decision:** Detect people with the smallest pretrained YOLO model,
  filtered to the "person" class, with the default confidence threshold of
  0.25.
- **Why:** A pretrained model already recognizes people, so no training is
  needed. The nano size runs faster than real time on a CPU: about 52 seconds
  for the 79.5-second sample video.
- **Alternatives:** Larger YOLO models (small, medium) are more accurate but
  slower. Training a custom model would need labeled data and isn't needed
  to detect people.
- **Revisit if:** Step 7 shows many missed people (for example, small or
  partly hidden people far from the camera). Then compare a larger model or
  adjust the confidence threshold.

## 7. Place the zone and line away from the lamppost and frame edges

- **Decision:** For `vtest.avi`, the zone is a section of road to the right of
  the lamppost, and the line crosses the walkway on the left. Positions are
  stored in `config/vtest_regions.json`.
- **Why:** Tracking IDs often break near the lamppost and at the frame edges
  (see `tracking_errors.md`). Keeping the zone and line away from those spots
  reduces missed entries and crossings, while still covering places where
  people walk.
- **Alternatives:** Hard-coding the coordinates in Python. Storing them in a
  JSON file means each video can have its own regions, and the interface in
  Step 10 can save them without code changes.
- **Revisit if:** Step 7 shows many missed events, or a different video is
  used.

## 8. Require 5 frames inside before counting a zone entry

- **Decision:** A zone entry only counts after the person's foot point stays
  inside for 5 frames in a row (0.5 s at 10 fps). The reported time is the
  first of those frames.
- **Why:** The Step 7 review showed people near the zone edge creating
  entries without walking in, because their boxes jitter. Testing 1, 3, 5,
  10, and 15 frames showed 5 removed the questionable entries in the reviewed
  window without losing real ones (see `event_review.md`).
- **Alternatives:** 3 frames barely helped. 15 frames started dropping real
  entries.
- **Revisit if:** The video has a different frame rate. The setting is in
  frames, so the same value means a different amount of time at 30 fps.
  Converting it to seconds would make it independent of frame rate.
