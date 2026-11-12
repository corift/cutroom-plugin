# Spotlight

The camera eases in and holds, the room goes dark and soft, and the person stays fully lit. An optional neon serif word glows behind the head. It eases back at `until`. For the name of the thing ("it's called…"), a reveal, or a line that should feel like a stage moment. Needs `--mask`; without one the person darkens with the room.

```json
{"do": "spotlight", "at": "it's called", "until": "real images", "text": "Wikimedia"}
```

- `text`: the word behind the head, set in heavy italic serif and shrunk to fit. Leave it out for just the dark room.
- `y` (face height − 290) is the word's centre. The top of the head should overlap its bottom edge; check a still.
- `zoom` (1.4) is where the camera settles, reached after `push` (0.8s) and held until `until`; `dim` (0.86) how dark the room gets; `blur` (12) how soft; `rgb` the glow colour (neon pink).
- The room darkens over 0.4s and comes back over 0.3s. Keep it to 2–5s. Leave out a `whip` or `glitch` on a section that starts with it; the fade is the transition.
- Captions stay up.
- Lands with a soft whoosh.
- Code: `V.spotlight`.
