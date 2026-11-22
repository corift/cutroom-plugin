# Caption: editorial (spread, feature, masthead)

Three magazine-style captions. Big words are Instrument Serif italic; small words are the display face. Each one picks one main word per phrase: a word in `keys` if the phrase has one, otherwise its longest word that isn't filler.

| style | look | sits |
| --- | --- | --- |
| `spread` | little words (the, on, this) in small tracked caps, every other word in a big white serif italic, stacked tight and centred, up to 5 words. Each word blurs in as it's said. | y 1360 |
| `feature` | a left-set line of bold white words, up to 5. The main word is a big red serif italic. Words rise in as they're said. | y 1420, left 90px |
| `masthead` | one giant word (330px, white serif italic) behind the person's head for the whole sentence, with the rest of it in tracked caps low in the frame, a few words at a time. | word on the top of the head, line at y 1500 |

```json
{"at": "then it followed", "caption": "masthead", "keys": ["followed"]}
```

- `masthead` needs `--mask` (`effects/behind-head.md`). Without one the word is drawn over the person, so check it before you use it.
- Set `keys` when the longest word isn't the one that matters. In `masthead` the main word stays up until the next sentence or pause, so give one key per sentence: the word that carries it.
- `spread` and `masthead` are calm. Use them for the setup or the payoff, not for fast lists.
- `feature`'s red comes from the style; set `cy` if the hands or the chin are in the way.
- Code: `V.spread_caps`, `V.feature_caps`, `V.masthead_caps` + `V.masthead_back`.
