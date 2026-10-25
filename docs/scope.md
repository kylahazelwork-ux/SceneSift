# Version 1 scope and definitions

## Supports

- One prerecorded video at a time
- Detecting and tracking people
- One zone (a marked area) and one line, each optional
- Three question types:
  1. Zone entries: "When did someone enter the zone?"
  2. Line crossings: "When did someone cross the line?"
  3. Person counts: "How many people were in the zone at 0:30?"
- Typed or spoken questions
- Answers include timestamps and matching frames as evidence

## Not in version 1

- Live camera streams
- Multiple zones or lines
- Objects other than people
- Recognizing the same person after they leave and come back

## Definitions

- **Position:** A person's position is the bottom-middle point of their
  detection box, which is roughly where their feet touch the ground.

- **A person enters the zone when:** Their position moves from outside the
  zone to inside it and stays inside for 5 frames in a row (0.5 s at 10 fps).
  Count one entry per transition, not once per frame. Someone first detected
  inside does not count as an entry.

- **A person crosses the line when:** The same tracked person's position
  moves from one side of the line to the other, passing through the line
  segment. The direction (left to right or right to left) is recorded.

- **Person count means:** The number of people whose positions are inside
  the zone at a specified video time, not the total number of different
  people across the video.
