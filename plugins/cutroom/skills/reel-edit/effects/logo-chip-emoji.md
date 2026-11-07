# Logo, chips and emoji

Small pops that land on a word.

```json
{"do": "logo", "at": "claude", "until": "entire"},
{"do": "chip", "at": "silences", "text": "8 pauses cut", "emoji": "✂️", "rgb": [232, 44, 48], "fg": [255, 255, 255]},
{"do": "badge", "at": "done", "text": "✓ all clear"},
{"do": "emoji", "at": "entire", "text": "🤯", "x": 840, "y": 560}
```

- `logo`: the Claude asterisk on a white tile, popping and untwisting (top right). For the hook when Claude is named.
- `chip`: a rounded label with an optional emoji, tilted -3°. `x`, `y`, `rot`, `size`.
- `badge`: a green pill (`rgb` to recolour).
- `emoji`: one big emoji, tilted. At most two in a video.
- Chips and badges get a soft click.
- Code: `V.logo`, `V.chip` + `V.pop`, `V.badge`, `V.big_emoji`.
