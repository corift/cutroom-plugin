---
name: ugc-video-edit
description: The end-to-end spec-ad flow (research top TikToks → script → AI character → Omni clips → real-looking graphics → finished edit) and the editor for any vertical UGC-style ad. Use whenever the user says "make an ad for <brand>", "spec ad", or "ad making", or asks to "copy" a competitor's UGC ad (same structure and B-roll, new script and character). Edit a vertical UGC-style ad (talking head + B-roll) into a finished, captioned 9:16 video — tighten the A-roll, cut fillers and doubled words, map every script line to a B-roll shot, layer face punch-ins and product/demo cutaways, review the timing for flashes and stray frames, then caption and add an end card. Use for UGC ads, creator-style product ads, spec ads, AI-avatar (Omni etc.) talking heads with B-roll, or when the user says an ad's B-roll feels weird, cuts feel off, or the edit is slow. For a plain cut-and-caption with no B-roll, use basic-video-edit.
---

# UGC Video Edit (A-roll + B-roll ads)

This skill turns talking-head clips and B-roll into a finished vertical ad.
- **basic-video-edit** does the cut and the captions.
- **This skill** adds speed-up, a filler pass, even audio joins, shot mapping, punch-ins, B-roll, pop-up overlays, a hook line, sound effects, a handheld sway and a timing review.

Before anything else, read the project's `instructions.md` and `brand.json` and `$CUTROOM_ACCOUNT/preferences.md`; where they disagree with a default here, they win. Run the scripts with `python3` (Pillow, numpy and the engine are on its path):

```
PY=python3
BASIC="$CUTROOM_CORE/skills/basic-video-edit/scripts/basic_edit.py"
UGC="$CUTROOM_CORE/engine/cutroom/ugc/ugc_edit.py"
HTML="$CUTROOM_CORE/engine/cutroom/ugc/render_html.py"
```

Work inside the video's folder (`videos/<YYYY-MM-DD-slug>/`), with edit work in `edit/`. Review goes through Cutroom like every other edit: publish the shot map / stills as a storyboard where it fits, and every finished cut with `node "$CUTROOM_CORE/bin/cutroom.mjs" publish render "videos/<name>" edit/<slug>_vN.mp4`.

## The full spec-ad flow (worked example: a Northern Fitness spec ad)

This is the order that produced the best ad. The workflow below covers the edit itself.

1. **Research the brand's ads**, then **transcribe 6–8 top organic TikToks in the category** (0.3–5M views). Write a table of hook, shape and views. The script comes from these, not from the brand's ads alone. Follow the research checklist below. Its output is `plan-<brand>.md` (the checklist below is its outline).
2. **Write 3 scripts in different formats** that borrow those shapes. The winner was an insider tip ("If you're in Canada… don't order it from the States") that turned the brand's main claim (no customs) into a money story with one specific number ("like two hundred bucks more").
3. **The user edits the line by voice.** Keep their wording and only smooth the joins (copywriting-for-ads §4).
4. **Character:** swap the face in a frame from a top category creator using Nano Banana Pro. Change the person and one wardrobe detail, keep the set, remove the caption, and put the hands at rest. Show the frame before any video.
5. **A first-line Omni test, then every other clip at once.** Use the omni-talking-head word budget, with one hand gesture per clip.
6. **Edit with real assets only:**
   - Site screenshots via Playwright at 432px ×2.5. Crop the overflow to 1080 wide.
   - Product photos from the store's search (`/search/suggest.json`).
   - The logo cropped from the screenshot.
   - **Check every claim against what's on screen.** Her set rack had no lat pulldown, so that line cut to the real product photo with the cable circled.
7. **Design the graphics so they look real** (see "Graphics that look real" below). Show the user stills of every graphic before rendering video.
8. **3 full-screen proof shots and 5 pop-ups**, each landing on its word, plus sound effects and the end card. Put the graphics for the whole ad on one page; `$CUTROOM_CORE/templates/ugc/overlay-receipt-checkout.html` is the starting point.

## Competitor-copy flow (worked example: a Silk & Snow spec ad)

Use this when the user says to "copy" a competitor's UGC ad. It means the same structure, B-roll beats, set and editing, with a **different script and a different person**. Once the character is approved, one-shot the rest without check-ins.

