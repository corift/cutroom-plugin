# Jump cuts

No pause survives. Either list the stretches to keep (`keep`, source seconds) or leave it out and every pause over 0.22s is cut from the audio (`Timeline.from_audio`: -34 dB floor, 0.07s pad).

```json
"keep": [[0.00, 4.42], [4.42, 7.12], [7.15, 8.64]]
```

- Write `keep` by hand when there are retakes or a line to drop. Cut at sentence ends, in the pause after the last word, never mid-word.
- A keep under 0.6s reads as a glitch. Merge it.
- Two keeps that touch (`4.42` → `4.42`) still make a cut: the camera changes there, the audio doesn't skip.
- Each cut inside a section punches in 12% (`punch-in.md`), so a cut always looks like a cut.
- Code: `V.Timeline`, `V.JumpReader` (reads the source through the cut, so there's no intermediate file).
