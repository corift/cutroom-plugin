---
name: video-edit
description: Edit a raw talking-head recording into a finished vertical short (Instagram Reels / TikTok / Shorts) — silence-snapped sentence cuts, a stack layout with person pop-out, bold captions in one fixed spot, animated explainer graphics, full-screen proof, and real-sample sound design laid on storyboard cues. Use when asked to edit, cut, caption, storyboard, add B-roll/animations/SFX to, or re-render a short-form talking-head video. Pure Python (Pillow + numpy + ffmpeg), no NLE, no HyperFrames/Remotion.
---

# Video edit (talking-head shorts)

A repeatable pipeline that turns a phone recording into a finished 1080x1920 short.
Everything is code: an edit is a cut plan, a timeline of layouts, and an event list for sound.

## Read first: the project decides the look

Before you design anything, read, in this order (later wins over earlier, and all of them win over this skill):
1. `$CUTROOM_ACCOUNT/preferences.md`: the user's preferences for every project.
2. The project's `instructions.md` (in your working directory, `projects/<slug>/`): how this kind of video should look and be made. **This is where house style lives.**
3. The project's `brand.json` (`$CUTROOM_BRAND_KIT`): colours (`accent`, `marker`, `highlight`) and fonts (`caption`, `serif_italic`, `mono`). The engine reads it through `cutroom.brand` (`engine/cutroom/brand.py`), so `components.RED`, `components.HILITE`, `core.HELV`, `captions.SERIF_IT` etc. already follow the kit. **Don't hard-code hex/RGB colours or font paths in new render scripts**: take them from those module constants or from `brand.color(name, default)` / `brand.font(name, default)`.
4. The project's `references/`, if any.

Everything below that describes a specific look (stack layout, red headers, caption spot y=960, Helvetica Neue + New York Italic, red as the one accent) is **the default look: the `shorts` starter** in `$CUTROOM_CORE/templates/shorts/`. Use it when the project doesn't say otherwise. The process (cut → QA → assets → storyboard gate → build → sound on cues → cue check → review) applies to every look.

When the user gives a note that is a lasting preference ("always", "never"), say so and suggest adding it to `instructions.md` (this kind of video) or `preferences.md` (everything). Don't edit them silently.

## The default look (`shorts` starter)

