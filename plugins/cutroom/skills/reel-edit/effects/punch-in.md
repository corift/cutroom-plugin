# Punch-in

The camera moves on every cut and on the big words.

- **Section zoom**: `"zoom": 1.3` on a section. Alternate it between sections: 1.0 / 1.3 / 1.1 / 1.35. Every shot also pushes in slowly (+3.5% per second) from its cut.
- **Cuts inside a section** alternate between the section zoom and 12% tighter.
- **Punch moment**: a hard zoom on one word, held until `until`, with an impact and a small shake when the zoom is 1.4 or more.

```json
{"do": "punch", "at": "claude", "until": "entire", "zoom": 1.8}
```

- Use it on the hook's subject, a name, or a number. At most one every ~5s.
- A 1.8 punch also hides text burned into generated footage (Omni sometimes writes captions on the shirt). If it can't be hidden by framing, use `{"do": "blur", "at": ..., "until": ..., "y": 1250, "h": 300}`.
- The face stays at `--face-y` height at every zoom. Check the stills: a high zoom on a low face crops the chin.
