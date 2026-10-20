# SceneSift

SceneSift is a video explorer that detects and tracks people in a prerecorded
video, records when they enter a marked zone or cross a line, and answers
questions about those events with timestamps and video evidence.

## Version 1 scope

**Supports:**
- One prerecorded video at a time
- Detecting and tracking people
- One zone (a marked area) and one line
- Three question types:
  1. Zone entries — "When did someone enter the zone?"
  2. Line crossings — "How many people crossed the line?"
  3. Person counts — "How many people were in the zone at 0:30?"
- Answers include timestamps and a matching frame or short clip

**Not in version 1:**
- Live camera streams
- Multiple zones or lines
- Objects other than people

## Definitions 

- **A person “enters the zone” when:** The bottom-middle of their bounding box moves from outside the marked zone to inside it. Count one entry per transition, not once per frame. Someone first detected inside does not count as an entry.

- **A person “crosses the line” when:** The same tracked person’s bottom-middle point moves from one side of the marked line to the other, passing through the line segment. Record the direction so crossings in opposite directions can be distinguished.

- **“Person count” means:** The number of people whose bottom-middle points are inside the marked zone at a specified video timestamp, rather than the total number of different people across the video.
