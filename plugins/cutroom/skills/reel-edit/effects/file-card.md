# File card

A white card (a file name, an optional tag) whose rows fade in one by one, over the top of the shot.

```json
{"do": "card", "at": "design", "title": "design.md", "tag": "Step 3",
 "rows": [["captions", "bold, 3 words"], ["type", "SF Pro + serif"], ["cuts", "punch in on each"]]}
```

- For a file, setting or rule the speaker names. Up to 4 short rows, each value under 18 characters.
- Rows land 0.28s apart; give the card at least 1.2s or set `until`.
- `y` (360) moves it. Lands with a click.
- Code: `V.file_card`.
