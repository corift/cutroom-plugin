# Visual tactics library

Reusable ways to *show* a line instead of just saying it. Most were learned from @rpn's mini-doc reels (e.g. his "Joining Sound Ventures" reel) and @albert.olgaard's tool reels.

Use them at storyboard time: for each beat, ask whether the line has a brand, a name, a number, a claim, a "who/what is X" question, or something the speaker called early. If it does, pick the matching tactic and write its name in the beat's `visual` field (e.g. `"visual": "count-up: 100,000,000 record sales"`).

**Pacing depends on the script, not a fixed cut rate.** @rpn's ~1 cut/s suits a dense mini-doc packed with names and numbers; most scripts don't need a cut every second. Use fast visuals where the script is dense with proof, and stay on the face for opinions, stories and "you" lines. Default guide: a visual change every 2–5s, faster through proof runs.

## 1. Keyword → graphic in the caption spot

When the speaker says a keyword, the caption for that word becomes a graphic, in the **same fixed caption spot** (y=960 in the default look; captions never move around):

| Keyword type | Becomes | Example |
|---|---|---|
| Brand/product | Its logo (white or colour version), sized like a caption word | "as an ((SOUND)) advisor", "switch back to [Claude logo]" |
| Person's name | Big serif italic (bigger than EMPH) | "*Guy Oseary*", "*Sam Altman*" |
| Key idea / turn | Heavy bold caps, bigger, can stack two lines | "RECOGNIZING TALENT", "BUT WE ARE" |

- Use them sparingly, about one per 5–8s. If every word becomes a graphic, none of them stand out.
- Logos come from `$CUTROOM_ACCOUNT/logos/` (official marks only).
- **Build status:** EMPH italic phrases exist (`captions.join_phrases`). A logo swap and bold-caps swap are not built yet; add a `SWAPS = {"claude": logo_img, ...}` path in `captions.caption_img` the first time a video needs it, and check legibility on the storyboard board.

## 2. Number count-up

Any number that matters (users, $, %, records, benchmark) rolls up to its final value while it's said, usually with a small label above ("Total record signings:"). It lands on the final number as the word ends.

- Where: in the caption spot over the face (big bold numerals), or inside a card on a stack beat.
- Sound: `counter` SFX (sliced, 1.0s) on the cue, which is anchored to the number word (`"t": "word:million"`).
- **Build status:** `B.big_number` (count-up with a settle and optional serif label), `B.number_morph` (odometer roll from one value to another) and `B.versus_bars` (bars that count) are in `blocks.py`; `components.bars_panel` also counts values up; dot-swarm/flow primitives are in `cutroom/explainer.py`.

## 3. Proof shown, not said: headline + highlighter

Every claim gets its receipt on screen, from the real source:
- an **article headline screenshot**, where a marker sweeps over the key phrase ("$240 Million AI Investment Fund");
- **X posts** as cards (`B.post`, `B.post_receipt`), a **magazine cover**, a **stock/metric chart**;
- a small source line, always.

- **Build status:** the marker colour `components.HILITE` (brand `marker`) exists, `render_doc` supports highlights, and `explainer.marked_copy` + `sweep` put a marker sweep on a real screenshot.
- Sourcing: `asset-sourcing.md`. Capture the real page (browser screenshot), never a mock.

## 4. "Who / what is X?" → search bar, then collage

For a question beat ("Now, who is Guy Oseary?", "So what is Claude Code?"):
1. A search bar types the name (UI mock, caret blinking, typing SFX optional).
2. Results/photos land as a collage on a clean background, in a per-element cascade. (Under the Polish rules: no tilt, entrances come into focus.)
3. The next line's facts ride on top of the collage.

- A light "gallery" look contrasts with the dark cards; use it as a *section*, not everywhere.
- **Build status:** not built. Add `search_bar(k, text)` and `photo_stack(k, imgs)` to `components.py` on first use.

## 5. Receipt: "I called it"

When the speaker predicted or covered something early, **show the old post or video** (their own profile grid → zoom into the post, with the date visible) as they say "I said this X months ago…". Then land the result ("…and here we are") with the headline proving it.

- It's one of the strongest credibility beats for an explainer channel. Script it on purpose.
- Stay on the face for the line itself (eye contact); cut to the receipt on the date/quote.
- Sourcing: screenshot the speaker's own X/IG/YouTube post; log the URL and date.

## 6. Acted-out comment CTA (from @albert.olgaard)

When the close is "comment WORD and I'll send you X", show a mock comment box. A cursor types WORD and taps Post, and the freebie's name appears as a chip. Only use it when the freebie is real and an auto-DM is set up. **Build status:** not built. Add `comment_box(k, word, chip)` to `components.py` on first use.

## 7. Metaphor hook animation + full-screen takeover (from @albert.olgaard)

- **Metaphor:** for an "X is N× faster/cheaper" hook, turn the comparison into a picture: logos racing, a scale tipping, bars fighting. Use it once, in the hook.
- **Takeover:** during a dense demo, the graphic can fill the frame and the face drops out. One big caption word sits under the graphic, with green for good numbers and red for problems.
- Raw screen recordings are fine. Clarity beats polish: some of the biggest tool reels have no motion graphics at all.

## Other tricks seen (use rarely)

- **Pattern break:** a one-frame white/inverted flash on a big turn, or a black screen with one line typing out in mono. At most once per video.
- **Famous-faces montage** for an abstract idea ("founders are rock stars"): fast cuts of recognizable people with their company's logo over them. Only with real, licensed-or-press footage, and credited.
