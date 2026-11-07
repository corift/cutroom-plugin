---
name: omni-talking-head
description: Write prompts for Gemini Omni talking-head (UGC creator) clips using our tested format, which splits the dialogue from the actions, uses timed eye cues against the uncanny stare, and names captions only once to avoid burned-in captions. Use whenever generating or retaking a spoken Omni clip with generate_video_from_frames, a first-line test, or the rest of a script. It overrides the prompt template in Cospark's models/gemini-talking-head guide, but their other guidance (first-line test, credits, inspection) still applies.
---

# Omni talking-head prompts

These are tested findings from producing Omni clips for spec ads. They replace the single-paragraph template in Cospark's `models/gemini-talking-head` guide. Keep following Cospark's workflow for everything else: the first-line test, approval before retakes, and polling.

## The format

```text
He speaks with a clear, standard American accent. He talks to the camera with big pitch swings and clear, punchy enunciation, like he's telling his buddy something he just found out, a little in disbelief at himself.

Dialogue, spoken verbatim:
"So I juuuust found out I've been paying for a meditation app since January... and I opened it ONE time."

Actions while speaking:
0-1s: as he starts the story, he glances up and to the side for half a second like he's remembering, then looks back at the camera and blinks.
2-3s: he tilts his head as he names the app, and blinks.
4-5s: a disbelieving half laugh as he admits how often he used it.

He blinks every couple of seconds, like a normal person talking, and his eyes move naturally. No captions or on-screen text appear while he speaks. Keep the lighting and everything else the same.
```

The prompt has four parts, in this order:

1. **Vibe line.** Put the accent first, always "clear, standard American accent", because Omni drifts Australian. Then the energy and who they're talking to. Telling a friend news works, and complaining or venting comes out flat.
2. **`Dialogue, spoken verbatim:`** with the quoted line on its own, and nothing else in that block.
   - It's fine to stretch one word ("juuuust"), put one word in caps, and use "..." for a beat.
3. **`Actions while speaking:`** with two or three cues. Tie each one to a time and the word it lands on.
   - Include **one early glance away** (up and to the side, like they're remembering) and **blinks tied to words**. That's what breaks the locked, unblinking stare.
   - Omni drops some cues, so don't stack four or more.
4. **Closing line, exactly as written above.** It's the only place captions are mentioned.

## Why these rules

- **Keep the dialogue on its own line.** When the line was inside the description paragraph, Omni burned it in as captions.
- **Don't quote the dialogue in the action cues.** Write "as he says the monthly amount", not "on \"ninety bucks a month\"". Two takes of clip 5 quoted three phrases in the cues, and both came back with exactly those phrases burned in as captions. The same line with no quotes in the cues came back clean. A single quoted short phrase in clip 1 was fine, but the safest habit is to describe the moment.
- **Name captions once, at the end only.** The take that said "audio only, never shown as text" and "no captions, subtitles or on-screen text at any point" got captions. Every mention of text pushes it toward drawing text, so never put "text" near the dialogue.
- **Don't write "raw phone footage" or "TikTok".** It pulls up the captioned-TikTok look.
- **Use timed eye cues.** Clips with only "He blinks naturally" often held an unblinking stare into the lens, which looked uncanny. With a timed glance away and blinks tied to words, the same clip came back with about four blinks in 7 seconds and a natural look away.
- **Caps aren't the problem.** A clean take had "ONE" in caps.

How sure we are: 7 of 8 split-format takes came back with no captions. The timed eye cues are tested on one clip so far. Update these numbers as more clips come in.

## Duration

- **Pacing: about 3.5 words a second, not faster.** Six Northern Fitness clips measured 2.9–3.8 w/s, with 0.2–0.4s before the first word. Lines with prices and numbers ("four forty-nine… fifty bucks for eight") ran slowest, and two 7s clips with 21–24 words got cut off.
- **Word budget per clip: `words ≤ 3 × seconds`.**
  - 5s → up to 15 words, 6s → 18, 7s → 21, 8s → 24.
  - Count numbers as they're said ("four forty-nine" is 3 words), and take 2 words off for a line with a price or a list.
- **Split the script into short clips and fire them all in parallel.** Aim for one sentence or clause per clip, 5–6s and 12–18 words. Don't go under 4s, because the lead-in and the tail eat about 0.6s.
  - Short clips rarely get cut off, retakes are cheaper, and each one gets its own gesture.
  - More joins are fine: they all start from the same frame, and punch-ins and overlays cover the jump cuts.
- **Cost:** 1.5 credits a second. A 5s clip is 7.5 credits.
- **Watch the last word.** If its transcript end time is within 0.3s of the clip length, check that the word isn't cut off.
- **Give every clip one hand cue.** For example, palms up in disbelief, a thumb back at the product, one finger up for "the only", or an open hand toward the camera for the ask. Clips without one sit still, and clips with one read as far more natural.

## Checking every take

- **Captions:** check the lower half of the frame at 4 fps, because a 1-second contact sheet can miss them.

  ```bash
  ffmpeg -i clip.mp4 -vf "fps=4,crop=720:300:0:850,scale=140:-1,tile=14x2" -frames:v 1 cap.jpg
  ```

- **Stare:** check the face at 4 fps for blinks and glances.

  ```bash
  ffmpeg -i clip.mp4 -vf "fps=4,crop=720:820:0:0,scale=140:-1,tile=14x2" -frames:v 1 face.jpg
  ```

- **Dialogue:** compare the transcript word for word against the script.
- **Accent:** you can't hear it. Tell the user to listen to every new clip for the accent before it goes into an edit.

## Characters

Make starting frames with **Nano Banana Pro only, never GPT Image**: GPT Image faces read as fake.

Nano sometimes keeps the real creator's face, so compare every swap with the reference frame. If it kept the face, try a different reference frame rather than another model.
