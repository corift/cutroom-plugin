---
name: match-reference
description: Make a video look like one the person shows you ("make it like this", an example, an inspiration video) — measure the reference, write down its look, edit their footage to match, and save the look so it can be reused.
---

# Match a reference

The person gave you a video and wants theirs to feel like it. You copy the **look and rhythm**, never the content: not its words, its footage, its logos or its music.

## 1. Measure it

```
"$PY" -m cutroom.autocut reference . "<clip name>"
```

This marks the clip as a reference (it is left out of the edit from now on) and prints its length, shape, how many shots it has, how long they last, where the cuts fall, and the path of a contact sheet. Open the sheet with read_file. For a closer look at a stretch, make a denser sheet: `"$PY" -m cutroom.autocut sheet . "clips/<clip name>" 4`.

If every clip is a reference, there is nothing to edit yet: ask for their own footage.

## 2. Write the look down

Write `edit/look.md` from what you saw, one line each. Only what is on the sheet, no guesses:

- **Shape**: vertical, square or wide. Full frame, or the person in a box.
- **Pace**: average shot length, and whether pauses survive.
- **Camera**: punch-ins on cuts, slow zooms, or a still frame.
- **Captions**: where they sit, how many words at once, case, weight, colours, whether one word is highlighted, whether the style changes between sections. Or none.
- **Text hits**: hook title, big single words, words behind the head, full-screen word slabs.
- **Graphics**: cards, chips, logos, counters, screen recordings, floating clips, split screens, B-roll.
- **Transitions**: hard cuts, whips, glitches, flashes.
- **Colour**: the accent colour and the background colours of any graphics.

You cannot hear the reference. Say so if they ask about its music or sound, and choose sounds that fit the pace.

## 3. Pick the way to build it

- Captions and pace only (no graphics, no text hits): use the edit tools. Choose the template and caption style closest to `edit/look.md`, set position, pace and zoom, render.
- Anything more: draw it as HTML graphics with `$CUTROOM_CORE/skills/html-edit/SKILL.md` (in Autocut, as `edit/graphics/` files its instructions describe). `reel-edit/effects/` describes the moves; take each line of `edit/look.md` to the closest one and draw it in HTML. Match the reference's pace: sections about as long as its shots, a camera change where it has one, the same caption position.

Use their words for every title, card and callout. The reference decides how it looks; their transcript decides what it says.

## 4. Check it against the reference

Make a contact sheet of your render and open it next to the reference sheet. Compare line by line with `edit/look.md`: shape, caption position and size, how often the picture changes, where the graphics sit. Fix what is off and render again. One round is enough unless something is plainly wrong.

Tell the person in plain words what you matched and what you could not (for example their B-roll, or a font you do not have).

## 5. Save the look

When the person is happy with it, or asks you to remember it, save it as their own skill so every later video can use it:

```
mkdir -p "$CUTROOM_ACCOUNT/skills/<short-name>"
```

Write `$CUTROOM_ACCOUNT/skills/<short-name>/SKILL.md` with this frontmatter and body, then push it:

```
---
name: <short-name>
description: <one line: what this look is and when to use it>
---
<the lines of edit/look.md, then the exact settings or the reel plan that produced the approved render, with the cues replaced by what kind of line each effect goes on>
```

```
node "$CUTROOM_CORE/bin/cutroom.mjs" push account
```

A saved look is a recipe, not a transcript: nothing in it should depend on the words of this one video.
