# Animation blocks catalog

Code: `$CUTROOM_CORE/engine/cutroom/blocks.py` (`from cutroom import blocks as B`). Each block is `block(canvas, k, ...)`, where `k` is the time in seconds since the block started. Blocks are chunk-safe.
Live demo of the current blocks (Polish-rules only; off-style blocks left out): `$CUTROOM_CORE/templates/shorts/blocks_showcase.py OUT.mp4 [--face base.mp4 --mask mask.mp4]`.

Colours in blocks come from the brand kit (`blocks.RED` = brand `accent`, the serif italic = brand `serif_italic`), so a project's `brand.json` restyles them without code changes.

**This is a menu, not a recipe.** Read the script, work out what each line needs the viewer to *see*, and then pick blocks (or combine and extend them).
- Mix it up across a reel. Change the kind of visual every section, with one recurring scene per section and something updating about every second.
- Don't use every block, and don't force one in where the line doesn't call for it.
- If nothing fits, build a new block in the same spirit (and consider adding it to `blocks.py`):
  - one big physical or real thing per frame
  - a flat textured canvas
  - no boxed UI cards
  - per-element ease-out cascade

Ratings come from reviewing the showcase in real edits. Treat 👍 as a safe default, 🆗 as usable when it fits the line, and ❌ as don't-use. The project's instructions can override any of them.

## Canvas and layout

| Block | What it does | Rating |
|---|---|---|
| `canvas(theme, frame)` | Flat background (`dark` near-black or `paper` light grey) with a vignette and live film grain. Use it instead of the dotted box panels. | — |

**Inset layout (Kallaway proportions; storyboard layout `inset`):**
- The graphic zone is the top ~60% (y ~250–1090, inside the safe zone).
- The face is a rounded inset flush on the bottom edge, drawn with `face_inset(canvas, frame, mask, box, src_y, pop)`. Default box **(160,1380,920,1920)**: 760 wide, inset from the sides, flush at the bottom, only the top corners round. (A full-width inset (60,1300,1020,1920) also works but takes more of the frame.)
- The head breaks out over the inset's top edge, Kallaway-style. It needs the person mask (`mask_vN.mp4`). `src_y` is the source row that lands on the inset's top edge; set it so ~120–150px of head sits above the edge: `src_y` = head_top + 120/s with s = 760/1080. **The head must always pop out of the inset; a head cut off at the inset edge is a bug.** Graphics in the bottom of the zone can sit behind the head, and that's fine.
- **No full-screen layouts in an inset explainer.** Every beat is inset, so the face stays and the graphic zone changes. Results/payoffs (e.g. `phone`) go in the graphic zone, not full bleed. Real clips can still go full screen in a full band (y 330–1290 over its own blurred copy, captions staying at the inset spot with the pill) when the project's flow calls for it.
- Don't keep the face in the small inset for the whole reel: cut to full face (~1–2.5s) on turn and opinion lines, then return to the graphic.
- Captions for this layout go at **y=1170** (`cap.STYLES["kallaway"]["y"]["stack"]=1170`), between the graphic zone and the popped-out head. `storyboard.rough_board` reads `caption_y_inset` and draws inset beats with the mask.

## Blocks

**Off by default (they break style-guide §Polish rules):** use only when the user or the project asks. `sticky_notes` (handwriting + tilt), `marker_circle`/`marker_line`/`marker_arrow` (hand-drawn), `cutout` (die-cut sticker with tilt), `_chip` used as a free-floating sticker label, `B.hand` and Marker Felt text, and anything with `rot≠0` or `back()` bounces. Their ratings below stand for when they're asked for.

