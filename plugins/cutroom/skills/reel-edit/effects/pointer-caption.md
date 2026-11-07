# Pointer caption

A white caption chip with a gold arrow that draws itself to the thing it's about: by default the floating clip that's up, or any point on screen.

```json
{"do": "point", "at": "file", "until": "and it checked", "text": "his edit"},
{"do": "point", "at": "button", "text": "this one", "target": [300, 640]}
```

- `target`: `"clip"` (default, the active floating clip's bottom edge) or `[x, y]` on the 1080×1920 frame.
- `x`, `y` place the chip (760, 1000). Put it beside the face, never on it; the arrow curves away from the face.
- 1–3 words. One pointer at a time.
- Lands with a click. `rgb` recolours the arrow.
- Code: `V.pointer`.
