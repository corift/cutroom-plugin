---
name: basic-video-edit
description: Simple cuts + burned-in captions for ANY talking video (any person, any aspect: landscape, vertical, square) — remove retakes, false starts and dead air at sentence boundaries, QA the cut by re-transcribing, then add clean bold white captions. No graphics, B-roll, headers, SFX or music. Use when asked to "just cut and caption" a video, clean up a recording, or add subtitles/captions to a general video. For talking-head shorts with graphics, layouts and sound design, use video-edit instead.
---

# Basic Video Edit (cuts + captions)

Takes a raw recording and returns a tighter video with captions.
- It only cuts and captions: no graphics, no layouts, no sound design.
- It works on any video and keeps the source size unless you ask for vertical.
- It uses Python and ffmpeg only, no editor app.

Everything runs through `$CUTROOM_CORE/skills/basic-video-edit/scripts/basic_edit.py`, which reuses the cutting and caption code of the Cutroom engine (`cutroom.cutplan`, `cutroom.captions`). Run it with `python3` (Pillow, numpy and the engine are on its path). Put positional arguments first and `--options` after them.

## Workflow (each step has a gate)

1. **Set up and transcribe.**
   - Make a work folder next to the source: `edit/` (in a Cutroom project the source sits in `videos/YYYY-MM-DD-<slug>/`; for a loose file, `edit_<CLIPNAME>/` next to it).
   - Run `basic_edit.py transcribe SRC transcript.json` (word timestamps). It uses ElevenLabs Scribe when `ELEVENLABS_API_KEY` is set (verbatim: retakes and repeated words show up), else Groq Whisper with `GROQ_API_KEY`. Keys are never printed.
   - Read the whole transcript. Mark retakes, false starts, repeated lines, dead air and off-topic chatter.
2. **Write `keeps.json`**: a list of `[start, end]` pairs in source seconds, at sentence level.
   - When someone restarts a line, keep only the **last clean take**.
   - End each keep on the pause **after** the last word, not at the word's transcript end, because a cut there clips the final syllable.
   - Add a 3rd value of `0.02` to pin a boundary exactly, for example right before a retake's first word.
3. **Dry-run the cut:** `basic_edit.py cut SRC keeps.json base.mp4 --dry`.
   - **Gate:** no `SHORT (<0.6s)` segments (they look like glitches), and every cut sits between sentences, never mid-phrase.
   - Pauses over 0.25s are shortened automatically, leaving 0.08s of air on each side (the `cutroom.cutplan` defaults).
4. **Build the cut and QA it:** `basic_edit.py cut SRC keeps.json base.mp4 --qa`.
   - This writes `base.mp4` and `base_transcript.json`. The audio gets light polish and is normalized to -16 LUFS.
   - **Gate:** QA shows no doubled words ("so so") and no missing lines.
   - To fix a double, move that keep's boundary to just before the retake, with a 0.02 window, and rebuild.
5. **Voice (optional):** if the mic sounds boomy, muddy or too close, run `basic_edit.py voice base.mp4 voice.wav`. It cuts the low end, adds gentle compression and normalizes to -14 LUFS. Then pass `--audio voice.wav` in step 7.
6. **Preview the captions:** `basic_edit.py caption base.mp4 base_transcript.json out.mp4 --preview 2,10,25,40 [--vertical]`. Then look at the stills.
   - **Gate:** the caption never covers a mouth, face or on-screen text, and it is readable at phone size. If it isn't, adjust `--y`, or add `--pill` over busy or bright footage.
7. **Render:** the same command without `--preview`. Deliver **one** video file: no separate preview copy.
   - It renders on every core through `cutroom.parallel.render` at the source's size, a few seconds per minute of video. If you write your own render script for a video, render through `parallel.render(..., size=(w, h))` and take encoder settings from `core.h264()` or `core.mezzanine()`; don't hand-roll a single-process ffmpeg encode.
8. **Deliver:** in a Cutroom project, publish it for review (`node "$CUTROOM_CORE/bin/cutroom.mjs" publish render "videos/<name>" edit/<file>.mp4`); otherwise send the video. Add a few stills and a short list of what was cut and why, and ask for timestamped feedback.

## Caption rules

- **Use the speaker's exact words.** Only fix mis-hears (`--fix "Cloud=Claude"`). Never paraphrase or clean up grammar.
- **Style:** Helvetica Neue Bold, white, soft shadow, up to 2 words per chunk. A new chunk starts on punctuation and on pauses.
  - `--font montserrat` switches to Montserrat Black (bundled in `fonts/`, OFL). Emphasis stays italic serif.
- **Emphasis:** at most one key phrase per sentence goes in italic serif (`--emph "one prompt,10 to 20 grand"`).
- **Position:** one fixed spot for the whole video; captions never move around.
  - Default for landscape is 84% of the height (lower third).
  - Default for vertical is 72%, below the face.
  - For vertical videos going to Reels, TikTok or Shorts, keep captions between 13% and 78% of the height, clear of the platform UI.
- If Whisper returns the transcript lowercase or without punctuation, restore sentence case with `--fix` (e.g. `--fix "i=I"`), or re-transcribe with a short `prompt` that has normal punctuation.
- Caption size scales with the frame, so it looks the same at 1080p, 4K or vertical.

## Cut rules

- Cut only between sentences. Use the word timestamps to find each boundary, and let the snap put the cut in silence.
- Remove retakes, false starts, "wait, let me redo that", long dead air, and repeated points.
- Keep natural pacing. Don't trim every breath, because tiny jump cuts feel jarring.
- Never reorder content or change meaning unless asked.
- For a heavy or unclear edit (for example "cut it to 60s"), list the proposed keeps in chat before building.

## Not in scope

Graphics, B-roll, zooms and reframing, headers, SFX, music, colour grading. For shorts with graphics and animations, use `video-edit`. A video cut here can go into that pipeline later: pass `base.mp4` and `base_transcript.json` so the cut isn't redone.
