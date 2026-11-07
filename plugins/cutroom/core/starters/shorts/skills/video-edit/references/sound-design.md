# Sound design

Sound is laid **last**, on the storyboard's cues, from real samples. The project's `instructions.md` / account `preferences.md` can change any default here (e.g. a music bed, more or fewer clicks).

## Current defaults

- **Voice:** `S.mix(..., dry=85)` runs the voice through Apple voice isolation first (room echo + noise out, timing exact, 85% wet keeps a touch of room). Set `dry=None` only if the raw room sound is wanted. macOS only; elsewhere it warns and uses the raw voice.
- **Clicks:** only on real on-screen presses (Enter, copy, a message button) and at most an intro/payoff or two: about 6 a reel. Rows, tags, bars, counters, list ticks, icons landing and typing starts are silent cues (keep the cue `name` for timing, drop its `sfx`). `sfx_events()` warns over budget. Too many clicks ("click, click, click") is the most common sound note.
- **Typing:** a prompt that types on screen gets `typing` at gain 0.07 with `"until": "<its Enter cue>"`, so it stops 0.12s before the Enter click.
- **Keep:** whooshes on full-screen cuts, a ding on a payoff fill, the counter on a number count-up, an impact on the hook / chapter headers / end card.
- **No music bed** by default: creators usually add music in the platform's editor. SFX sit about 8–10 dB under the voice.
- Final loudness is -14 LUFS integrated and -1 dBTP; `sound.mix` runs loudnorm.

## Sound is laid last, on storyboard cues

- Every SFX is a **cue** in `storyboard.json` (`"sfx": "click"` etc.). `sb.sfx_events()` builds the mix. No separate hand-typed event list.
- The registry `$CUTROOM_ASSETS/sfx/sfx.json` holds file, onset, default gain and status. `avoid` items are refused. `sound.load(name)` looks in `$CUTROOM_ACCOUNT/sfx/` first, so a user file with the same name overrides the library sample; a new user sound can also be passed by path.
- **Clicks need a visible press** (`components.press`, driven by the same cue). A click with no press on screen reads as broken: e.g. the prompt already typed with nothing pressed at the click, or the logo swap already done by the time it sounds.
- After rendering, run `sb.cue_sheet(...)` and confirm each sound's visual is in the ON frame.

## The sample library (`$CUTROOM_ASSETS/sfx/`)

Onset/peak times are measured, so pass them to `sound.at()` (the registry does this for cues):

| File | Onset/peak | Use | Gain |
|---|---|---|---|
| impact-7.wav | 0.64 | Hook, chapter headers, end card | 0.34–0.55 |
| whoosh-1.wav | 0.80 (peak) | Every change into a stack or full layout | 0.18–0.22 |
| riser-3.wav | 0.73 (peak) | **Off by default**; only use if asked | — |
| camera-shutter-5.wav | 0.11 | Clip changes inside a montage | 0.22 |
| mouse-click.mp3 | 0.56 | Prompt submit, a real button press | 0.25–0.3 |
| correct-ding.mp3 | 0.14 | A payoff tick | 0.14 |
| counter-sound.mp3 | slice 14.6s + 1.0s | Numbers or bars counting up | 0.2 |
| keyboard-typing-fast.mp3 / keyboard-typing-laptop.mp3 | — | Subtle typing bed under on-screen typing | 0.07 |
| pop-1.mp3, money-sound-2.wav | — | Avoid (plops read as childish); money only for revenue claims | — |

## Rules

- **No plops, pops, bubbles, boings or cartoon swooshes.** They read as childish.
- **No synthesized sound.** The legacy synth palette in `sound.py` (`pad` bed, `boom`, `whoosh`, `riser`, `tick`) sounds flat and fake next to real samples; don't use it unless asked.
- One sound per visual event at most. Don't sound every caption or every word.
- Don't put a sound on a real clip that already has its own (e.g. its own click).
- The user may send their own files; prefer them over the library when they fit, and save reusable ones to `$CUTROOM_ACCOUNT/sfx/`.

## A very subtle music bed (only when asked)

When the user asks for a bed:
- Pick tracks from a royalty-free library (e.g. Pixabay Music): ambient/minimal, no vocals, no big drops. Show the user 2–3 options before downloading, and log the licence.
- Level: bed RMS = voice talking RMS **−18 dB** (−22 is a tad quiet), plus `duck_curve` −9 dB while the speaker talks, 1s fade-in, then loudnorm. Pass it as `S.mix(..., bed=<array>)`.

## Measured from the reference creators

- **@rpn**: a continuous low music bed under the voice (quiet frames around -28dB), a tonal synth pad in the intro, big sub-bass booms (20–90Hz, ~2s decay) on section hits, and a short dropout (near-silence) right before a hit.
- **@kallaway**: graphic cuts get a short transient or whoosh; the music bed only starts after the hook.
