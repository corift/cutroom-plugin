# Background swap

The room disappears in one frame: the person is cut out with a white sticker edge and stands on a flat colour, or in front of a wall of their own videos, with a 1.1x push-in. It hard-cuts back at `until`. For "pulls me out", a change of topic, or "all my videos". Needs `--mask`.

```json
{"do": "swap", "at": "pulls", "until": "puts", "color": "orange"}
{"do": "swap", "at": "puts", "until": "when i mention", "wall": ["refs/a.mp4", "refs/b.mp4", "refs/c.mp4"]}
```

- `color`: a `SLAB` colour name (orange, ink, gold, white, blue, claude).
- `wall`: clips relative to the plan, tiled three across and playing, dimmed so the person reads. The first frame is blurred, then it's sharp. Use the creator's own videos; six files is plenty.
- Keep it to about 1–2s. Captions stay up, so a `pill` or `pop` style reads best over it.
- Lands with a whoosh.
- Code: `V.swap`, `V.wall`, `V.outline`.
