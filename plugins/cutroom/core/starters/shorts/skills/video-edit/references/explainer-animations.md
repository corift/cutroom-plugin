# Explainer animations

Worked example: a 95s reel explaining OpenAI's 10,000-agent swarm (the scene catalogue below is from it). The brief that produced it: no header text at the top unless it clearly illustrates a point, more animations and illustrations because the script is wordy, and charts and flows for the big numbers.

Use this mode for any explainer script, or any wordy script that walks through *how something works*. It sits on top of the default flow (stack ↔ full ↔ face, full-screen proof). It changes two things: **the explanation is animated, not captioned**, and **headers are off by default**.

Code: the reusable primitives are in `$CUTROOM_CORE/engine/cutroom/explainer.py`; the scenes themselves are written per video in `renderN.py`.

## Rules

1. **No headers by default.** Only use one when the header itself is the point. The one top-of-frame text in the example was the struck-through "10,000 agents" over the face on "the magic was never really the number of agents". Label cards with a small tracked **kicker inside the card** instead (`explainer.kick`, e.g. "OPENAI · SEPTEMBER 2026", "THE PLAYBOOK").
2. **Every spoken step is a state change on its word.** The explainer gets a storyboard cue per verb ("split" → agents stream into rooms, "stuck" → room B goes red, "cracked" → ring pulse, "shared library" → card flies to the shelf, "pass it across" → stars fan out). If a sentence has a verb, it has a cue.
3. **One recurring world that evolves.** Build one scene (here an office floor plan with 4 coloured team rooms) and come back to it across beats, adding one thing each time: teams → versions A–D + progress bars → group chat → library in the corridor → manager in the middle. The viewer learns the map once and then only watches what changes. Keep colours consistent everywhere (team colours = `explainer.TEAM`, taken from the source's own slides).
4. **Charts and flows for scale.** Big numbers get a visual, not just a count-up:
   - a dot swarm that counts to 10,000 (numpy `stamp`, real 10k dots),
   - a lens flow chart "Goal → N lanes → Solution ✓" with particles streaming (`flow_lanes` / `draw_flow`),
   - a comparison bar ("unsolved ~90 years" full bar vs "88 hours" sliver),
   - a collapse (10,000 dots → 5 orbs) for the "you don't need 10,000" scale-down.
5. **Head fake = visual reversal.** "Didn't come from one genius AI…it came from 10,000 working together like a company" became orb → accent strike through the label → orb bursts into dots → dots snap into an org chart.
6. **Receipts stay verbatim.** For a quoted claim, rebuild the source paragraph word for word on a black quote card (`quote_card`) with a marker sweep on the phrase when it's said; the rest dims. For a page header, sweep the marker over the real screenshot (`marked_copy` + `sweep`). Source line on the card.
7. **Stack for explaining, full for payoffs.** The step-by-step scenes run on the stack (card at y=370). The payoff of a sequence goes full screen: the same scene blown up (`full_panel`), e.g. "every other agent could read and build on" → beams to every room, full. Also full: "it actually worked" → the flow chart, and merge → RESULT ✓.
8. **Illustrations are generic, not quotes.** Chat messages, task names and the like are clearly illustrative ("Approach 2 is a dead end."). Never invent numbers or quotes attributed to the source. Mention mock items when delivering, but don't add caveats on screen.
9. **Real clips still break it up.** Use 4–5 credited full-screen clips from the source between animated beats, so it never feels like a slideshow.
10. **Mix footage and animation.** Real footage/assets for showable nouns, animated scenes for the mechanism. All-footage loses the explanation; all-animation feels like a slideshow.

## Scene catalogue (example timings, ~95s)

| t | Beat | Layout | Animation |
|---|---|---|---|
| 0:00 | hook | stack | swarm floods in, counter 0 → 10,000 on "10,000" |
| 0:02 | prize | full | real OpenAI header, marker on "Millennium Prize Problem", chip "Unsolved for ~90 years" |
| 0:09 | genius | stack | orb → strike → burst → org chart (head fake) |
| 0:16 | office | stack | floor plan line-draws, agents stream from corridor into 4 team rooms on "split" |
| 0:22 | stuck | stack | VERSION A–D + progress bars; B jams red STUCK; others "still going" |
| 0:26 | chat | stack | `#all-agents` messages cascade; DM card slides in on "DM" |
| 0:33 | library | stack | agent ring-pulses on "cracked"; card flies (bezier) into the LIBRARY; +1 book |
| 0:39 | readall | full | beams + particles from library to every room; rooms pulse on "build" |
| 0:41 | codexsrc | full | verbatim source paragraph, marker on the key phrase |
| 0:43 | manager | stack | manager node drops in; scan highlight per room; stars lift to it, fan back out |
| 0:48 | worked | full | flow chart Goal → 4×6 lanes → Solution ✓ on "worked" |
| 0:50 | numbers | full | 88 hours count + 90-years-vs-88-hours bars; 2.7M messages count |
| 0:55 | proof | stack | verbatim quote card, marker on "88 hours…" then "additional 17 hours" |
| 1:02 | five | stack | 10,000 dots collapse into 5 orbs on "five" |
| 1:06 | split → merge | stack → full | 1 agent → 3 task cards → 3 attackers from different angles → reviewer → RESULT ✓ |
| 1:17 | magic | face | serif "10,000 agents" over the head, accent strike on "never" |
| 1:19 | shelf | stack | shared library centre; one agent drops a card; others' spinners → "skips ahead ✓" |
| 1:28 | playbook | stack | checklist (kicker "THE PLAYBOOK", no header) |

## Build notes / gotchas

- Write one `office(t, **state)`-style function per recurring world, returning a 900×500 panel. Each beat function computes state from `SB.cue(...)` and calls it. Use `place_card` for the stack and `full_panel` for the full-screen version.
- `glow_card` adds padding. At full-screen scale it ends up wider than 1080, and PIL `alpha_composite` raises on negative coordinates. Use `full_panel` (no glow) and the safe `P()` paste.
- Use logos in their white version on dark (e.g. `openai.png`); a `-light` variant is the black mark for light backgrounds. Logos live in `$CUTROOM_ACCOUNT/logos/`.
- Status chips on rooms: put them on the room's top border (y0 − 20), right-aligned, so they don't cover the room's label.
- Vertical (9:16) source clips with burnt-in captions: crop the 1080×960 band above the captions (`cover(..., cy≈0.36)`). Pick a source time where nobody walks in front of the camera (check the contact sheet).
- Render time: well under the video's length with the parallel renderer (`cutroom.parallel`). Preview stills seek directly (~0.4s each).
- Deliver only the 1080p render, even when it's over a phone-send size limit; no second low-res copy.
