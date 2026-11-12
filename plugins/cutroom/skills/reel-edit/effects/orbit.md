# Orbit

The speaker's own videos circle their head on a tilted ring. The cards spiral out from behind the head, pass behind the person (smaller, dimmer, soft) above the head and in front of them at chest height, then pull back in at `until`. For "every video you make", "all my videos", or a run of results. Needs `--mask` for the pass behind the head.

```json
{"do": "orbit", "at": "every video", "until": "anything", "files": ["refs/a.mp4", "refs/b.mp4", "refs/c.mp4", "refs/d.mp4", "refs/e.mp4", "refs/f.mp4"]}
```

- `files`: clips relative to the plan, playing muted. Five or six fill the ring; use the creator's own videos.
- `y` (face height + 40) is the ring's centre; `rx` (430) and `ry` (300) its width and depth; `w` (180) the card width; `speed` (1.1 rad/s); `tilt` (-8°).
- The front pass sits under the chin; check a still at the front of the ring if the face is low in frame, and raise `y` or lower `ry`.
- Hold it for 3–6s so the ring goes most of the way round.
- A whoosh as it opens and a softer one as it closes.
- Code: `V.orbit`.