1. **Find the reference.** Look for a competitor's creator video or partnership ad in the same category, with real reach (Silk & Snow → Endy's @itsmaelam paid partnership, 277K plays, 42s).
   - Sources: the competitor's Meta ads (`v1_facebook_ad_library_company_ads`) and TikTok search for the competitor name plus "review".
   - Save it to `refs/<brand>/comp/`.
2. **Break it down.** Make a 1fps contact sheet and get the transcript. Write down:
   - **The shape:** for Mae it was verdict first ("would I still buy it months later? yes, in a heartbeat"), then the move-in story, waited before reviewing, little things, the pet proof, and the brand claims at the close.
   - **The shot list, in order:** wide on the bed with hook text, the empty apartment, lying on the bare mattress, a hand pressing it, the duvet flop, the dog jumping on the bed, making the bed, and a cuddle at the end.
   - **The hook text style:** white bold text with yellow sparkles over the top third.
3. **Character, the only stop.** Pick the reference's best talking frame: eyes on the lens, captions off the face, set and pet visible.
   - Blur the face and the burned-in caption with PIL, then run the Nano Banana Pro swap (`quality: high`, 9:16). Make 2 variants that differ in hair, freckles and cardigan shade, and send them next to the reference.
   - Keep the set, the pet, the framing and the wardrobe type.
   - **Never recreate the real creator's face**, even if the user asks for it. Say why in one line and offer the same vibe with a new face.
4. **Script.** Pour the brand's verified claims into the reference's shape, one clip per clause (omni-talking-head budget). Give the pet a name, and turn the reference's pet beat into the brand's proof (Mochi jumping on the bed = motion isolation).
5. **Fire everything in parallel:** all Omni A-roll clips, plus the B-roll as 3–4 Omni montages.
   - Use `generate_video_with_references`, `model: "gemini-omni"`, with the approved character still as the reference. That keeps the face, pet and room consistent.
   - Put 2–4 timed shots per montage, with `HARD CUT to` between them, in the `production/broll-shot-prompts` format, copying the reference's shots one by one.
   - Cost in the example: 4 montages (24s) for 36 credits, and all came back usable on the first try.
   - Seedance on Cospark can fail with "Insufficient Pika balance". That's an upstream problem, so rerun the same prompts on Omni.
