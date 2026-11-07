# Counter

A big gold number counting up behind the head, a label above it, and a green badge on the payoff word.

```json
{"do": "count", "at": "checked", "to": "frame", "value": 616, "label": "frames checked",
 "badge_at": "done", "badge": "✓ all clear"}
```

- Counts from `at` to just past `to`. Use a real number (frames = seconds × 30, words in the transcript).
- The frame darkens and captions hide while it runs. Counter sound on the start, ding on the badge.
- Code: `V.big_word`, `V.badge`.
