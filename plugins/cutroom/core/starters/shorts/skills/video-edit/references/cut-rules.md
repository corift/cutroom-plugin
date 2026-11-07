# Cut rules

> **Default for every video:** plan pauses on the dried voice, not the raw audio: `env, th = cp.speech_env(SRC)` then `cp.trim_edges(cp.plan(KEEPS, env, thresh=th), env, thresh=th)`. On the raw track, room tail sits above -42 dB and no pause is found, which leaves dead air at every join. Transcribe and QA with ElevenLabs Scribe: it's verbatim, so retakes and repeated words show up; Groq drops them.

These rules exist because cuts that are too tiny feel jarring, and a keep boundary that catches the start of a retake leaves a doubled word ("so so").

1. **Content cuts only between sentences.** Write `KEEPS` at sentence level in source seconds. Drop retakes, false starts, redundant lines and in-sentence self-repeats ("for you, for your business").
2. **Snap every boundary to the quietest 10ms point.** The default window is ±0.15s.
   - Use a tiny window (0.02) when the boundary must stay exactly where it was measured, for example right before a retake's first word.
   - The first frame (s ≤ 0.01) is never snapped.
3. **Pause trimming.**
   - Trim pauses longer than **0.25s**, and leave **0.08s** of air on each side (joins land ~0.16s). These are the `cutplan` defaults (`MAX_PAUSE`, `HANDLE`).
   - Inside `TIGHT` windows, where the face is covered by full-screen B-roll, trim pauses longer than **0.25s** (`TIGHT_PAUSE`). Those jump cuts are invisible.
   - Always run `cp.trim_edges(segs, env)` after `cp.plan()`: `plan()` only trims pauses *inside* keeps, so dead air at a keep's edges (e.g. reaching for the camera after a line) stays otherwise. Check `cp.silences(env, min_d=0.25)` on the base shows no run over ~0.35s.
4. **No segments under 0.6s.** The planner flags them. They read as glitches.
5. **Framing alternates on every visible cut**, wide ↔ tight. No per-segment zooms or mid-shot punch-ins (a deliberate hard-cut punch-in on a long face beat is the one exception; see `blocks-catalog.md`).
6. **12ms audio fades at every join.** `build()` does this automatically.
7. **QA by re-transcribing** the assembled cut, via `cutplan.qa`.
   - A doubled word means a keep boundary included the start of a retake. Move the keep's end to just before the retake's first word, using an energy dip.
   - The QA only flags doubled single words; read it for doubled *phrases* too.
8. **Speed:** `cp.build(..., speed=1.03)` by default (range 1.0–1.055). It applies `setpts`/`atempo` to the whole cut; `segments.json` is in sped-up time.
9. **Voice polish** in `build`:
   - highpass at 80Hz
   - +2.5dB presence boost at 3.5kHz
   - 3:1 compression
   - loudnorm to -16 (the final mix goes to -14)
