# Example storyboard: a 63s launch reel (stack-heavy default look)

What `sb.markdown("storyboard.md")` produces: a loose plan for review before the build. Picture first, sound last on the cues. The matching JSON is `$CUTROOM_CORE/templates/shorts/storyboard_template_v5.json`.

| # | Time | Layout | On screen | Says | Cues → SFX |
|---|---|---|---|---|---|
| 1 | 0.00–0.86 | face | Talking head, tight | So Claude just dropped |  |
| 2 | 0.86–3.30 | stack | **Just dropped** · Hero card: Claude Opus 5.5 over launch image | Opus 5.5 and I've been using it for the last day. | 0.86 card rises → `impact`<br>0.86 layout in → `whoosh` |
| 3 | 3.30–5.60 | face | Talking head | And I have to tell you, it is probably one of, |  |
| 4 | 5.60–7.50 | face | **The best AI model** · Header + sub 'available right now.' over face | if not the best AI model available. |  |
| 5 | 7.50–13.02 | stack | **Opus 5.5 vs GPT-6 Astra** · Benchmark bars: Terminal-Bench 66.4 vs 57.9, GDPval 1846 vs 1542 | And I've used GPT-6 Astra for the last month straight or since it came out every single day. | 7.50 layout in → `whoosh`<br>7.95 bars grow + count → `counter` |
| 6 | 13.02–16.30 | face | Talking head | If you're not on it, then you need to get on it because here's some of the things that it can do. |  |
| 7 | 16.30–17.90 | face | **1. It makes videos** | So first, it can literally | 16.30 chapter header → `impact` |
| 8 | 17.90–21.10 | stack | **Made entirely in Claude** · Clip card: @Oldnoob007 GPT-6 remake | create videos with no tools, no video editor, | 17.90 layout in → `whoosh` |
| 9 | 21.10–29.00 | stack | **Made with Claude** · Clip card cycling 4 creator videos + credits | and it creates some of the craziest ones. Like some of these are truly insane to me and it kind of gives me the feel, the AGI vibes. So | 23.00 clip change → `shutter`<br>24.90 clip change → `shutter`<br>26.90 clip change → `shutter` |
| 10 | 29.00–31.60 | face | Talking head | you can imagine that you can use this for video editing. |  |
| 11 | 31.60–36.06 | stack | **All inside Claude Code** · Terminal: prompt types, Enter, progress lines cascade · _click = prompt submit; needs a visible press_ | You can create videos, create animations, all directly in Claude Code. | 31.60 layout in → `whoosh`<br>33.65 prompt submitted → `click` |
| 12 | 36.06–37.19 | face | **2. The writing** | The next thing is the writing. | 36.06 chapter header → `impact` |
| 13 | 37.19–48.47 | stack | **Same prompt, both models** · Paper doc: Opus 5 answer scrolls, accent wipe to Opus 5.5 answer + marker | So if you've ever used Claude, you probably realize the writing at Opus 5 was not legible. It was not even human readable. And fortunately, they fixed it. I've been using it for the last day since it came out. | 37.19 layout in → `whoosh`<br>44.95 5 -> 5.5 wipe → `whoosh` |
| 14 | 48.47–54.50 | stack | **So much better at** · Checklist: Copywriting, Plain-English updates | And it is so much better at copywriting. Even when it codes, it tells you what it's doing in plain English. | 48.47 layout in → `whoosh`<br>50.00 tick Copywriting → `ding`<br>53.90 tick Plain-English → `ding` |
| 15 | 54.50–57.10 | face | Talking head | So if you haven't had a chance, I would definitely recommend to |  |
| 16 | 57.10–59.40 | face | OpenAI tile struck through, Claude tile rises in | swap everything back over to Claude. and I'm sure this is going to change | 58.43 logo swap → `click` |
| 17 | 59.40–61.40 | face | Talking head | in a month. Give it a try. That's just the |  |
| 18 | 61.40–63.70 | full | End card: Claude logo, 'Claude Opus 5.5' over hero | power of Claude. | 61.40 end card → `impact` |

Notes on reading it:
- Every `click` needs a visible press on screen at the same cue (beat 11's prompt submit, beat 16's logo swap); the cue check after render proves it.
- Under the current sound defaults, only real presses keep a `click` (about 6 a reel), and the checklist ticks / logo swap would be silent cues unless they're payoffs.
