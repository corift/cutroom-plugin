# Word slabs

A full-screen word on a flat colour, replacing the shot for the length of that word. Two in a row make a beat: "ONE" on orange, "TAKE" on ink.

```json
{"do": "slab", "at": "one", "until": "take", "text": "ONE", "color": "orange"},
{"do": "slab", "at": "take", "until": "it wrote", "text": "TAKE", "color": "ink"}
```

- Colours: `orange`, `ink`, `gold`, `white`, `blue`, `claude`.
- Keep each under a second. Lands with a shutter.
- The voice keeps going under it, so the next line should start as the slab ends.
- Code: `V.slab`.
