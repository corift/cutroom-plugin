# Transcript split screen

The top half becomes a transcript card (audio.json) that slides down, each word lighting blue as it's said; the face moves to the bottom half. A marked word gets a highlight and a chip ("✂ cut the gaps").

```json
{"do": "split", "at": "it wrote", "until": "then", "mark": "silences"}
```

- For lines about what Claude read, wrote or transcribed. The card shows the first 12 words of the moment, with their source times.
- `title`, `sub` and `chip` change the text. Keep it 3–5s.
- Lands with a whoosh; the mark gets a click.
- Code: `V.split`.
