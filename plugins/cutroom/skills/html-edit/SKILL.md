---
name: html-edit
description: The way every Cutroom video is built and rendered. The edit is an HTML composition (a page per reel, a small HTML file per graphic) rendered with `cutroom compose`. Use for every edit, re-edit, new version or round of review notes on a reel, ad or short, together with the project's editing skill: that skill decides the cut, storyboard, look, caption wording and sound; this one is how graphics, layouts and captions are drawn and how the video is rendered. Skip it only when the user asks for the Python renderer.
---

# HTML edit

The edit is a folder of HTML: `videos/<name>/edit/<slug>/`. One page (`index.html`) holds the timeline: footage, one host per graphic, captions, sound. Each graphic is its own file in `compositions/`. A fixed renderer (Hyperframes, pinned by the CLI) plays the page frame by frame into `edit/<slug>_vN.mp4`. Nothing is drawn in Python.

```
edit/<slug>/
  index.html              the timeline: every timed element has data-start and data-duration
  compositions/<id>.html  one graphic each
  assets/                 footage, cutouts, sound, images, fonts used by this edit
edit/<slug>_vN.mp4        renders (publish these as usual)
```

## Commands

`CR='node "$CUTROOM_CORE/bin/cutroom.mjs"'`, run from the project folder.

| | |
|---|---|
| `$CR compose init "videos/<name>" <slug>` | start the folder (`--size 1920x1080` for landscape) |
| `$CR compose check "videos/<name>" <slug>` | lint, layout and audio checks. Fix every error before rendering |
| `$CR compose frames "videos/<name>" <slug> --at 1,8.5,20` | stills in `edit/<slug>/frames/`; Read them. `--against edit/other_v3.mp4` pairs each with a reference |
| `$CR publish live "videos/<name>" <slug>` | publishes the edit for review as a live preview, no render. Every version starts this way |
| `$CR compose render "videos/<name>" <slug>` | only when the user wants the MP4: writes `edit/<slug>_vN.mp4` for the latest live version (then `publish render` it). `--start 12 --end 18` renders just that span to `edit/<slug>/renders/` for a quick look |
| `$CR compose preview "videos/<name>" <slug>` | a live preview with a timeline at http://localhost:3002 for the user; `--stop` ends it |
| `$CR compose hyperframes "videos/<name>" <slug> -- <command>` | any other HyperFrames command, pinned and with telemetry off: `catalog --query "film grain" --json`, `add <name> --json`, `lint`, `timeline --json` |

## Flow

1. Cut the A-roll, transcribe and pass the storyboard gate exactly as the project's editing skill says. The storyboard's beats and cue times are what you build from.
2. `compose init`, then prepare `assets/`:
   - `aroll.mp4`: the cut A-roll, re-encoded with a keyframe every second so seeking is exact: `ffmpeg -i edit/base_v1.mp4 -an -c:v libx264 -crf 18 -g 30 assets/aroll.mp4`.
   - `voice.m4a`: the cleaned voice track. Sound effects as their own short files with the gain baked in.
   - A head cutout over a graphic is a transparent WebM (`-c:v libvpx-vp9 -pix_fmt yuva420p`) made from the person matte, cropped to the band it covers.
   - Images, logos and fonts the graphics use. Reference everything as `assets/...`.
3. Write `index.html` and one file per graphic. Set the root `data-duration` to the reel's length.
4. `compose check`, then `compose frames` at the middle of every beat and 0.1s after every cue. Read the frames and fix what's off before rendering.
5. Write the caption and script files (`edit/<slug>.caption.md`, `edit/<slug>.script.md`), then `publish live "videos/<name>" <slug>` and stop. The user watches the page itself in the app; the review timeline shows its footage, graphics, captions and sound as lanes. Every file the page uses must sit inside `edit/<slug>/` and video files must stay under 16 MB each (the A-roll plays from its 720p preview).
6. Each round of notes: edit the HTML, re-check the frames you touched, `publish live` again for the next version.
7. Render only when the user asks for the video file (download, export, save, post): `compose render "videos/<name>" <slug>`, then `publish render "videos/<name>" edit/<slug>_vN.mp4`. It lands on the latest live version, not a new one. The Render button in the app does the same on the user's Mac.

## The page (`index.html`)

