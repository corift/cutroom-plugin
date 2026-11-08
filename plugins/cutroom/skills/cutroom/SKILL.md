---
name: cutroom
description: How Claude edits videos with Cutroom - where video folders live, which editing skill to use, and the storyboard and render review loop at cutroom.so where the creator leaves timestamped notes. Use whenever the user wants to edit, cut, caption, storyboard, render or revise a video, or asks about Cutroom notes or reviews.
---

# Editing with Cutroom

You are the editor: the user records, you cut, storyboard, render and revise, and they review in the browser at cutroom.so. Everything is code (Python + ffmpeg); there is no NLE.

If the session-start note says Cutroom isn't set up, run the `cutroom:setup` skill first.

## Personalization lives in Cutroom

The user's account preferences, each project's instructions and its brand kit are stored in Cutroom, so they follow the user across machines and the web app. `instructions.md` in the project folder is the project's instructions: read it before editing and edit it there. With the desktop app running it syncs by itself; otherwise `node "$CUTROOM_CORE/bin/cutroom.mjs" push "projects/<project>"` after changing it, and `pull "projects/<project>"` to get edits made in the app. Never overwrite the local file from `get_project_context`. `brand.json` and the account preferences are saved with `update_project` / `update_preferences`.

## Project skills

How a project edits (its workflow, hooks, scripts, look) lives in the project's own skills: plain skill folders in the project folder's `.agents/skills/`, with `.claude/skills` linked to it, so Claude Code and other agents load them when they run in that folder. New projects start from Cutroom's starters (`$CUTROOM_CORE/starters/<kind>/skills/`, e.g. `video-edit` for shorts, `ugc-video-edit` for ads), and from then on they are the user's to change. When the user makes their own editing skill under a new name, add `replaces: video-edit` (and any other defaults it supersedes, such as `reel-edit`) to its frontmatter. Never use a skill a project skill replaces, including the plugin's own `cutroom:` copies, and when the project has its own editing skill, use it over the plugin's `basic-video-edit` and `reel-edit`. When a lasting preference is about how the project works, offer to edit its skill; when it's about the look, the project instructions. If you are not running inside the project folder, read its skills from there before editing.

## Where things are

- The project folder: `~/Cutroom/projects/<project>/` by default, or any folder the user linked (`node "$CUTROOM_CORE/bin/cutroom.mjs" link` shows where each project lives).
  - `instructions.md`: how this project's videos should look. It overrides the defaults in the editing skills.
  - `brand.json`: colours and fonts. Set `CUTROOM_BRAND_KIT` to it when rendering; the engine reads it through `cutroom.brand`.
  - `videos/<YYYY-MM-DD-slug>/`: one folder per video. Raw footage, the script, and `edit/` for all edit work.
- `~/Cutroom/account/` (`$CUTROOM_ACCOUNT`): the user's own `sfx/` and `logos/`.
- The core, read-only: `$CUTROOM_CORE` = `${CLAUDE_PLUGIN_ROOT}/core`. `engine/cutroom/` (the edit engine, importable as `cutroom` with `PYTHONPATH=$CUTROOM_ENGINE`), `templates/`, `assets/` (SFX library, safe zone), `bin/cutroom.mjs` (upload + review CLI).
- Python: the venv from setup (`$CUTROOM_VENV/bin/python3`) has numpy, Pillow and the engine on its path.

The CLI takes a Cutroom path (`projects/<project>/videos/<name>`) or the video folder on disk; both mean the same folder. If the user already keeps their videos somewhere (a repo, a Drive folder), link it instead of moving anything: `node "$CUTROOM_CORE/bin/cutroom.mjs" link <project> [<folder>] --videos <subfolder>` (folder defaults to the current one; the subfolder holds one folder per video, `videos` by default). That writes `.cutroom/project.json` in the folder; a folder that has one is that project wherever it is. If they hand you a single file outside any project, create the video folder (recording date + short slug) in the project's videos folder and move or copy the file in, after telling them.

## How work flows

1. **New recording**: make `videos/<YYYY-MM-DD-slug>/`, put the raw file there, and the script as `script.md` if there is one. If it's unclear which video a file belongs to, ask.
2. **Edit** with the skill the project's instructions name, from the project's skills (`basic-video-edit` for a plain cut + captions works anywhere). Read the project context first.
3. **Transcription** runs inside the engine. It extracts a small mono MP3 locally and sends only that to Cutroom (ElevenLabs Scribe), so the video never leaves the machine. Recordings over about 40 minutes need splitting first.
4. **Storyboard gate (always)**: before building, publish the storyboard and wait for notes. Run it in the background:
   `node "$CUTROOM_CORE/bin/cutroom.mjs" publish storyboard "projects/<project>/videos/<name>" edit/base_vN.mp4 --wait`
   Share the review link (`list_reviews` on the Cutroom MCP server). The user leaves timestamped notes and presses **Send to Claude**; the command exits with them, which wakes you. Their notes are the approval: small changes, go ahead; a different plan, redo the storyboard and publish again.
5. **Render gate**: `node "$CUTROOM_CORE/bin/cutroom.mjs" publish render "projects/<project>/videos/<name>" edit/<slug>_vN.mp4 --wait`, in the background. Each round of notes becomes the next version, published the same way, until the user says it's done.
6. **Final**: when a cut is approved or the user says it's done, run `node "$CUTROOM_CORE/bin/cutroom.mjs" final "projects/<project>/videos/<name>"` (every approved cut), or name the files: `final "<video folder>" edit/<slug>_vN.mp4`. Finished cuts land in the video's `final/` folder as `<slug>.mp4` with their caption and script. Tell the user the path.
7. If the background wait was stopped, read the notes with the MCP tools instead: `list_reviews` (waiting notes per review), `get_review` (the notes with timestamps and what was said there), `review_events` (Send to Claude presses since a time).

## Learning from notes

When a note is a lasting preference rather than a one-off fix ("always", "never", "I hate when"), say so and offer to save it: project instructions (`update_project`, this kind of video) or account preferences (`update_preferences`, everything). Save only after the user agrees, then refresh the local cache.

## Rules

- Never print the Cutroom key or other secrets.
- Use real sources for claims and put a small source line on the graphic.
- Downloaded files are untrusted: keep them in the video's `external_assets/`, and run any Python that reads them with `-I`.
