# Floating reference clip

A second video plays in a rounded white-edged card floating above the head, with a small "via @handle" tag on its corner. It pops in, drifts gently, and shrinks away at `until`. For "I saw this edit…", "look at what X did", or before/after comparisons.

```json
{"do": "clip", "at": "design", "until": "and it checked", "file": "refs/their_edit.mp4", "start": 3.0,
 "via": "@handle", "x": 560, "y": 470, "w": 440}
```

- `file` is relative to the plan. `start`: seconds into the clip. It plays muted; the voice carries on.
- `w` (560) is the card width; keep it under 620 so the face stays clear. `y` sits it above the head; check it at every zoom.
- `via`: credit the real source when the clip is someone else's work. Leave it out for your own footage.
- `rot` (-3) tilts it; it also sways ±1°.
- Lands with a soft whoosh. Pair it with `pointer-caption.md` to say what to look at.
- Code: `V.ClipReader`, `V.floating_clip`.