- Root: `<div id="root" data-composition-id="main" data-start="0" data-duration="…" data-width="1080" data-height="1920">`.
- A timed element has `class="clip"`, `data-start`, `data-duration`, `data-track-index` and an `id` that reads well: ids become the labels in the review timeline (`face-hook`, `sfx-click-match`).
- Footage: `<video class="clip" muted playsinline src="assets/aroll.mp4" data-start="5.72" data-duration="31.76" data-media-start="5.72">`. `data-media-start` is where in the file it starts. Time the `<video>` itself, never a wrapper. Position and crop it with CSS on a wrapper with `overflow: hidden`: one `<video>` per stretch of a layout (full face, inset box, cutout), all reading the same file.
- A graphic: `<div id="cost" class="scene" data-composition-id="cost" data-composition-src="compositions/cost.html" data-start="33.72" data-duration="3.76" data-track-kind="graphics" data-layout="inset" data-width="1080" data-height="1920">`. `data-layout` (`face`, `inset`, `full`, `stack`) colours the beat in review.
- Captions: one host with `data-track-kind="captions"` running the whole reel.
- Sound: `<audio id="voice" class="clip" src="assets/voice.m4a" data-start="0" data-duration="…" data-volume="1">`, and one `<audio>` per sound effect at its cue. Every `<audio>` needs an `id`. Keep the footage `muted`.
- Layer with `z-index`: backdrop, footage, graphics, inset and cutout, captions, title.

## A graphic (`compositions/<id>.html`)

```html
<template>
  <style>
    #root { position: absolute; inset: 0; }
    #cost-card { position: absolute; left: 70px; top: 220px; … }
  </style>
  <div id="root" data-composition-id="cost" data-width="1080" data-height="1920">
    <div id="cost-card">…</div>
  </div>
  <script>
    (() => {
      const tl = gsap.timeline({ paused: true });
      tl.fromTo("#cost-card", { opacity: 0, scale: 1.12 }, { opacity: 1, scale: 1, duration: 0.3, ease: "expo.out" }, 0.4);
      window.__timelines["cost"] = tl;
    })();
  </script>
</template>
```

- The host id, the file's root `data-composition-id` and the `window.__timelines` key are the same word. Times inside are seconds from the graphic's own start.
- Prefix every id and class with the graphic's name; all files end up in one page.
- Wrap each script in `(() => { … })()`.

## Rules the renderer needs

- All motion comes from a paused GSAP timeline registered on `window.__timelines`. No `Date.now()`, `Math.random()`, timers, CSS animations or transitions: a frame must look the same whenever it is drawn.
- Use `fromTo`, never `from`. Don't tween `display` or `visibility` on a `.clip`; use opacity.
- Don't put a CSS `transform` on an element GSAP also transforms. Put the static transform on a wrapper.
- Never call play or pause on media.
- Anything that changes by rule (a counter, a chart drawing, a typing line, a state machine) is a `render(k)` function called from one linear tween's `onUpdate` that spans the graphic:
  `const clock = { k: 0 }; tl.fromTo(clock, { k: 0 }, { k: D, duration: D, ease: "none", onUpdate: () => render(clock.k) }, 0);`
- Captions: one absolutely positioned element per caption group, switched with `tl.set(el, { opacity: 1 }, start)` and `tl.set(el, { opacity: 0 }, end)`. Generate that file from the transcript with a short script; don't hand-write it. Give each caption element `data-s` and `data-e` (seconds from the captions' start) and drive the timeline from them: publish reads them to fill the review's transcript when the storyboard has none.
- Fonts: Inter and the other bundled families work by name. Any other font goes in `assets/fonts/` with an `@font-face`. A font that only exists on this Mac will not render in the cloud.
- Blur filters make rendering slower. Prefer opacity and scale for entrances unless the look needs the blur.
- Colours and fonts come from the project's `brand.json`; read it and write the values into the CSS.

## HyperFrames reference and effects

The `hyperframes` skill has the renderer's full contract and its motion, caption and overlay techniques; `hyperframes-cli` has every command; `hyperframes-registry` has about 450 ready-made blocks and components. Before hand-building a named effect (a glitch, grain, a transition, a chart), use the user's own components first, then search the registry with `compose hyperframes … -- catalog`. An installed item is ordinary source: restyle it to `brand.json` and the project's look. Those skills are reference only: where they disagree with this skill, the project's editing skill, `instructions.md` or the user's preferences, those win.

## What carries over from the project's skill

The script, the cut, the storyboard gate, caption wording and emphasis, sound choices, safe zones, the polish rules and the review loop. Only the drawing changes: where that skill says to build a beat with the Python engine, build it here as a graphic file.
