---
name: hyperframes-registry
description: About 450 ready-made HyperFrames blocks and components (transitions, overlays, titles, kinetic type, captions, charts, camera moves, glitch, grain) installed as editable source. Search it before hand-building a named effect the user's own library doesn't have, then restyle it to the project's look. Reference only, below the user's own components and Cutroom's skills.
---

> **In Cutroom.** Taken from HyperFrames 0.9.85 (https://github.com/heygen-com/hyperframes, Apache-2.0, [license](../hyperframes/LICENSE.txt)), trimmed, with this note added. It explains how HyperFrames works and ranks last. Who decides, first to last: the user in this chat, the project's `instructions.md`, the account's `preferences.md`, the user's own skills and `library/` components (project, then account), Cutroom's skills (`html-edit` and the project's editing skill), then this. Where they disagree on workflow, look, motion, captions or sound, they win, and anything taken from here is restyled to the project's look.
>
> - The workflow is `html-edit`'s: `cutroom compose init|check|frames|preview|render` stand in for `init`, `check`, `snapshot`, `preview` and `render`, and the storyboard and render gates stand in for the story, `SPEC.md` and `REVIEW.md` steps here.
> - Any other command (`catalog`, `add`, `lint`, `timeline`, `media-treatment`, `beats`, …) runs as `node "$CUTROOM_CORE/bin/cutroom.mjs" compose hyperframes "videos/<name>" <slug> -- <command> <args>`: the pinned release, in the edit folder, telemetry off. Read every `npx hyperframes <command>` below that way.
> - Skip the usage note and anything that reports back or sells: `events`, `usage`, `feedback`, `share`, `publish`, `cloud`, `lambda`, `cloudrun`, `skills`, `upgrade`, `open`, `catch-up`, and the HyperFrames desktop app, Studio and Framey. Cutroom renders and reviews in its own app.
> - Skills named here that aren't installed (`/media-use`, `/slideshow`, `/figma`, `/reverse-any-video`, `/style-sampling`, `/remotion-to-hyperframes`) aren't available, nor are the frame presets and bundled scripts.

# HyperFrames registry

Starting from an item is faster and usually better than writing the effect yourself, and an installed item is ordinary source in your project: change it, cut it down, restyle it.

## Find and install

There is no `hyperframes registry` command; searching is `catalog`, installing is `add`.

```bash
npx hyperframes catalog --query "<what the beat should do, in English>" --json
npx hyperframes add <name> --json        # prints the written files and the mount snippet
```

- Query in English even when the video is not: the catalog is indexed in English, and another script returns `No searchable words in query`, which is not a gap.
- Search is local and sends nothing. The default `words` tier only finds items that reuse your words; `--on-device` ranks by meaning after a one-time ~33 MB download. Offer that download and let the person decide; never enable it silently. The `--json` envelope names the tier that answered.
- Narrow with `--type block|component` and `--tag <tag>`. `add <tag>` installs every block with that tag; dependencies install first. `add` needs the network even for an item installed before; search works offline from the cached manifest.
- Nothing fits: report it before you hand-build, on either tier, unless the person said no to usage notes. `catalog --query` prints the line (`report_gap` in `--json`): `npx hyperframes feedback --search-miss --wanted "<the move you needed>" --tier <tier>`. Describe the effect in your own words, not their query or an item name you imagined; their query is never sent.

Tiers, `dropped` and `unindexed`, stale indexes, offline behaviour: `references/search.md`.

## What's in it

| Blocks: a scene with its own timeline | Examples |
| --- | --- |
| Transitions | `beat-freeze-cut`, `chromatic-radial-split`, `cinematic-zoom` |
| Overlays and lower thirds | `camcorder-hud`, `editorial-flash-overlay`, `lt-clean-bar` |
| Title cards and kinetic type | `canopy-part-title`, `code-slice-hero` |
| Social, chat and UI cards | `ai-chat-reveal`, `chatgpt-exchange` |
| Code, charts, data and maps | `code-diff`, `bar-chart-race`, `data-chart` |
| 3D, shader and backgrounds | `app-showcase`, `aurora`, `blob` |

| Components: a snippet merged into your scene | Examples |
| --- | --- |
| Motion primitives and text effects | `agent-cursor`, `blur-in`, `bottom-up-letters` |
| Caption styles | `caption-clip-wipe`, `caption-editorial-emphasis` |
| Camera moves | `camera-shake`, `camera-scan-gate` |
| Product demo and UI props | `before-after-wipe`, `browser-device-stage` |
| Textures, particles and effects | `ascii-render-pass`, `grain-overlay` |

## Wiring

- **Block**: installs to `compositions/<name>.html`. Mount it with `data-composition-src`, `data-composition-id` matching the block's own id, `data-start` and the `data-duration` you need; the snippet `add` prints is the starting point. `references/wiring-blocks.md`.
- **Component**: installs to `compositions/components/<name>.html`. Copy its markup, `<style>` and script into your scene, and follow its comment block if it hooks into your timeline. `references/wiring-components.md`.
- Take the largest unit that fits, then edit it. Keep an installed item's ids prefixed as they are, so two items can't collide.
- An item keeps its own variables; set them for one mount with `data-variable-values` on its host (`add --vars '{"title":"…"}'` writes that), and point its colour and font variables at your brand's.
- Beat-synced blocks take hit times from `npx hyperframes beats --json`: the beat times minus the mount's `data-start`.
- Install paths come from `hyperframes.json` (`references/install-locations.md`).

