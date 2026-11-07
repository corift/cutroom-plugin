# Slide

The speaker moves up into the top half while a photo or clip rises into the bottom half, edge to edge. The voice carries on. It's the calmest big moment in the look, so use it to show the real thing the speaker just named.

```json
{"do": "slide", "at": "golden gate", "until": "so now", "file": "assets/bridge.jpg"}
{"do": "slide", "at": "real cities", "until": "anything", "files": ["city.jpg", "rocket.jpg", "first_flight.jpg"],
 "cuts": ["rocket", "moments"], "focus": {"rocket.jpg": [0.5, 0.2]}}
```

- `file`, or `files` with `cuts`: one cue per later file, each a hard cut on its word. Files are relative to the plan. About three per slide reads well.
- Photos get a slow push. Video clips play muted from `start` (0).
- `focus` keeps part of a photo in the crop: `[x, y]`, each 0 to 1, per file.
- `until` is when it has finished sliding back to the full shot. `"exit": false` makes that a hard cut instead.
- `face` (0.42): where the face sits in the top panel, as a fraction of its height. `zoom` (1.0): the framing in the panel. It also needs `--face-y` to be right.
- `join` (960): the y of the line between the panels.
- Captions travel with the join and sit on it, away from the face. `cy` moves them.
- Lands with a soft whoosh; each cut gets a click.
- Code: `V.slide`, `V.slide_still`, `V.slide_push`.
