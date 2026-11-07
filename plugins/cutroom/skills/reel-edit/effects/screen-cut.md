# Screen cut

A hard cut to a screen recording, a slow push-in toward the thing that matters, a thin red box that snaps on around it (no draw-on), then a hard cut to a zoomed crop of that box over a dimmed copy of the screen. Captions stay up. For "watch my screen", "click this", "here's the setting".

```json
{"do": "screen", "at": "watch my", "until": "then it pulls", "file": "edit/screen.mp4", "start": 2.0,
 "box": [340, 740, 740, 880], "box_at": "one button", "zoom_at": "matters"}
```

- `file` is relative to the plan and is cover-cropped to 9:16. Record or crop it vertical so the UI stays readable.
- `box` is x0, y0, x1, y1 on the 1080×1920 frame before the push-in. Render a `--preview` still on the screen first and read the box off it.
- The push-in is 10% over 0.6s toward the box. `box_at` snaps the red box on; `zoom_at` cuts to the crop. Leave either out to skip it.
- The red box should be up for about 1.2s before `zoom_at`.
- Sounds: a whoosh on the cut in, a click when the box snaps on, a soft whoosh on the zoom.
- Code: `V.screen`.
