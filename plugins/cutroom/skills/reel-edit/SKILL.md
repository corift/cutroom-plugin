---
name: reel-edit
description: Edit a talking-head clip like the viral Claude Code reels — jump cuts, a punch-in on every cut, a different caption style per section, giant words behind the head, full-screen word slabs, a transcript split screen, floating reference clips with pointer captions, screen-recording cuts, background swaps, videos floating around the person, popped cards and chips, whip / glitch / flash transitions, and a sound on every hit. Use only when the user asks for this style by name ("reel-edit", "viral style", "like the viral Claude Code reels") or names an effect in effects/. Never for a project that has its own editing skill unless the user asks; for a normal short, use the project's skill. Works on any vertical or landscape talking head (real or AI); everything is cued from the transcript.
---

# Reel edit (the viral reels look)

The look we pulled from a study of the Claude Code editing reels (Oct 2026): no pause survives, the camera moves on every cut, the captions change style from section to section, and the turns in the script get a loud visual and a sound.

This look breaks the house **Polish rules** on purpose: bounces (`back()` overshoot), tilted stickers, slams and pops are allowed **in this look only**. The Polish rules in the shorts `video-edit` style guide stay as they are for every other edit. Don't carry these moves into a non-reel edit.

Each effect has its own file in `effects/`. Read the ones you plan to use before writing the plan.

## How it works

One script renders the whole edit from a plan you write after reading the transcript:

```
REEL="$CUTROOM_CORE/templates/shorts/reel_edit.py"
python3 "$REEL" edit/reel_v1.mp4 --video SRC.mp4 --words transcript.json --mask mask.mp4 --plan edit/plan.json
python3 "$REEL" edit/reel_v1.mp4 ... --preview 1.5,6.2,12.0     # stills at output seconds, next to OUT
```

- `--words`: `cutplan.transcribe` output (`{"words": [{"word", "start", "end"}]}`) or `[{"w", "s", "e"}]`.
- `--mask`: the person mask of the **source** (not a cut), white person on black. It's needed for words behind the head; without it the words go over the person. See `effects/behind-head.md` for how to make one.
- `--face-y`: where the face sits in the source, as a fraction of its height (0.34 default). Punch-ins hold the face at that height.
- With no `--plan`, an automatic plan is built from the sentences (sections every ~3s, rotating captions, zooms and transitions) and saved as `OUT.plan.json`. Use it as a first draft, never as the edit.

## The plan

Every time in the plan is a **cue**: a phrase from the transcript (`"design file"`; the last word may be a prefix), found after `after` (another cue or source seconds), or a number of source seconds. `until` can also be `"+0.8"`: seconds after the cue. Write cues from what the speaker actually says, never from fixed times.

```json
{
 "keep": [[0.0, 4.42], [4.42, 7.12]],
 "keys": ["claude", "silences"],
 "sections": [
  {"at": "okay", "caption": "pop"},
  {"at": "like", "caption": "serif", "zoom": 1.3, "transition": "whip"}
 ],
 "moments": [
  {"do": "punch", "at": "claude", "until": "entire", "zoom": 1.8},
  {"do": "behind", "at": "entire", "until": "like", "text": "ENTIRE", "sub": "this whole video"}
 ],
 "sfx": [{"at": "silences", "name": "click", "gain": 0.7}]
}
```

- **keep** (optional): the source stretches to keep, at sentence level (`effects/jump-cuts.md`). Without it, every pause over 0.22s is cut automatically.
- **keys**: words that get the accent in keyword caption styles, for the whole video. Sections can add their own `keys`.
- **sections**: each starts on its cue and runs to the next. Each sets `caption` (style), `zoom` (base framing), `transition` (into this section) and optional `keys`, `cy` (caption height), `direction` (whip: 1 or -1).
- **moments**: effects on a cue, by `do`. One file each in `effects/`.
- **label** moments (`{"do": "label", "at": …, "until": …, "text": "screen cut"}`) put an effect's name at the top, for showreels and tests.
- **sfx**: extra sounds. Effects and transitions already add their own (`effects/sound.md`).

## Fonts

Everything in this look is set in TikTok Sans, which ships with Cutroom (`assets/fonts`, SIL Open Font License), so it renders the same on every machine. Weights run from 300 to 900 through `core.display(size, weight)`. To use another face, set `"display"` in the project's brand kit `fonts` to a font file. A variable font keeps the weights; a static one is used as is. Characters the font lacks, such as ✓ and ✂, come from a system symbol font.

## Workflow

1. **Transcribe** the source (`cutplan.transcribe`, Scribe preferred) and read the whole thing.
2. **Mark the beats**: the hook, each claim or step, the payoff, the CTA. Each beat becomes a section; the biggest words become moments.
3. **Pick a moment per beat**, at most one big one (behind, slab, split, count) per ~4 seconds. Fit the effect to the line:
   - a claim about scale or a single word to hit: `behind` or `slab`
   - "it wrote / it read / every word": `split`
   - a file, setting or rule: `card`
   - a number, "every / all / checked": `count`
   - feedback, memory, notes: `note`
   - "comment X": `comment`
   - a brand or tool named in the hook: `logo` or `chip`
   - someone else's edit, video or post: `clip`, with a `point` caption saying what to look at, or `refs` with `inset`
   - "watch my screen", a setting or a button: `screen`
   - a real thing named in the script (a place, a launch, a page): `slide`, with the actual photo or clip
   - a turn, "pulls me out", "all my videos": `swap` (a colour, or a `wall` of their videos)
   - several demos, "my results", "the final cut": `refs` with `fan`, `float`, `fly` or `result`
   - "every video you make", "all my videos": `orbit`, their videos circling the head
   - a name or reveal that should feel like a stage moment: `spotlight`
4. **Write `edit/plan.json`** and render stills at the start of every section and moment (`--preview`).
   - **Gate:** no caption over the chin or under a card, no burned-in text from the source showing (hide it with a `punch` or `blur`), no section without a camera change.
5. **Render**, then watch it at phone size.
   - **Gate:** every transition has a sound, nothing pops in silence on a big hit, the CTA is readable for at least 1.5s.
6. **Publish** the render for review: `node "$CUTROOM_CORE/bin/cutroom.mjs" publish render "videos/<name>" edit/reel_vN.mp4`. Notes become the next version. Variations (other hooks, CTAs, lengths) stay in this same video folder with their own slug: `publish render "videos/<name>" edit/trials_v1.mp4 edit/buy_now_v1.mp4`, never a new `videos/` folder.

## Rhythm rules

- Rotate caption styles by section: `pop` → `serif` → `pop` → `sticker`. Never the same style twice in a row.
- A transition on roughly every other section, never two of the same kind in a row. Whip for a turn, glitch for a reveal, flash for a hard stop.
- A camera change on every cut: alternate the zoom between sections (1.0 / 1.3 / 1.1 / 1.35). Jump cuts inside a section punch in by 12% on their own.
- Captions hide while a `behind`, `count` or `comment` word is up (set `"captions": true` on the moment to keep them).

## Extending

These files ship with Cutroom. To change the look for yourself or a project, add a skill with the same name (`reel-edit`) to your account or project skills; it replaces this one. To add an effect, add a file to `effects/` in your copy and the matching code to your own render script. Don't edit the core files.
