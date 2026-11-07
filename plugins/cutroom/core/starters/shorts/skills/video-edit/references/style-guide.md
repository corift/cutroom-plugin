# Style guide: the default look (`shorts` starter)

This is the spec the `shorts` starter templates are built to. Use it when the project doesn't say otherwise. **The project's `instructions.md` and `brand.json`, and `$CUTROOM_ACCOUNT/preferences.md`, override anything here.** Colours and fonts below are the defaults the engine falls back to when the brand kit doesn't set them (`cutroom.brand`: `accent`, `marker`, `highlight`, `caption`, `serif_italic`, `mono`).

The last sections (§Craft defaults, §Line-level visuals) are general craft rules that hold for any look.

## Polish rules (default for every graphic)

Why: one consistent system is what makes an edit look properly edited. An edit with 6–7 fonts (including handwriting), 6 colours, a dozen sticker chips, tilted elements and bouncy entrances looks like a kids' app; any one of those reads as "fun", but stacked together they read as childish. The reference (@kallawaymarketing) uses 2 fonts, 1 accent and nothing tilted.
1. **Two fonts.** A bold sans (SF Pro Display Bold for graphics, the caption font for captions) plus the serif italic for **one** accent word per scene. Small labels may use mono (the kit's `mono`, or SF Mono for code). **Never** handwriting or novelty fonts (Noteworthy `B.hand`, Marker Felt).
2. **One accent colour** (the brand kit's `accent`; default red (232,48,40)) on black and white. Other brand colours (product logos, app UI) appear only inside real UI, logos and screenshots, never as decoration. Footage is graded toward the palette (desaturate ~0.6–0.85) unless the real colour is the point.
3. **Nothing tilted.** Rotation is 0 on cards, chips, prints and words. Motion comes from push, drift and focus, not from rotation.
4. **No sticker chips.** A label is plain text (bold or small uppercase mono), or `B.tag()` (a dark chip with an accent left bar). Skip a label the caption already says.
5. **Entrances come into focus** (`B.focus_in`: blur + 1.12 → sharp in ~0.3s). Words un-blur on the spoken word (`B.unblur_text`). No bounces (`B.back`), drop-ins, slams or stamps.
6. **Never frozen.** Every hold gets a slow push or drift (`B.push_layer`, 1.0 → 1.05–1.06 across the beat). Payoffs get an accent `B.ripple`.
7. **Fewer, bigger things.** 1–3 elements per scene, filling ~85–95% of the frame width. Use flat shadows or none, not a drop shadow on everything.

## References

- **Graphics, captions, pop-out and headers: @kallawaymarketing.** https://www.instagram.com/reel/DcqiQesO_R9/ (38.9s)
- **Cutting rhythm and editorial feel: @rpn.** https://www.instagram.com/reel/DdpGALzywYY/ (120s, 47 cuts)

Take from @rpn the cutting, the big face panel and real graphics (screenshots, footage, posts) as assets inside the layouts. Don't restyle toward his 50/50 B-roll split with tiny mono captions.

## Canvas bands (1080x1920)

| Band | y | What lives there |
|---|---|---|
| *Platform UI* | *0–250* | *Unsafe: status bar + Shorts/Reels header. Keep it to background / face only* |
| Header | 250–340 (`HEAD_Y = 260`) | Accent type-on header, plus an optional white sub-line. Same y on face shots and stack |
| Graphic | 360–900 | Glowing card with the visual (card height ~460–530) |
| **Caption** | **960, fixed (dead centre)** | Captions, in the same spot in every layout — on the stack seam |
| Face panel | 960–1920 | Face fills the WHOLE bottom half, full width, hard seam (stack layout) |
| *Platform UI* | *1500–1920, and x>900 from y 1080* | *Unsafe: channel/title/share + like/comment rail. Face only, no text* |

### Safe zone

Shorts and Reels draw their UI over the video, and tall phones crop ~55px per side. **Anything that must be read stays inside x 70–1010, y 250–1500.** The right rail (x>900, y 1080–1780) and the bottom 420px are only for face or background. A header at y≈64 sits under the status bar and the "Shorts" header.

- `cutroom.safezone`: `SAFE`, `overlay(img)` (tints the unsafe zones, for review only, never in the render) and `check(boxes)`.
- The storyboard rough board draws the overlay by default (`rough_board(..., safe=True)`).
- Preview stills: `python3 renderN.py --preview ... --safe`.
- Blank template: `$CUTROOM_ASSETS/safe_zone_1080x1920.png`.
- The end card's big title sits in 1030–1450, left-aligned, clear of the right rail.

The caption spot never moves (moving captions feel jarring and are hard to follow), and it's centred vertically. Captions overlapping a graphic or the face now and then is fine; covering the mouth is not.

## Layouts

| Mode | Use | Notes |
|---|---|---|
| **face** | Opinions, hooks, "you" lines, punchlines | Tight close-up, bottom-anchored: `Framing(wide=1.28, tight=1.38, face_cy=1.0)` so the centred caption sits on the chin, never the mouth. Alternate on every cut. Headers at `HEAD_Y` (260), logo tiles at y≈440. A face beat longer than ~2.5s can take a hard-cut punch-in (`punch=<t>` on the beat; 1.2×, cy 0.38) on a phrase start ~1.5–2s in. |
| **stack** | The default whenever something can be shown (incl. montage + document scenes) | Dotted near-black top half with header + glowing card; face fills the full-width bottom half: `Stack(framing)` — defaults `card=(0,960,1080,960)`, radius 0, `src_top=0.07` (headroom), `pop=240`, `hands_only=True`. **Pop-out is hands only**: the head/hair is hard-cropped at the seam (hair spilling over the graphic looks bad; cropping is fine). |
| **full** | Whenever the thing itself is shown: examples, montages, results after an Enter press, receipts, end card | Full-width band 1080x960 at y 330–1290 over a blurred, darkened copy of the same clip; 16:9 clips drift slowly; 9:16 clips are banded too (`cy=0.55`), because full-bleed collides with the header. Header at 260; credit pill top-left of the band; captions at y=960 with the seam pill, as in every layout. Montage: ~1.25s per clip, shutter on each change. |
| **inset** | Explainer reels where the face should stay on screen | See `blocks-catalog.md` §Canvas and layout: graphic zone on top, a rounded face inset flush at the bottom with the head popping out, captions at y≈1170. |

- A small rounded face card (e.g. `card=(210,1360,660,530)`) reads as too small; give the face the whole bottom half, or the inset size in the blocks catalog.
- **Pop-out:** the person mask (`$CUTROOM_CORE/engine/personmask.swift` or `personmask.py`) produces `mask_vN.mp4`. `Stack.draw` keys the person above the card's top edge.
  - **Never cut the panel edge through the forehead** (a sliced head with only hair popping out looks broken). Hair/head never pops over the graphic — `hands_only=True` blanks the head's columns in the pop-out strip.
- Prefer stack beats over full screen for explanation (keep the face on screen), full screen for real clips and receipts, and **end on the face**, not a graphic.

## Captions (`captions.py`, style `"kallaway"`)

- **Font:** the kit's `caption` font (default Helvetica Neue **Bold**, `core.HELV`, `HelveticaNeue.ttc` index 1) at 68px, tracking -0.045em.
  - Colour is pure white, with a soft drop shadow: black at alpha 200, blur 10, offset 3px down.
- **On the seam (stack/split/full band): a tight near-black pill** (PILL (28,28,30) at alpha 225, radius 18, padding 26×10, no shadow). A caption straddling graphic + face is unreadable without it. Face shots keep the plain shadowed caption.
- Write captions as spoken: lowercase except proper nouns, trailing commas dropped.
- 1–2 words per chunk (at most 14 characters). Hard swap: no pop, bounce or per-word highlight.
- **Key phrases** switch to the serif italic (default *New York Italic*) at 74px, passed via `join_phrases(words, EMPH)`.
  - Use about one per sentence: product names, the punchline, the benefit.
- Fix only mis-transcriptions (Cloud → Claude). Never paraphrase. Drop words the transcriber invented (e.g. a leading "So" that isn't in the audio).
- Don't repeat the caption in graphic text (an accent word on screen that says the same word as the caption reads as doubled). Let the caption say the word and give the graphic something else.
- Legacy `"rpn"` style (uppercase DM Mono, pills) is still in `STYLES` if ever asked for.

## Headers and type

- **Header:** white serif italic, 50–58px, inside an accent-colour box, typed on at about 32 chars/s (`red_header`; it uses the brand `accent`). An optional bold white sub-line types after it.
  - Used as the stack header at `HEAD_Y = 260`.
  - Also for section headers over the face (same y) ("1. It makes videos") and statements.
  - Off by default on explainer reels (see `explainer-animations.md`).
- **Product names and numbers:** SF Pro Display Semibold/Bold.
- **Labels, sources and credits:** small uppercase mono kickers in grey.

## Graphics ("techy-pro" plus the glowing-card look)

- **Background:** near-black (8,8,9) with a 22px dot grid (`dotted_bg`), or the flat textured `B.canvas()`.
- **Cards:** `glow_card`, with a white 3px outline, about 26px radius and a soft white outer glow. They come into focus (Polish rules) rather than bouncing in.
- **Accents:**
  - The brand `accent` is the one accent (see Polish rules); losers in grey.
  - Accent for headers and the before/after wipe bar.
  - The brand `marker` (default yellow (255,214,92)) for highlighted lines in documents.
- **Component set:**
  - bars that grow while their numbers count up
  - terminal: the prompt types, then progress lines cascade
  - checklist that ticks on the spoken word
  - paper document with a before/after wipe, marker sweep and chips
  - floating logo tiles for swaps: strike-through, then the new one rises in
- **Motion:** each element cascades in with ease-outs, never as a group, and never with bounces.
- **Sources:** real ones only, with a small source line on the graphic. Credit clips as `MADE WITH <TOOL> · @handle`.
- **Real nouns, drawn mechanisms.** For nouns (security teams, apps, hackers, hospitals, a cake), use real footage or real brand assets; drawn icon art (cartoon shields, coloured blocks, a bare logo mark) reads as cheap. Keep drawn shapes for abstract UI and mechanisms (code panel, race bars, quote cards, an evolving diagram).
- **Show brands as they look today.** Cut the real current app tiles/UI from source footage (e.g. a launch video frame); never an old badge or a toy mock-up.

## Cutting (see `cut-rules.md`)

- Cut between sentences and keep joins tight (~0.16s, pauses planned on the dried voice).
- Change something visually (a cut, layout or header) every 2–5s. The face should never sit alone for more than about 6s.
- Get the subject on screen within 1s of naming it in the hook.
- The end card goes over the last line, then holds 1.3s.

## Sound (see `sound-design.md`)

- Real samples from `$CUTROOM_ASSETS/sfx/` (and the user's `$CUTROOM_ACCOUNT/sfx/`) only. Mix them subtly, about 8–10 dB under the voice.
- No synthesized sound, no music bed unless asked, and no plops.

## Grade

Phone footage is left ungraded by default. If a grade is wanted, apply a subtle warm/contrast LUT to face shots only, never to UI.

## Craft defaults (any look)

- **Speed:** build talking heads at 1.03× by default; 1.0–1.055× is the working range. 1.10× is too fast once silence-trimmed cuts are joined back to back; take 1.0× when a cut feels rushed.
- **End a beat exactly on the cut.** A layout change that lands a moment before the camera cut reads as a glitch.
- **End a cut on the energy dip after the last word**, not at the word's transcript end (that clips the final syllable).
- **Hidden retakes:** transcribers can merge a retake into one long "word" or one smooth line. Re-transcribe suspicious stretches as separate chunks, and check the energy envelope before trusting a sentence boundary.
- **Mic check:** if the voice sounds boomy or too close, EQ it (`highpass=f=90`, −6 dB at 150 Hz, −2 dB at 300 Hz, light `acompressor`) into `voice_vN.wav` and mix from that.
- **Time reveals to land before the next line.** Anchor a reveal one phrase early if it would otherwise still be animating when the next sentence starts.
- **A named destination lands as its clause starts** (+0.1–0.4s), not when the name is finally said.
- **Hold dense proof longer.** A full-screen beat with a post + table needs about **2.1s+**; extend it ~0.3s into the next clause rather than cutting on the very next word boundary. Numbers must finish counting before the beat cuts (count in ~0.25s).
- **Real receipts for launches:** the company's real announcement image and the founder's real post ahead of anything recreated.
- **Don't animate over real actions:** no fake click ring on a clip that already shows the click. (A visible press is still required when *we* animate a click.)
- **Empty beats go to full face.** If a graphic beat has nothing real to show, cut to the face instead of filling it.
- **Turn lines on the face.** In stack/inset layouts, cut to full face (~1–2.5s) on turn and opinion lines ("The problem is,", "And this actually worked"), then return to the graphic on the next clause; roughly one face moment every 12–15s.

## Line-level visuals

In top-performing reels from both reference creators, the visual is the **literal noun being said** (the toggle on "stays awake", the URL on the URL), and **full face is saved for opinion, stakes and verdict lines**. The graphic area changes every ~0.6–0.8s, with a large change every ~2–3s and nothing still for more than ~5s. Edit rate is the floor, not what separates hits from misses: once an edit meets it, the difference is in the script.
