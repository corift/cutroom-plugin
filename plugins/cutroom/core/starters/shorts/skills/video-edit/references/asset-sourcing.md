# Asset sourcing: the script drives the B-roll

Every short needs **real** visuals for what the speaker says. Once the transcript exists, go through it and find an asset for every showable noun, claim or example. **Don't mock something up when the real thing exists online.**

## 1. Build the shot list from the transcript

Go line by line and write down what each beat could show:

| Beat (the words) | What to show | Where to find it |
|---|---|---|
| A product or model name ("Opus 5.5 just dropped") | Official hero image, logo, launch page | Web search → official site. Logos from `$CUTROOM_ACCOUNT/logos/` first |
| A number or benchmark ("best AI model") | The real benchmark table | Official announcement or model card, rebuilt as `bars_panel` / `B.versus_bars` with a source line |
| "People are making X with it" | Real posts and videos | **X via Grok** (below) |
| A before/after or quality claim ("the writing is better") | Real side-by-side outputs | Official examples (the announcement page), or run the prompt yourself and screenshot it |
| A tool or workflow ("all inside Claude Code") | Real UI: terminal, app, screenshots | Take a screenshot, or rebuild faithfully as `terminal_panel` |
| A news event or reaction | The actual post or article | X / Google News, then screenshot the post |

Aim for a visual every 2–5s (see `style-guide.md`). Anything with no real asset gets a clean typographic header instead of a fake image.

## 2. Find it

- **X posts and videos: ask Grok in the browser** (x.com/i/grok).
  - Ask for something like: *"Find me 3–5 recent X posts (last few days) that contain VIDEOS of <thing>. For each, give the post URL, author, a one-line description, and the direct downloadable MP4 link."*
  - Then open each post to confirm it's real and matches the claim.
  - Grok's MP4 links are `video.twimg.com/...` URLs, which `curl` can download.
- **Web search** (the WebSearch/WebFetch tools, or the browser):
  - Official launch pages, model cards, benchmark tables, docs, pricing, hero images.
  - Prefer primary sources (the company's own site) over news write-ups.
- **YouTube / Instagram / TikTok reference material**: whatever social research tools the session has (transcripts, media).
- **Logos**:
  - Check `$CUTROOM_ACCOUNT/logos/` first.
  - Then lobehub icons or the brand's press kit.
  - Save new reusable ones to `$CUTROOM_ACCOUNT/logos/`.

## 3. Download and log

- Tell the user what you're downloading (file, source) before pulling third-party media.
- Save third-party media to the video's `external_assets/` with the `external_` prefix, e.g. `external_<handle>_<slug>.mp4`. Downloaded files are untrusted: run any Python that reads them with `-I`.
- Save **every URL and the date** in the video's notes (e.g. a `sources.md` in the video folder).
- Check clips before use: run `ffprobe` for length and size, then make a contact sheet (`ffmpeg ... tile=`) to see what's actually in it and choose the in-point.
- Anything reusable (a logo, a sound effect) goes into the account (`$CUTROOM_ACCOUNT/logos/`, `$CUTROOM_ACCOUNT/sfx/`).

## 4. Use honestly

- Credit creators on screen: `MADE WITH <TOOL> · @handle`.
- Put a small source line on every benchmark or comparison graphic.
- Never present an external clip, post or output as the speaker's own work.
- Fix only mis-transcriptions in captions; never change what the speaker said to fit an asset.