Graphics and captions in the style of @kallawaymarketing, plus a big face panel and editorial cutting in the style of @rpn. Start every new short from `$CUTROOM_CORE/templates/shorts/` and don't restyle unless the project or the user asks:
- **Polish rules (required): read `references/style-guide.md` §Polish rules.** Two fonts, one accent colour, nothing tilted, no sticker chips or handwriting, entrances come into focus, nothing frozen. Toy-like props read as childish.
- Stacked layout: graphic card on a dotted near-black top half, face filling the full-width bottom half (seam at y=960).
- Raised hands pop out over the graphic (person mask, `hands_only`); head and hair crop cleanly at the seam.
- Captions on the seam get a small dark pill for contrast; face shots keep the plain shadowed caption.
- Bold white captions (the brand kit's `caption` font, default Helvetica Neue Bold, with a soft shadow) in **one fixed, vertically centred spot (y=960) in every layout**, with key phrases in the italic serif.
- Accent-colour type-on headers (off by default on explainer reels; see below).

### Flow: talk → show → talk

The default rhythm on top of that look: **full-screen proof** alternating with the face.
- **Hook on the stack** (~2s, one example in a card), then **cut to a full-screen montage** of real examples right after the hook line (~1.25s per clip, a shutter on each change, a credit pill on each clip).
- **Talk → show → talk.** A face shot with a header for each claim, a stack for anything explained step by step (checklist, prompt box), and **full screen whenever the thing itself is on screen** (examples, results, receipts such as a quoted price).
- **Action → result.** A typed action (prompt box, keyboard SFX) ends on a visible Enter press, then the **result cuts to full screen** about 0.2s later. Never shrink the result under the action, and never overlap the box on the result clip.
- **Close on a full-screen montage** over the last line, or end on the face.
- Hold no layout longer than about 6s. A good split is roughly stack ~60% · full screen ~25–30% · face ~15%: open on the stack, cut to full screen for 2–5s when the real thing exists (launch clip, receipt post, real chart, product demo), go back to the stack with the next animation, and use short full-face cuts (1–2.5s) on turn and opinion lines. Never shrink a real clip into a card when it could be full screen.
- `seg(beat, i, n)` splits a montage beat evenly and matches the shutter cues (`"+1.25"` style or absolute times).

### Explainer animations

For explainer / wordy "how it works" scripts. It's the flow above, but **the explanation is animated** and **headers are off** unless the header itself is the point (use small kickers inside cards instead). Every spoken step is a cue-anchored state change. One recurring scene evolves across beats (e.g. an office of team rooms → versions → chat → library → manager). Big numbers get charts and flows (a 10k dot swarm, a Goal→lanes→Solution flow, comparison bars, a collapse). Receipts are verbatim quote cards with marker sweeps. Payoffs go full screen. **Read `references/explainer-animations.md`** (rules, scene catalogue, gotchas). The primitives are in `cutroom/explainer.py`.

Mix real footage and animation: real footage or real brand assets for showable nouns (teams, apps, places, products), animated scenes (an evolving diagram, counters, a scale, prompt UI) for the mechanism beats. Neither all-footage nor all-animation.

### Full-screen spec (`full_frame`/`g_full` in `$CUTROOM_CORE/templates/shorts/render_template.py`)

- Every clip fills a full-width band 1080x960 at y 330–1290, over a blurred, darkened (55%) copy of itself.
- 16:9 clips drift horizontally (`cx` 0.35→0.65), so more of the frame shows.
- 9:16 clips get the same band at `cy=0.55`. Full-bleed lets their own text crash into the header.
- The header is at 260 over the top gradient. The credit pill is top-left on the band.
- Captions sit at **y=960 with the seam pill**, the same spot as every other layout (jumping the caption between spots is hard to follow). Keep the band's own text clear of ~920–1000 (e.g. post text above, chart below).
- Each cut gets a small 1.05→1.0 settle.

Read `references/style-guide.md` (the default spec and the general craft defaults), `references/asset-sourcing.md` (how to find real B-roll) and `references/visual-tactics.md` before you design a timeline.

## Setup

- Engine: `$CUTROOM_CORE/engine/cutroom/` (`core`, `cutplan`, `captions`, `layout`, `components`, `blocks`, `explainer`, `storyboard`, `sound`, `voice`, `parallel`, `safezone`, `brand`). It's already importable (`from cutroom import cutplan as cp`): `PYTHONPATH` and `$CUTROOM_ENGINE` point at `$CUTROOM_CORE/engine`. The templates also do `sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))`.
- `python3` has `Pillow` and `numpy`. `ffmpeg`/`ffprobe` must be on PATH.
  - drawtext and libass are *not* required; all text is rendered with Pillow.
- Fonts (defaults; the brand kit overrides `caption`, `serif_italic`, `mono`):
  - Helvetica Neue Bold for captions (`core.HELV`, index 1)
  - New York (Italic) for key phrases and headers
  - DM Mono for kickers/labels
  - SF Pro for UI and numbers
  - SF Mono for code
  - Paths are in `core.py`.
- Transcription goes through `cutplan.transcribe` (word-level timestamps): ElevenLabs Scribe when `ELEVENLABS_API_KEY` is set (better on names, tighter word times; `SCRIBE_MODEL` overrides the model), else Groq `whisper-large-v3` with `GROQ_API_KEY`. The output records which one ran under `provider`. The cut is transcribed a second time for QA; that transcript also drives the captions.
  - The key is passed to curl through a temp config file. Never print it.
- Work folder: each video lives in `videos/YYYY-MM-DD-<slug>/` inside the project (raw recording + `script.md` + research at the top, all editing work in `edit/`). Cut scripts read the raw file as `../<raw>.MOV`.
  - Put downloaded third-party media in the video's `external_assets/` with the `external_` prefix.
  - Reusable assets: the shipped SFX library is `$CUTROOM_ASSETS/sfx/` (registry `sfx.json`) plus the safe-zone overlay `$CUTROOM_ASSETS/safe_zone_1080x1920.png`; the user's own sounds and logos live in the account (`$CUTROOM_ACCOUNT/sfx/`, `$CUTROOM_ACCOUNT/logos/`). A user sound with the same file name as a library sound overrides it.
  - Name renders `<slug>_vN.mp4`.

## 16:9 (landscape) sources

A 9:16 source keeps the normal pipeline. For 16:9 (people often film landscape because it's easier to frame):
- Cut and QA on the landscape file as usual, then make three bases from the cut, all at the same speed:
  - **face shots:** a plain 9:16 crop centred on the face (`crop=608:1080:<x>:0,scale=1080:1920`), with no extra zoom (`Framing(wide=1.0, tight=1.06)`). Don't use blur fills, letterboxing or "further out" composites; zooming the crop reads as way too tight.
  - **stack face panel:** crop 1080x960 straight from the landscape frame (e.g. `crop=1080:960:<x>:40`). It's sharp and keeps the whole head in frame. There's no room above the frame, so skip the pop-out and the mask.
  - Speed-ups are applied to all bases (`setpts`/`atempo`). Re-transcribe the sped-up base for captions.
- An unzoomed face puts y=960 on the mouth, so **face-shot captions go to y=1240** (chin/chest) with `cap.STYLES["kallaway"]["y"]["face"] = 1240`. Stack captions stay at 960.

## Before filming: script

If the project has its own hook/script skills or instructions, use them. After filming, the script's "show" notes (what's on screen per line) become the storyboard's first draft.

## Workflow (do these in order; each has a gate)

1. **Transcribe the raw source** with `cutplan.transcribe(src, "transcript.json")`. **Use ElevenLabs Scribe** (`ELEVENLABS_API_KEY`; it's picked automatically). It's verbatim: retakes, false starts and repeated words show up. Groq Whisper silently tidies them away, so cuts built on it keep repeats and QA still passes.
   - Read the whole transcript.
   - Mark retakes, false starts, repeated lines and in-sentence self-repeats ("for you, for your business").
2. **Write the cut plan** (`vN_cut.py`, from `$CUTROOM_CORE/templates/shorts/cut_template.py`) as sentence-level `KEEPS` in source seconds, plus `TIGHT` windows. See `references/cut-rules.md`.
   - **Pauses are planned on the dried voice, for every video:** `env, th = cp.speech_env(SRC)` runs Apple voice isolation on the source (cached as `<src>_iso100.wav`), then `cp.trim_edges(cp.plan(KEEPS, env, thresh=th), env, thresh=th)`. Pauses over 0.25s are trimmed to 0.08s of air each side (~0.16s joins). On the raw audio, room echo hides most pauses and leaves 0.3–0.5s of dead air at the joins.
   - **Speed:** build at `speed=1.03` by default (`cp.build(..., speed=SPEED)`); the useful range is 1.0–1.055×. Above ~1.06× reads too fast once silence-trimmed cuts are joined back to back; if a cut feels rushed, use 1.0×.
   - **Gate:** run `--dry` and read the report.
     - Segments under 0.6s are flagged SHORT and are usually a mistake.
     - Every content cut must fall between sentences, never inside a phrase.
3. **Build the base, then QA:** `cp.build()` → `base_vN.mp4` + `segments.json`.
   - Run `--qa` to re-transcribe the cut.
   - **Gate:** no doubled words (e.g. "so so"), nothing missing, no `pause` flags (a gap over ~0.35s), and the QA ran on ElevenLabs (it flags when it fell back to Groq). Fix a double by moving the keep boundary with a tiny snap window (0.02). The QA only catches doubled single words: read it for doubled *phrases* too.
   - Use the QA transcript as the caption source; its timings match the cut.
4. **Source real assets (required: the script drives the B-roll).** Follow `references/asset-sourcing.md`:
   - Go through the QA transcript and build a shot list: every showable noun, number, claim or example gets a real asset.
   - **X posts/videos:** ask Grok in the browser (x.com/i/grok) for recent posts with post URLs and direct MP4 links, then open each post to verify it.
   - **Official pages, benchmarks, hero images, before/after examples:** web search, primary sources first.
   - **Logos and SFX:** check `$CUTROOM_ACCOUNT/logos/`, `$CUTROOM_ACCOUNT/sfx/` and `$CUTROOM_ASSETS/sfx/` first.
   - Say what you're downloading, save it to `external_assets/` as `external_*`, and log every URL and date.
   - Pick a **visual tactic** for each beat that has a brand, name, number, claim, "who is X" question or receipt (`references/visual-tactics.md`: keyword→logo/serif/bold caps in the caption spot, number count-up, headline + highlighter, search bar → collage, "I called it" receipt). **Pacing follows the script:** dense proof runs get fast visuals; opinions and stories stay on the face.
   - **Gate:** no beat that names something showable is left without a real visual (or a deliberate typographic header).
5. **Storyboard → review gate (required before any build).** Write `edit/storyboard.json` (start from `$CUTROOM_CORE/templates/shorts/storyboard_template.json`): every beat of the video in order — time, layout, header, what's on screen, the asset, notes — and its **cues** (card rises, prompt submit, tick, wipe, clip change) with the SFX on each. Anchor cues to spoken words where possible (`"t": "word:copywriting"`). Every beat noun gets its **literal** visual (the toggle on "stays awake", the URL on the URL), and full face is saved for opinion/stakes/verdict lines (see `references/style-guide.md` §Line-level visuals). Then produce the review pack:
   ```python
   sb = Storyboard.load("storyboard.json")
   sb.markdown("storyboard.md")                              # the table
   sb.rough_board("base_vN.mp4", "storyboard_board.jpg")     # low-fi frame per beat, ~1 min
   ```
   See `references/example-storyboard.md` for what a good table looks like.
   - **Review happens in Cutroom.** With `storyboard.json`, the transcript, `base_vN.mp4` and `storyboard_board.jpg` in `edit/`, publish it:
     `node "$CUTROOM_CORE/bin/cutroom.mjs" publish storyboard "videos/<name>" edit/base_vN.mp4`
     It shows up as **STORYBOARD**: the cut plays with the planned beats on its timeline, and each beat's plan shows on a card.
     - Post a short summary. In a Cutroom chat, end the turn (notes come back as a new message). In a terminal session, add `--wait` and run it in the background so the notes wake the session.
     - The user's notes are the approval: if they say it's good or ask only for small changes, fold them in and build. If they ask for a different plan, update the JSON, rebuild the board and publish again first.
   - This replaces render-and-fix rounds.
   - **The storyboard step works for any style or creator.** The process (beats + cues JSON → table + rough frame board + safe-zone overlay → review → cue check) doesn't depend on the look. Swap out the style-specific parts (the layouts, header positions and caption spot in `rough_board`), but keep the process.
   - If the user explicitly says to skip review and just build ("just edit it"), build clean mock UI for anything unrecorded, render, publish the render with the cue check, and list the mocks so they can swap in real footage.
6. **Person mask** (for the pop-out), once the base exists:
   ```bash
   swiftc -O "$CUTROOM_CORE/engine/personmask.swift" -o <scratch>/personmask
   <scratch>/personmask base_vN.mp4 540 960 | ffmpeg -f rawvideo -pix_fmt gray -s 540x960 -r 30 -i - -c:v libx264 -crf 8 -pix_fmt yuv420p mask_vN.mp4
   ```
   It uses Apple Vision (built into macOS); a 60s video takes about 2 minutes.
   - **Cleaner matte / Linux:** `python3 "$CUTROOM_CORE/engine/personmask.py" base_vN.mp4 540 960 | ffmpeg …` (same pipe). Robust Video Matting: hair strands and steady edges, better than Vision. With `MATTE_URL` + `MATTE_TOKEN` set it runs on the GPU matte service (`$CUTROOM_CORE/engine/matte/modal_matte.py`, ~30s for a 60s reel); without them it falls back to onnxruntime on CPU (minutes; model at `PERSONMASK_MODEL`).
7. **Build the picture** in the render script (`renderN.py`, from `$CUTROOM_CORE/templates/shorts/render_template.py`):
   - `TIMELINE = SB.timeline({beat_id: draw_fn})`, `OVERLAYS = SB.overlays({...})`; animation moments read `SB.cue(name)` (ticks, wipes, submits). **Never hand-type a time that also exists in the storyboard.**
   - Every `click` cue needs a visible press: `C.press(canvas, t - SB.cue(name), x, y)`. Exception: don't animate a press over a real clip that already shows the click.
   - `OVERLAYS` for headers / logo tiles over the face.
   - Pick `EMPH` key phrases (about one per sentence) for the italic-serif captions.
   - Keep headers at y≥250 and graphics in 360–900 (**platform safe zone**, see style guide), so the caption band (y ≈ 920–1000) is clear; occasional overlap is OK.
   - Anchor every window to word times in the QA transcript. Time a reveal so it's complete before the next sentence starts, and land a named destination ("went back to X or Y") as its clause starts, not when the name is finally said.
   - Colours and fonts come from the brand kit (module constants / `cutroom.brand`), not literals.
   - Rules of thumb are in the style guide. Put a visual change every 2–5s, and never leave the face on screen for more than ~6s without an overlay or layout change. On a face beat longer than ~2.5s, a punch-in (`FRAMING.face(frame, t, b.get("punch"))`) keeps it alive.
8. **Preview stills:** `python3 renderN.py --preview t1,t2,... --safe`, then build a contact grid and look at it. `--safe` tints the Shorts/Reels UI zones.
   - **Gate:** no header, text, logo or number in a tinted zone (top 250, bottom 420, right rail), whole head inside the stack panel (no sliced forehead, no lean covering graphic text), caption in the same spot on every still and never on the mouth, text legible at phone size, nothing overlapping the caption band.
9. **Sound, laid last on the picture's cues** (like an editor: lock picture, then SFX): `mixN.py` (from `$CUTROOM_CORE/templates/shorts/mix_template.py`) is just `S.mix(..., sb.sfx_events(), ...)`. Samples, onsets and default gains come from `$CUTROOM_ASSETS/sfx/sfx.json`; items marked `avoid` are refused. Loudnorm to -14 LUFS. Details in `references/sound-design.md`.
   - Synthesized pads and booms sound flat and fake. Don't use `pad`/`boom`/`whoosh` synth unless asked.
   - No music bed by default (creators usually add music in the platform's editor). Add a very subtle bed only when asked (see sound-design).
   - **The voice is always dried (default):** `S.mix(..., dry=85)` runs the voice through Apple's on-device voice isolation (`cutroom/voice.py` → `$CUTROOM_CORE/engine/voiceisolate.swift`, compiled once into `~/.cache/cutroom/`). Room echo and noise go, timing is sample-exact, no key or upload. 85% wet keeps a touch of room so it doesn't sound processed. macOS only: elsewhere it warns and uses the raw voice.
   - **Clicks only on real on-screen presses** (Enter, a button, copy): about 6 a reel. Every other state change (rows, tags, bars, counters, typing starts) keeps its cue `name` for timing but has no `sfx`. `sfx_events()` warns over budget. Whooshes stay on full-screen cuts.
   - **Typing under prompts that type on screen:** `{"name": "type2", "sfx": "typing", "gain": 0.07, "until": "enter2"}` — a subtle keyboard bed that stops 0.12s before its Enter so the Enter click lands alone.
   - **Gate:** check `loudness()` reports about -14 LUFS and a -1 dBTP peak.
   - Listen at SFX peaks: each should sit under the voice, not over it.
   - **Cue check (after render):** `sb.cue_sheet("<slug>_vN.mp4", "cue_check.jpg")` shows frames at -0.2s / ON / +0.25s for every SFX. The visual event must be visible in the ON frame — a click with no press, or a sound landing after the thing already happened, gets its cue moved.
10. **Render:** `python3 renderN.py`, which muxes `mix_vN.wav`.
   - It renders in parallel (`cutroom.parallel`): the frame range is split into 2-second chunks handed out to every core as it frees up, each chunk in its own forked process with its own seeked readers and encoder (the Mac's hardware H.264 encoder, x264 `veryfast` elsewhere), then stitched with concat `-c copy`. A 36s reel with effects takes **~16s** on an M2 Pro. `--workers N` overrides; `CUTROOM_ENCODER=x264` forces software encoding.
   - **Chunk-safe rule:** `compose(t, …)` must depend only on `t` (module-level RNG is fine; no state carried between frames), and every B-roll reader must open seeked to the frame it starts at: `Reader(EA + f, w, h, s + PR.clip_offset(t, a))`. If an older render script isn't chunk-safe, copy `main()`/`open_sources`/`make_frame` from the template.
   - `--preview t1,t2,…` seeks straight to each still (~0.4s per still), so preview freely.
   - Fonts load from memory (`core.font`); a path-loaded FreeType face shares its file handle across forked workers and crashes with "invalid stream operation". Don't call `ImageFont.truetype(path)` directly in render scripts; use `core.font`.
   - **Upload-ready by default:** renders encode at 10,000 kbps H.264 for 1080x1920 (`core.BITRATE`, scaled by pixel count for other sizes through `parallel.render(..., size=(w, h))`) with AAC audio, the plain IG/TikTok upload rate (platforms re-encode to ~3–6 Mbps anyway). `core.social_encode(src, out)` re-encodes an older render the same way.
   - **One video per version.** Don't make a separate `_preview.mp4` or `_mobile` copy. Only use `core.preview_encode()` if a send fails for size.
11. **Deliver (in Cutroom):** `node "$CUTROOM_CORE/bin/cutroom.mjs" publish render "videos/<name>" edit/<slug>_vN.mp4` (it picks up `edit/cue_check.jpg`). In a Cutroom chat, end the turn; in a terminal session, publish with `--wait` in the background.
   - Post what changed and what to check, and ask for timestamped notes.
   - Publishing again with `_vN+1` adds a version to the same video.
   - On long builds, post a one-line status before going quiet, and give an ETA once the render starts.
12. **Address the review notes before the next version.** They arrive as a list (in the chat message, or the output of `publish … --wait`): time, the note, and the words said there. Read all of them, including earlier rounds that are still open, address every one, then say which notes each change covers. The user marks notes done in the app; you don't. Storyboard changes go through the review pack as usual.
   - The **Transcript** tab shows the words grouped by storyboard beat. Clicking a word jumps the video there.
13. **Save text work** after meaningful steps: `node "$CUTROOM_CORE/bin/cutroom.mjs" push "videos/<name>"` (it never sends audio, video or files over 25 MB).

## Library cheat-sheet

- `cutplan`:
  - `transcribe`, `envelope`, `speech_env(src)` (dried-voice envelope + threshold), `silences`, `plan(keeps, env, tight, thresh)`, `trim_edges`, `report`, `build(src, segs, out, speed=)`, `qa`, `src_to_out`.
- `voice` (Apple voice isolation, macOS): `dried(media, wet)` → cached `<stem>_iso<wet>.wav`, `isolate`, `available`.
- `captions`:
  - `load_words(json, fixes={"Cloud": "Claude"})` → `join_phrases(words, EMPH)` → `chunk(words, "kallaway")` → `draw(canvas, t, spans, mode, "kallaway")`.
- `layout`:
  - `Stack(framing, card, src_top).draw(canvas, frame, mask, t)`: the stack with pop-out.
  - `Framing(cuts)` alternates wide/tight on every visible cut. `.face(frame, t, punch=)` gives the full-frame face (with an optional punch-in); `.bottom(frame, t, face_cy)` gives the split-panel face.
  - `split(canvas, top, face)`, `resolve(t, timeline)`.
- `explainer`: `P`/`PC` safe paste, `panel`, `kick` (in-card kicker), `place_card`, `full_panel`, `orb`, `star`, `ring`, `mini_card`, `bez`, `rect_path` (line-draw), `stamp` (numpy dot stamp for the 10k swarm), `flow_lanes`/`draw_flow`, `quote_card` (verbatim receipt + marker), `marked_copy`/`sweep` (marker on a real screenshot), `chip_img`, `credit_pill`, `TEAM` colours.
- `components`:
  - `serif_title`, `chapter`, `float_img`, `tile`, `dark_panel`, `kicker`
  - `bars_panel`, `terminal_panel`, `checklist_panel`
  - `render_doc`, `model_tag`, `chip`, `paper_fade`, `press`
  - default look: `dotted_bg`, `glow_card`, `red_header` (type-on, in the brand accent)
  - `RED` (brand `accent`), `HILITE` (brand `marker`), `ACCENT` (brand `highlight`)
- `blocks`: reusable animation blocks with character. **Read `references/blocks-catalog.md`** (each block's name, what it does, what lines it fits, and how it has rated) and choose blocks per script; don't follow a fixed mapping.
- `brand`: `color(name, default)`, `font(name, default)`, `get(key, default)`; reads `$CUTROOM_BRAND_KIT`.
- `safezone`: `SAFE`, `overlay(img)`, `check(boxes)`.
- `parallel`:
  - `render(out, n, make_frame, open_sources, audio, workers)`, `clip_offset(t, a)`, `BITRATE`.
- `storyboard`:
  - `Storyboard.load(json)` → `.timeline(fns)`, `.overlays(fns)`, `.cue(name)`, `.sfx_events()`, `.sfx_cues()`, `.markdown()`, `.rough_board()`, `.cue_sheet()`, `.word_time("word#n")`.
- `sound`:
  - `load(name, gain, start, dur)`, `at(t, clip, onset)`, `mix(..., bed=, dry=85)`, `duck_curve`, `loudness` (synth `pad`/`boom`/`whoosh`/`riser`/`tick` are legacy; don't use).
- `core`:
  - Easing: `expo`, `cubic`, `inout`, `env`.
  - Text and compositing: `font`, `text_img`, `reveal`, `paste`, `cover`, `vgrad`, `logo`.
  - I/O: `Reader`, `probe_duration`, `social_encode`, `preview_encode`.

## Templates

Starting-point copies live in `$CUTROOM_CORE/templates/shorts/`:

- `cut_template.py`: cut plan (KEEPS/TIGHT, dried-voice pause planning, `--dry`/`--qa`)
- `render_template.py` (the flow look): stack + face + full-screen montages/results, a prompt box with typing
- `storyboard_template.json`: its storyboard (every beat + cue, incl. montage shutters and typing `dur`)
- `render_template_v5.py` / `storyboard_template_v5.json`: the earlier stack-heavy version
- `mix_template.py`: sound built from the storyboard cues
- `blocks_showcase.py`: a live demo of the current blocks in the inset layout (needs `CUTROOM_SHOWCASE_ROOT` pointing at a folder with logos and showcase clips)

Copy them into the video's `edit/`, keep the setup, and replace the content (KEEPS, EMPH, graphics, the storyboard beats/cues). Rename outputs to the new video (`<slug>_vN.mp4`).

## Hard rules

- **The project's `instructions.md`, `brand.json` and the account `preferences.md` override this skill.** Read them before designing.
- **Respect the platform safe zone.** Readable content goes in x 70–1010, y 250–1500. The rough board and `--safe` previews show the zones, so check them before building and again before rendering.
- **Always storyboard first.** Publish the review pack (`storyboard.json` + `storyboard_board.jpg` + the cut) to Cutroom and wait for the user's notes before building anything. After the render, publish it with the cue check (`cue_check.jpg`).
- The speaker's own words decide the edit. Never paraphrase the voiceover into captions; fix only mis-transcriptions (Cloud→Claude).
- Real sources only for claims:
  - Benchmarks, before/after examples and posts must come from primary sources.
  - Put a small source line on the graphic.
  - Credit creators' clips on screen (`Made with <tool> · @handle`).
- Motion: every element cascades on its own offset with ease-out. No bounces, no whole-block fades.
- SFX: real samples only, subtle. **No plops, pops, boings or cartoon swooshes** (they read as childish), no synthesized sound (flat and fake), no music bed unless asked.
- Captions never move between layouts.
- Only hands/gestures pop out; hair never spills over the graphic (cropping the head at the seam is fine, a sliced forehead mid-card is not).
- Don't change framing mid-shot except a deliberate hard-cut punch-in on a long face beat; otherwise change it only on cuts.
- Colours and fonts come from the brand kit via `cutroom.brand`; never hard-code them in new render scripts.
