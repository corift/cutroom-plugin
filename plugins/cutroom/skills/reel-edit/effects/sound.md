# Sound

Every hit has a sound, from the shipped SFX library (`$CUTROOM_ASSETS/sfx/sfx.json`, `ok` sounds only). The mix is normalised to -14 LUFS.

| effect | sound |
| --- | --- |
| whip, zoom, circle, split, comment bar | whoosh |
| glitch, slab | shutter |
| punch (≥1.4), crack, comment word, flash moment | impact |
| card, chip, badge, split mark, memory chip | click |
| count | counter, then ding on the badge |
| note | typing |

- Add more with `"sfx": [{"at": "silences", "name": "click", "gain": 0.7}]`. `gain` multiplies the library level.
- No riser and no pop (off / avoid in the library). No music bed yet; add one only if asked.