6. **Find the real cuts** with `ffmpeg -vf "select='gt(scene,0.25)',showinfo"`, then map each shot to the word it illustrates. Reuse the brand's existing proof screens (price, trust, coils) for the claim lines.
7. **Edit with every gate** (workflow below), then speed the captioned edit up 1.05× (`setpts=PTS/1.05`, `atempo=1.05`) before adding the end card. It sits on top of the prep speed-up (46s total in the example).
8. **Don't open on a staged wide B-roll shot.** The AI "sits centred on the bed, arms out" opener looked fake: too symmetrical, too clean and posed. Open on the face with the hook text above her head, and save AI B-roll for shots with action (dog jump, duvet, stretch).
9. **Then ship:** deliver the 1.05× cut (plus a 720p ~850k web encode and a poster if it's going on a landing page). **Never mention or link the competitor or its creator anywhere the brand sees it.**

## Research checklist (step 1)

Call Cospark `read_docs` first. Save everything to `refs/<brand>/`, and write the findings at the top of `plan-<brand>.md` before any script. Northern Fitness took about 15 Cospark calls.

1. **The brand's site.** Note:
   - what it is in one line, where it's based, and its house brands
   - its colours and font, and the logo (crop it from a screenshot if the HTML doesn't have it)
   - the main claim it repeats (Northern Fitness: "Canadian, so no customs or duty")
   - real prices for the 2–3 products the ad could name
     - Shopify stores: `curl -g "https://<site>/search/suggest.json?q=<term>&resources[type]=product"` gives prices and image URLs.
     - Apps: App Store screenshots and the pricing page.
2. **The brand's Meta ads.** Use `v1_facebook_ad_library_search_companies`, then `v1_facebook_ad_library_company_ads`. The scrape returns a page of about 30 ads, not the total. Before quoting a count, open `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id=<id>` and read the "~N results" heading (Silk & Snow showed 30 in the scrape and about 1,300 live). Say "in the 30 we went through" for anything judged from the sample.
   - Download every video ad (`meta-<id>.mp4`), make a contact sheet of each, and get a transcript (`meta-<id>_tr.json`).
   - Write down:
     - the longest-running winners (start date)
     - the claims that show up in every ad
     - their B-roll types and on-screen text style
     - whether captions are burned in, since that rules the footage out as B-roll
   - SaaS: the real app UI comes from these ads. Save stills to `refs/<brand>/ui/`.
3. **What customers really say.** Pull 4–6 quotes from reviews (Trustpilot, Google, App Store) or ad comments, in their words.
   - Note the main complaint too. Northern Fitness was 3.2/5 for delivery delays, so speed couldn't be the claim.
4. **Top organic TikToks in the category.**
   - Search `v1_tiktok_search_keyword` / `v1_tiktok_search_top` for the category and its pain: "home gym on a budget", "home gym Canada", "subscriptions I forgot about". Don't search the brand name.
   - Keep 6–8 videos with 0.3–5M views from creators, not brands.
   - Download them, make contact sheets, and get transcripts (`v1_tiktok_video_transcript`), saved as `tt-<handle>.*`.
   - Fill in the table: video, views, hook (first sentence word for word), shape.
5. **What the top videos share.** Write 3 bullets. Northern Fitness: the first sentence names the stake, there's one real price per item, and nobody says "buy now".
6. **Pick the claim the ad makes.** Choose one claim the brand can back up, turned into the customer's money, time or annoyance. Note what to avoid.
7. **Character references.** Save 3–4 frames of top creators in the category to `refs/<brand>/frames/` for the Nano Banana Pro swap, and show them to the user before generating anything.

**Gate:** the plan has the brand facts with real prices, the Meta ad notes, customer quotes, the TikTok table and the chosen claim. Only then write the 3 scripts (copywriting-for-ads).

## Graphics that look real

Generic white cards work, but a real-looking receipt works better. Every pop-up should look like a screenshot of the actual thing it stands for, not a design-system card.

1. **Find the real reference before designing.** For each graphic, pull 1–2 real examples and save them to `refs/<brand>/ui/`:
   - **Receipts and invoices:** search Google Images or Reddit for the real document (for example "UPS brokerage invoice", "FedEx duty bill Canada", "Amazon order summary").
   - **Checkout and app screens:** use the brand's live site via Playwright, or its real app screenshots from the App Store or its ads.
   - **Notifications, texts and bank alerts:** use the real iOS look, rebuilt from a real screenshot.
2. **GPT Image is allowed here, and only here.** Use GPT Image 2.5 for graphics such as receipts, invoices, documents and printed paper, because it renders text and paper well. It is never allowed for faces or characters, which stay Nano Banana Pro only.
   - Use `generate_image` with `model: "gpt-image-2.5-sunburst"`, `background: "transparent"` and `quality: "high"`. Pass the real reference as image 1 and spell out every line item and number in the prompt.
   - **Check every number and word in the result** against the script. If anything is wrong or garbled, regenerate, or blank that field and set it in HTML.
   - Fire at most two at a time. On Rocket Money v5, 3 of 4 parallel calls came back "No image generated", and all worked when retried one by one.
   - If an edit pass keeps one wrong letter (it wrote "PEACOCK FREMIUM" twice), patch it locally with PIL by copying the right glyph from the same line. Don't keep paying for regenerations.
   - Worked examples (a Rocket Money spec ad): a printed statement with yellow highlighter on the repeat charge, a "recurring charges" statement with a blank handwritten "= $" for HTML to write the total, two receipt emails as iPhone Mail cards, and a cancellation confirmation email.
   - Lookalike emails from real brands (Apple, Google, Paramount+) are fine in a spec ad, but tell the user they're lookalikes before an ad goes public.
   - Animate the PNG in the HTML page: reveal it top-down with a mask so it "prints", tick on each line, then draw a circle on the total. To have numbers count up, generate the receipt with the total area empty and put the counter on top in HTML.
3. **Copy the reference's details.** Use its font family, layout, grey labels, line items, the carrier logo or wordmark, dashed dividers, barcodes and reference numbers, and the order number style. A receipt should be paper-white with a monospace or carrier font, slightly rotated, with a soft shadow, and it should print or slide up rather than pop like a card.
4. **Animate the way the real thing behaves:**
   - Receipts print downward line by line, with a tick per line.
   - A notification drops from the top with the iOS spring.
   - A checkout total recalculates (old number fades, new one lands) and a field highlights.
   - Totals count up from partway.
   - Add a circle or underline drawn on the key number.
5. **Keep the numbers honest and consistent with the script:** each line lands on the word that names it, and the total matches what the person says ("like two hundred bucks" → +$200.65).
6. **Gate:** for each graphic, the stills sit next to their real reference in one image, and you'd believe it was a screenshot. Show that image to the user before rendering.

## Workflow (each step has a gate)

0. **Study the brand's real ads first.** Pull 3–5 of its top Meta and TikTok ads, make a contact sheet of each, and write down what they do: where the creator films, what's in their hands, how the app or product appears on screen, the hook text, and the end card. Copy the real app UI from these, not from memory.
   - **Gate:** you can name the 4–5 patterns the brand repeats, and your shot map uses them.
1. **Map the script to shots before anything is generated or cut.**
   - Write a table with one row per spoken line: line → shot under it (face, punch-in, or a named B-roll shot).
   - If a line has no shot to match it, or a shot has no line, fix the script now. Use the copywriting-for-ads skill for the wording.
   - Each line gets one of three treatments: the face, a **full-screen cutaway**, or a **pop-up overlay** over the face (see "Full screen or overlay" below).
   - A B-roll shot must land on the word it illustrates. If the product's key feature is something you can see (a squeeze bottle, an app screen), name it on the first shot that shows it, not later.
   - **Gate:** every B-roll shot has a line that names or implies it, and the user has approved the table.
2. **Check the A-roll clips.** For AI talking heads (Omni and similar), check every clip:
   - The accent is right. Flag clips nobody has listened to; don't assume.
   - There's no burned-in text, captions or speech bubbles. Look at a 1fps contact sheet.
   - Products and props keep their shape, and nothing new appears in the hands or on the counter.
   - No words are doubled. AI clips often say "bottles bottles" or "so weird, so weird".
   - Any regeneration costs credits, so get the user's approval before retaking a clip.
3. **Prep:** `$PY $UGC prep c1.mp4 c2.mp4 ... -o raw.mp4`.
   - This scales every clip to 1080x1920 at 30fps and speeds it up (`--speed`) before joining them. **Use `--speed 1.1`** by default (1.1× read better than 1.05× on the Ö Hydration ad); pitch stays the same.
   - The script prints each clip's place on the timeline. Use it to work out where a clip's lines land.
4. **Cut with basic-video-edit:**
   - Run `transcribe`, write `keeps.json`, run `cut --dry`, then `cut --qa`, exactly as that skill describes.
   - For a cut inside a sentence (a doubled word, a spliced line), find the exact spot with `$PY $UGC envelope raw.mp4 START DUR`. Cut at the quiet dip between syllables. Groq's word times drift 0.2–1s around stumbles, so don't cut on them blind.
   - If shortening a pause leaves a `SHORT` scrap, start the next keep about 0.15s before the next word.
   - **Make every join the same length.** basic's cut snaps each boundary to the nearest quiet spot, so some joins clip the next word and others leave dead air. A 0.2s difference is audible.
     - Measure the real silences with `$PY $UGC gaps raw.mp4 --from S --to E`.
     - Pin each keep (3rd value `0.02`) to end **0.15s after** the last word's sound and start **0.10s before** the next word's sound.
     - Where two sentences from different clips meet with no breath at all, add one after the cut: `$PY $UGC breath base.mp4 AT 0.15 -o base2.mp4`. It holds the frame, fills the pause with the clip's own room tone, and shifts the transcript.
     - **Never leave digital silence in a pause.** The room sound dropping to zero and back sounds like a thud ("ba-dunk"), and switching room tone on and off abruptly clicks. Fill gaps with faded room tone, and join pieces with a 0.04s `acrossfade`, not a hard cut.
   - **Listen for stray sounds at every clip join.** Omni clips often end or begin with a 0.2–0.4s half-word or noise after the last word (Silk & Snow: a burst after "price" that sounded like "forty", which read as "the four" and a doubled "hundred"). Groq leaves these out, so the cut keeps them. Check the last word's `envelope` at the end of each clip, and cut any loud burst that isn't the next word.
   - **Tighten the pauses inside sentences too, not just at the joins.** The Ö Hydration ad still felt slow after the joins were fixed. `gaps` misses pauses the speaker breathes through, so find them by loudness instead: scan `envelope` for dips of 0.2s or more between words.
     - Cut them down to about 0.08s inside a sentence and 0.15s between sentences, with the same room-tone fill and 0.04s crossfade as the joins.
     - Ö cut 16 of these, about 2.8s; with the 1.1× speed the ad went from 38.9s to 34.6s.
     - Usual spots: after a comma ("as I do,"), after a price ("$17.99 and…"), and before the closing line.
   - Use `--qa` on the cut. **Gate:** no `SHORT` segments, and no doubled or missing lines.
   - **Gate:** `$PY $UGC gaps base.mp4` shows no `TIGHT` or `DRAG` at any join. They're fine inside a sentence.
5. **Filler pass:** `$PY $UGC fillers base.mp4`.
   - Groq Whisper silently drops "uh" and "um". This re-transcribes the cut locally with a prompt that keeps fillers, and lists fillers and doubled words.
   - Confirm each one with `envelope`. To cut them, run basic's `cut` again on `base.mp4` with keeps in base time, which writes a new base.
   - **Gate:** no fillers or doubled words left.
   - **Audio gate:** `$PY $UGC audiocheck base.mp4`. It lists:
     - `DEAD`: digital silence. Refill it with room tone.
     - `CLICK`: a sample jump. Fix it with `$PY $UGC declick base.mp4 T -o base2.mp4`, which keeps the length.
     - `STRAY`: a sound the local pass hears that the transcript doesn't have. Confirm it with `envelope`, since many are mis-heard words or number spellings.
     - **Clunks at clip joins (not flagged):** Omni clips often start or end with a low thump (mouth or mic bump under 250Hz) in the gap between two clips' sentences. They're heard as "clunks". At every join, replace the gap between the last word and the next word with faded room tone, and high-pass the whole track at 80Hz. Silk & Snow v6 had thumps at 3 of 7 joins.
       - Cut a room-tone sample from a quiet spot in the raw clip (`ffmpeg -ss 0.02 -t 0.22 -i raw.mp4 -ac 1 -ar 48000 -c:a pcm_s16le tone.wav`).
       - Then run `$PY -I "$CUTROOM_CORE/engine/cutroom/ugc/fill_tone.py" base.mp4 base_f.mp4 tone.wav 4.12:4.34,5.06:5.25,...`, listing the gap at each join in base seconds. Fill the breaths added with `breath` too.
     - **Restarted numbers:** Omni sometimes restarts a number ("three hundred and, hundred and sixty-five"). Groq writes it as one number, so check every spoken number with the local pass using a prompt that spells numbers in words.

     Fix everything here, before assembling, so every later step is built on clean audio.
6. **Build the graphics, then assemble.**
   - **Sway (optional, on by default for AI talking heads):** `$PY $UGC sway base.mp4` writes `base-sway.mp4`, which drifts like a hand holding the phone. Use it as the spec's base. A locked-off AI shot reads as AI.
   - **Full-screen UI shots and pop-up overlays** are HTML pages rendered with `$PY $HTML page.html OUTDIR shot:dur ...`. Add `--alpha` for overlays, which become transparent `ov-<shot>.mov`. Start from `$CUTROOM_CORE/templates/ugc/overlay-example.html` (Rocket Money's hook text, cards, phone and call pill). The page defines `render(shot, t, dur)` and draws one frame.
   - Write `spec.json` (format below) and run `$PY $UGC assemble spec.json`.
   - It writes `<stem>-layered.mp4` and `<stem>-cap_transcript.json`, and prints each cutaway's and overlay's window and the B-roll share.
   - The caption transcript is trimmed so no caption carries onto a `nocap` screen. A lone word that starts within 0.35s of one is dropped, so it can't flash up as a ghost.
7. **Review the timing:** `$PY $UGC review <stem>-layered.mp4`, then `--from/--to` around each stretch of B-roll.
   - **Gate:** no `SHORT` shots, apart from a deliberate cut inside the brand's own clip such as a label-to-action cut.
   - **Gate:** in the 6fps contact sheet, every B-roll stretch shows only what its line says. Look for stray frames: a salt grinder, the next scene, a different product.
8. **Caption:** run basic's `caption` on the layered video with `<stem>-cap_transcript.json`.
   - Over bright product footage, use `--y 0.47 --pill`.
   - Fix product names with `--fix`.
   - Give at most one `--emph` phrase per sentence.
   - Preview first, as basic describes.
9. **Sound effects:** add an `sfx` list to the spec and run `$PY $UGC sfx captioned.mp4 spec.json captioned-sfx.mp4`.
   - **Keep them minor.** Most UGC ads need very few. Aim for about 3–5 cues in a whole ad, only on the graphics that matter most. Never add sounds under plain talking or on B-roll cuts, and don't add whooshes.
   - They're synthesised in code, so there's no licence to worry about: `pop` for a key card appearing, `tick` with `n`/`over` for a number counting up, `tap` for a finger on a button, `ding` for success.
   - They're mixed at `sfx_volume` 0.5 under the voice. Ask the user how the level sounds, because you can't hear it.
   - **Put each sound on the exact frame its graphic appears,** not on the spoken word. Take the time from the overlay's `at` plus its pop-in delay, and `tap` from when the circle starts drawing.
   - **No sound on notifications or banners** (bank alerts, Shop, Reminders, texts). They were cut from both the Ö Hydration and Protein Candy ads. The banner drop is enough.
   - Use `ding` once at most, on the single payoff number or success moment (Ö: the calculator landing on 72 cents).
10. **Finish:**
   - Make the end card with `$PY $UGC endcard card.png end.mp4`.
   - Then run `$PY $UGC finish captioned.mp4 end.mp4 final.mp4`.
   - The finished file should be under 30MB so it can be sent.
   - **Gate:** `$PY $UGC audiocheck final.mp4 --transcript base_transcript.json` shows no `DEAD` or `CLICK`, and every `STRAY` is explained. You can't hear the ad, so this is the audio check, plus asking the user to listen to each join.
   - Deliver one file and a contact sheet, with a short list of what changed.

## spec.json

```json
{"base": "base.mp4",
 "zoom": 1.2, "min_face": 0.8,
 "cutaways": [
  {"word": "squeeze", "dur": 2.0, "src": "refs/tray-squeeze.mp4", "off": 0.9, "lead": 0.2},
  {"word": "drizzle", "dur": 2.5, "src": "refs/plate-dip.mp4", "off": 0.6, "lead": 0.3, "nocap": 1},
  {"word": "ice", "after": 30, "dur": 1.45, "src": "refs/icecream.mp4", "off": 3.2}],
 "overlays": [
  {"at": 0, "src": "ov/ov-hook.mov"},
  {"word": "meditation", "lead": 0.05, "src": "ov/ov-med.mov"}],
 "sfx": [
  {"kind": "pop", "word": "meditation", "lead": 0.0},
  {"kind": "tick", "word": "eleven", "n": 7, "over": 0.8},
  {"kind": "ding", "at": 33.29}],
 "sfx_volume": 0.5}
```

- `word`: the word in the base transcript, matched case-insensitively with punctuation stripped. `after` skips earlier matches.
- `lead`: how many seconds before the word the shot starts. Use 0.1–0.3, so the shot lands just as the word is said.
- `off`: where in the source clip the shot starts. Choose it from a contact sheet of the source, not by guessing.
- `nocap`: no captions over this shot. **Avoid it.** Captions should run all the way through: a Silk & Snow cut had about 10s with none across three proof screens and a card, and they had to come back. Keep captions on over full-screen shots (see "Captions over B-roll"), and use `nocap` only on a short shot under about 1s.
- `overlays` and `sfx` take either `at` (seconds on the base timeline) or `word`/`after`/`lead` like cutaways. An overlay plays for its own length, so set that when you render it.
- The script enforces these automatically:
  - A gap of face shorter than `min_face` between two shots is closed by stretching the earlier shot.
  - Zoom never switches within 0.7s of a B-roll edge.
  - A shot's start point is pulled back so it ends 0.2s before its source does.

## Full screen or overlay

Six full-screen app shots in a row (a Rocket Money cut) felt like a slideshow. The brand's own ads keep the person on screen and pop the app up over them.

- **Full screen for 2–3 proof moments only:** the number that shocks ("eleven", the yearly total), the one thing the product does that nothing else does (the cancel flow), and maybe one more.
- **Everything else is a pop-up over the face:** a notification-style card, a stack of charge cards, a phone with the screen scrolling, a call-on-hold pill. Each one appears on the word that names it and leaves before the next.
- **Hook text** at the top for the first ~3s, in the creator's own words.
- **Animate proof screens so the number lands on the word.** Start a counter partway (4→11, not 1→11) so it climbs in under a second, then zoom in on the total and circle it.
- Full-screen B-roll plus overlay time together should cover about 35–55% of the runtime.

## Timing rules

- **Face flashes look like mistakes.** No face shot under 0.8s between B-roll shots, and no shot of any kind under 0.6s.
- **B-roll shots run 1–2.5s.** A quick run of 3 shots of about 1.2s each works for a list ("eggs, vegetables, whatever's in the pan"). If two cutaways come from the same source clip back to back, merge them into one continuous shot.
- **B-roll covers about 35–55% of the runtime.** Top creator ads sit near 55%. A face shot that also shows the product counts as product time.
- **Show the product in the first 2–3s**, either in the A-roll frame or on a B-roll shot.
- **Label, then action:** a hand holds the label to the lens for 0.5–1.5s, then a top-down close-up of the product in use. Name the product on the label shot.
- **Use cuts that are already inside a source clip.** Find them with `review` on the source. Start just after one and end before the next, so a split second of the previous or next scene doesn't show.
- **End on the face** with a verdict or a small ask and the product in frame, then a 1.5–2s end card.
- **Punch-ins:** 1.2× on every other sentence, aimed slightly above centre. They're there to cover jump cuts, not as decoration.

## B-roll sourcing (in order)

1. The brand's own footage: its ads, YouTube demos, App Store screenshots, and product photos from its site.
2. The brand's own social posts. Skip any with burned-in captions.
3. Creators' partnership ads the brand runs. Flag the rights to the user once and let them decide. Don't silently swap the footage out.
4. AI close-ups of hands and the product. Start them from the real product photo so the labels stay correct, and get credit approval first.
5. **Seedance 2.5 montages** for list lines and places ("Netflix, Spotify, my gym"). Use `generate_video`, `model: "seedance-2.5"`, 9:16, 720p, `generateAudio: false`, with one timed shot per item, `HARD CUT to` between them, and the prompt format from Cospark's `production/broll-shot-prompts`.
   - Tested on Rocket Money v4: 4s, 3 shots, 14.57 credits, about 5 minutes. It looked like real phone footage.
   - The cuts don't land where you ask. Asked for 1.33/2.66s, they came at 1.83/2.92s. Find them with `review` (or `scdet`) and trim each shot to its word.
   - Ask for screens with "no readable words or logos" and keep real app UI to the HTML renders, because AI screens garble text.
   - Make the montage file a few frames longer than its cutaway slot, or the face flashes for one frame at the end.
6. **Omni montages of the ad's own character** (`generate_video_with_references`, `gemini-omni`, the character still as the reference). Use them for lifestyle shots with the creator, their pet or their room, and when Seedance fails. See the competitor-copy flow above.

Never use AI lifestyle stills animated with a push-in, and never use B-roll with someone else's captions burned in.

## Captions over B-roll

- Keep one fixed y position for the whole ad. Choose it so it clears the product on the counter in the A-roll.
- With pop-up cards in the lower third, put captions on the chest (`--y 0.5`) and the cards from about 61% down, so they never collide. At 0.47 they touched the chin on punch-ins.
- Use `--pill` whenever B-roll is bright: white UI, plates, a beige background.
- **Captions never drop out**, including over full-screen proof shots and screens the viewer needs to read.
  - On a white or light screen, use `--pill` (a dark pill) or move the caption just below the light area for that shot.
  - When a pop-up card covers the lower half, move the caption up above the card while it's on screen, then back.
  - **Gate:** check a frame from every second of the captioned video. Each one with speech shows a readable caption.

## Not in scope

Music and colour grading. For talking-head shorts with graphics, use video-edit. Build app or messaging screen demos as HTML renders (above) first, then use them as B-roll.
