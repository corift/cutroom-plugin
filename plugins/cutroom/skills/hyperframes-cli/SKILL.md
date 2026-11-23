---
name: hyperframes-cli
description: HyperFrames CLI reference for a Cutroom edit - lint, check, snapshots, timeline edits, media treatment, beats and transcribe, and what to do when a command fails. Commands run through cutroom compose. Reference only, below the user's own skills and Cutroom's.
---

> **In Cutroom.** Taken from HyperFrames 0.9.85 (https://github.com/heygen-com/hyperframes, Apache-2.0, [license](../hyperframes/LICENSE.txt)), trimmed, with this note added. It explains how HyperFrames works and ranks last. Who decides, first to last: the user in this chat, the project's `instructions.md`, the account's `preferences.md`, the user's own skills and `library/` components (project, then account), Cutroom's skills (`html-edit` and the project's editing skill), then this. Where they disagree on workflow, look, motion, captions or sound, they win, and anything taken from here is restyled to the project's look.
>
> - The workflow is `html-edit`'s: `cutroom compose init|check|frames|preview|render` stand in for `init`, `check`, `snapshot`, `preview` and `render`, and the storyboard and render gates stand in for the story, `SPEC.md` and `REVIEW.md` steps here.
> - Any other command (`catalog`, `add`, `lint`, `timeline`, `media-treatment`, `beats`, …) runs as `node "$CUTROOM_CORE/bin/cutroom.mjs" compose hyperframes "videos/<name>" <slug> -- <command> <args>`: the pinned release, in the edit folder, telemetry off. Read every `npx hyperframes <command>` below that way.
> - Skip the usage note and anything that reports back or sells: `events`, `usage`, `feedback`, `share`, `publish`, `cloud`, `lambda`, `cloudrun`, `skills`, `upgrade`, `open`, `catch-up`, and the HyperFrames desktop app, Studio and Framey. Cutroom renders and reviews in its own app.
> - Skills named here that aren't installed (`/media-use`, `/slideshow`, `/figma`, `/reverse-any-video`, `/style-sampling`, `/remotion-to-hyperframes`) aren't available, nor are the frame presets and bundled scripts.

# HyperFrames CLI

Run `npx hyperframes <command>` as above, never a project's own scripts or wrapper unless the person names that command. A job with no TTY pins the release with the launcher's `--cli-version <exact-version>`, taking the version from the person or from `--cli-version latest --version`, never from the project's files and never a floating install (`references/unattended.md`). It needs Node.js 22+ and FFmpeg. Every command has `--help`; most take `--json`, and a failure prints `✗ …`, a `Fix:` line and exits non-zero.

A `--json` result may carry `_meta.updateNotice`: a newer HyperFrames release is out. Pass it to the person once per conversation, in your own words, at a natural pause; updating is theirs to decide.

## Commands by job

| Job | Commands |
| --- | --- |
| Start | `init <dir> --skip-skills` (blank; `--example <name>` only when asked), `capture <url>` |
| Read a project | `info`, `compositions`, `timeline --json`, `docs <topic>` |
| Check it | `lint` while writing; `check --json` as the gate (lint, runtime, layout, contrast) |
| Look at it | `snapshot` (`--at <t,…>`, `--range START,END`, `--composition <id>`, `--zoom`, `--angle`, `--against <video>`), `keyframes`, `compare`, `audio` |
| Edit the timeline | `timeline` with `move`, `trim`, `split`, `set`, `duplicate`, `delete`, `apply`, `undo`, `ids` |
| Reuse | `catalog`, `add` (`/hyperframes-registry`) |
| Media and sound | `media-treatment`, `grade-compare`, `remove-background`, `tts`, `transcribe`, `beats`, `normalize-audio` (`/media-use`) |
| Show and ship | `preview`, `present` (`/slideshow`), `render`, `share`, `publish` (legacy), `cloud`, `lambda`, `cloudrun` |
| Desktop app | `open`, `catch-up` |
| Upkeep | `doctor`, `browser`, `upgrade`, `usage`, `clean`, `feedback` |

`captions` is not a command: run `transcribe`, then read ../hyperframes/references/captions.md.

`validate`, `inspect` and `layout` are deprecated aliases of `check`; `events` is skills' own telemetry. Don't run them.

## The loop

1. Write, then `npx hyperframes lint` after the first pass and after structural changes.
2. `npx hyperframes check --json` and fix every error. While a lint error remains the layout and contrast audits don't run; "0 samples" means nothing was checked. Contrast failures carry a `suggestedColor`. A finding at a single sample (an entrance in flight) is info; a 3 s+ video with no visible change fails `sweep_static`.
3. `npx hyperframes snapshot` and read the PNGs (under `.hyperframes/artifacts/snapshots/`): that is how you see the video. With sub-compositions, snapshot a midpoint of every scene; tiny unstyled content or a missing hero is a mount defect (`../hyperframes/references/format.md`).
4. `npx hyperframes preview --background`, check the URL answers 200, give the person the project URL and wait, unless they asked for the file or for no stops. Passing checks alone is not a reason to render.
5. Time to render (step 4): `npx hyperframes render --quality looks -o out.mp4` (`draft` while iterating, `delivery` for the final; paid plan: `cloud render --fps <data-fps> --quality high -o out.mp4`). Confirm the file is non-empty and `ffprobe` reports the root `data-duration` and the project's `data-width`/`data-height`, then look at decoded frames.

"This element" or the current selection: `npx hyperframes preview --context --json --context-fields selection`; `no-selection` means ask them to click it.

## Edit the timeline

These are the edits Studio itself makes, so the result stays in Studio's shape.

- `timeline --json` lists clips with absolute `absStart`/`absEnd`, owning `file` and the `#id` ref the edit commands take (`timeline ids` stamps missing ids).
- `timeline move|trim|split|set|duplicate|delete <ref> … --plan --json` previews one edit; run it again without `--plan`. `--start`, `--end`, `--duration` set one edge or the length.
- An edit is refused when the clip would overlap a neighbour (`--overwrite`, or move the neighbour first) or end past its composition: raise the root's `data-duration` first. No command changes `data-duration`.
- Several edits at once: a JSON file such as `[{"verb": "move", "ref": "#outro", "time": "9"}]`, then `timeline apply plan.json --json`. Each run prints a `receipt`; save it and `timeline undo receipt.json` reverts it.

<!-- history (trial): remove this block together with the command -->

## Project history

Every write is kept and can be undone. At the start of a turn, `npx hyperframes history begin --who <you> --label "<plan>"`, then `history --since mine --who <you>` to see what the person changed; build on their edits. A check failed or they say it got worse: `history undo --who <you>`, never hand-edit back. End the turn with `history end`.

<!-- /history (trial) -->

## Render where

| Need | Command |
| --- | --- |
| Local | `render --quality looks -o out.mp4` (`draft`, `delivery`) |
| Reproducible container | `render --docker --strict -o out.mp4` |
| Batch from variables | `render --batch rows.json -o "renders/{name}.mp4"` |

A 30 s film renders in a minute or two: run it in the foreground. Detach only a render longer than your tool's timeout (`HYPERFRAMES_RENDER_DETACHED=1`, its own group, output to a log) and wait with `until grep -qE 'Render (complete|failed)' render.log; do sleep 5; done`, never `pgrep -f`, which matches its own loop and waits until the tool times out.

After a verified render, send one `feedback --rating`, plus a report for anything the person asked for that HyperFrames can't do, unless telemetry is off or they said no to usage notes: `references/feedback.md`.

## When a command fails

| Symptom | Fix |
| --- | --- |
| Chrome missing or won't start | `npx hyperframes browser ensure`; `doctor --json` always exits 0, gate on `.ok` |
| A heavy page isn't ready in time | Raise `--timeout` on `check` or `snapshot` |
| Unusual codec looks blank | Keep `--proxy` on (the default) |
| Render slow on Linux | The summary's second line says `screenshot` + `software gpu`: the slow path |
| `capture` fails or writes `BLOCKED.md` | Take nothing from its partial files; retry into a new `-o` folder |
| Disk tight | `clean --dry-run`, then `clean`; never delete `.hyperframes` (it holds history) |

## References

Read the row before running its command.

| Commands | Read |
| --- | --- |
| `init`, `capture`, `skills` | `references/init-and-scaffold.md` |
| `lint`, `check`, motion sidecars, `snapshot` | `references/lint-validate-inspect.md` |
| `compare`, `grade-compare`, `render --batch` | `references/compare-and-batch.md` |
| `beats` | `references/beats.md` |
| `preview`, `play`, `render`, `share`, `publish` (legacy), Studio context | `references/preview-render.md` |
| `doctor`, `browser` | `references/doctor-browser.md` |
| `info`, `upgrade`, `compositions`, `timeline`, `docs`, `usage`, telemetry | `references/upgrade-info-misc.md` |
| `--strict` flags, run ids, `clean`, shader lint, JSON paths | `references/conventions.md` |
| `keyframes` | `../hyperframes/references/motion.md` (Seeing motion) |
