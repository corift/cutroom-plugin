# Reference video

Another video on screen, in one of five forms. Use it when the speaker mentions a reel, a demo, a result or "my videos". For a single card with a pointer caption, see `floating-clip.md`.

```json
{"do": "refs", "mode": "inset", "at": "reel", "until": "it floats", "file": "refs/their_edit.mp4", "via": "@handle"}
{"do": "refs", "mode": "fan", "at": "didn't", "until": "i recorded", "files": ["a.mp4", "b.mp4", "c.mp4"]}
{"do": "refs", "mode": "float", "at": "or a few", "until": "and my", "files": ["a.mp4", "b.mp4", "c.mp4", "d.mp4"]}
{"do": "refs", "mode": "fly", "at": "fly", "until": "boom", "files": ["a.mp4", "b.mp4", "c.mp4", "d.mp4"]}
{"do": "refs", "mode": "result", "at": "boom", "until": "comment", "file": "edit/final.mp4"}
```

- **inset**: a hard cut to the clip in a rounded card over a dimmed, blurred copy of itself. It replaces the face. Add `via` when the clip is someone else's work. Captions stay up.
- **fan**: three tilted cards (−11°, 0°, 11°) above the head, landing one frame apart.
- **float**: up to four demos drifting at different depths. The top two sit behind the person (smaller, dimmer, a little soft), and the bottom two sit in front at the edges. Needs `--mask` for the depth.
- **fly**: up to four cards fly out from behind the head to the sides, staggered, then hang there. Needs `--mask`.
- **result**: the clip grows from an inset to full frame in two frames, then holds. Keep it to about 1s. Captions hide.
- Files are relative to the plan. They play muted from `start` (0).
- Sounds: whoosh for inset, float and fly, a click for fan, an impact for result.
- Code: `V.inset`, `V.fan`, `V.depth`, `V.fly`, `V.result`.