| Block | What it does | Fits lines like… | Rating |
|---|---|---|---|
| `glow_chart` | A neon line chart draws on; points light up as the line reaches them; white label chips pop; `fill=True` adds an area fill. Points can be cued to words (`point_times`). | before vs now, trends, "the old way vs the new way" | 👍 |
| `big_number` | A huge count-up (a→b) with a colour bloom and a settle, plus an optional italic serif label. | any headline number ("5×", "$500K", "72%") | 👍 |
| `post` | An X post shown verbatim (avatar, name, verified tick, handle · date, body, views). A highlighter sweeps a phrase word by word, and the rest of the text dims. | "he even said…", receipts, quotes from a real person | 👍 |
| `person_quote` | Dark card: round avatar, big name, logo + role line, a divider that draws, then the quote types on in serif. Optional highlighter on one word. | introducing who someone is plus their one-line advice | 👍 |
| `number_morph` | The first value rolls up and out like an odometer while the new value rolls in, and the labels crossfade. | "600 words → 3 sentences", any reduction or upgrade | 🆗 (a strike-through version read worse; the roll replaced it) |
| `cutout` | A photo as a die-cut sticker (white border, real shadow) drops in; a name tag and a logo badge slap on. | putting a face to a name | 🆗, off by default (prefer `post` / `person_quote` when there's a quote) |
| `phone` | A phone rises in with a tilt and its screen scrolls a tall screenshot (use a mobile-width capture). | results, apps, landing pages, "here's what it built" | 🆗 |
| `marker_circle` / `marker_line` / `marker_arrow` | Hand-drawn accent marker: a loop around words, an underline, a curved arrow. Pass exact text boxes from `text_box()` so the loop hugs the words. | emphasis on a phrase in a quote or screenshot | 🆗, off by default (the loop must never run off or cut through letters) |
| `logo_burst` | The logo rises and turns into place on a breathing bloom. | first mention of a product or company | 🆗 (a rays/explosion version read as "mid" and was removed) |
| `scroll_doc` | A real-text prompt doc scrolling inside a window that fades at the edges. | "people paste these giant templates" | 🆗 |
| `delete_lines` | A real edit on a doc: a blue text selection runs down every line except the kept ones, then they collapse and the doc shrinks around what's left. | "delete most of your prompt", cutting things down | new |
| `sticky_notes` / `Note` | Handwritten sticky notes slap on (with a small shake) and peel off. | lists of tips/tricks/rules piling up | 🆗, off by default |
| `glow_list` | Numbered rounded tiles pop in with their lines; earlier lines dim. | 3-step frameworks ("what / who / what good looks like") | 🆗 |
| `prompt_bar` | A dark chat composer: parts `[(text,t,dur)]` type on with a caret, then the send button presses at `enter_t` (bloom + dip) and the text fades. Optional attach chip ("my_prompt.txt · 412 lines") and model label. | "you just ask for…", typing the actual prompt, "ask Claude to do it" | 👍 (a typing prompt box is consistently liked) |
| `focus_in` | Polish entrance for any image: blur + 1.12× → sharp in ~0.3s. | every entrance (replaces drop-ins and `back()` bounces) | default |
| `tag` | The one label chip: dark, flat, accent left bar, no tilt, focuses in. | short labels the caption doesn't already say | default |
| `ripple` | A thin accent ring expands and fades over ~15 frames. | payoffs, a match, "this one" | default |
| `push_layer` | Draw the scene on one layer and push it in 1.0 → 1.06 across the beat, so nothing freezes. | every hold | default |
| `unblur_text` | Kallaway's slow text reveal: the text is already on screen, blurred and dim, ~0.6s before it's spoken, then sharpens exactly on the word in ~0.25s with a white shine across it and a slow drift. Stagger several calls on word times to build a ladder or list line by line. | ladders and tiers ("1,000 → 10K → 100K → 1M"), lists, a key word or number landing | 👍 |
| `title` | Section title: bold sans words plus an italic serif accent word, per-word cascade, with a marker underline on the accent. | the persistent title for a section | — (not rated) |
| `thud` / `paper_stack` | A heavy object drops in with a squash, camera shake and a dust puff. | "handing them a three-page script" | — (not rated) |
| `Framing.face(frame, t, punch=)` (layout.py) | Kallaway punch-in: from `punch` on, a hard cut to a 1.2× zoom (cy 0.38); face stays, nothing else changes. Storyboard: `punch=<t>` on a face beat → `FRAMING.face(frame, t, b.get("punch"))`. | face beats longer than ~2.5s; cut on a phrase start ~1.5–2s in | 👍 |
| `rewind_counter(cv, k, a, b, settle, label)` | Year rolls back (2026 → 2021, ~0.9s) with an italic "rewind" label, then settles small up top as the date (`settle`) for the rest of the beat; `alpha` to fade it as a photo sharpens. | "go back N years", "in 2021…" backstory jumps | 👍 |
| `versus_bars(cv, k, rows=[(name, value, logo, t_on)], vmax, title)` | Subject vs the named rivals: real logo badge, name, bar grows on each spoken name (~0.6s), number counts in 0.25s; `accent` row in the accent colour with glow. Add a source line. | after a real benchmark table, to make "it's up there with X and Y" obvious | 👍 |
| `post_receipt(cv, k, avatar, name, handle, text, chart, crop, cols=[(x0, x1, t_on)])` | A founder's real X post (verbatim, views) on top; the real chart cropped to the columns/rows that matter rises under it; `cols` get an accent tint + outline on their word. Hold ≥2.1s. | launches with an official chart | 👍 |
| `flip_tile(cv, k, front, back, cx, cy)` | Card flip on its word: front squashes to an edge, back opens out with a small lift (old brand → new brand, before → after). | "Facebook renamed itself Meta", "it became…" | 👍 |
| `dot_stream(cv, k, src, targets=[((x, y), t_on)])` | White dots stream on curved paths out of one thing into others, split across targets as each lands. | "users went back to ChatGPT or Claude", money/data/people moving | 👍 |

**Benchmarks:** a dense benchmark table alone isn't enough. The pattern that works: (1) the real table, cropped to the columns and rows that matter, with the subject's column outlined in the accent on its word; (2) then `versus_bars` of just the subject vs the 2 rivals the script names, each bar growing on its spoken name, with real logos and a source line. Numbers must finish counting before the beat cuts.

## Calm motion kit (Kallaway-style): the default

The Polish rules in `style-guide.md` make this the default. Helpers live in `blocks.py`: `focus_in`, `tag`, `ripple`, `push_layer`, `unblur_text`. It's a motion treatment, not a new look: it keeps the layouts, rhythm and captions. Reach for it whenever a scene starts to feel busy or toy-like.
- **Focus-pull entrance** (`focus_in`): blur 14→0 and scale 1.12→1.0 in ~0.3s (expo). Use it in place of drop-ins, slide-ups and `B.back` bounces.
- **Never frozen** (`push_layer`): draw the scene on one layer and push the whole layer in 1.0→1.06 across the beat. Moving parts ease (expo) instead of springing or wobbling.
- **Plain words on the word**: bold type or small uppercase mono that focus-pulls in when the word is spoken. No sticker chips, no tilt, no box. Cut a label the caption already says.
- **One accent:** black, white and the brand accent only. Line art is white strokes, and footage is desaturated (`gray≈0.85`). A count-up is plain white with no glow and turns the accent colour on the payoff, plus an accent `ripple` ring (~15 frames).
- Minimum readable sizes at phone scale: mono labels ≥38 px, counter ~130 px (a hero number around 190px reads well; 300px is too big).

## Removed (❌, don't rebuild)

- **Rubber stamps** (`stamp_on`, a stamp slamming onto a doc), and ANY tilted boxed verdict word (NO MATCH, CAN'T UNBAKE, NOT ANYMORE): banned. For a verdict word use plain bold type that focus-pulls in (blur + 1.12 → sharp, no box, no tilt, no bounce), or nothing. (`explainer.stamp` is unrelated: it's the numpy dot stamp for swarms.)
- **`shred`** (the doc sliced into falling strips).
- **Ray/ring explosion on logos.**
