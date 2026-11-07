# Transitions

Set on the section they lead into: `"transition": "whip"`. Each brings its own sound.

| name | look | sound |
| --- | --- | --- |
| `whip` | a fast horizontal smear into the new shot (0.2s); `"direction": -1` to whip left | whoosh |
| `glitch` | RGB split and torn bands for ~3 frames either side of the cut | shutter |
| `flash` | the new shot starts from white (0.12s) | — |
| `zoom` | the new shot lands from 1.3x with a radial smear | whoosh |
| `crack` | white fracture lines from a point, a bright first frame | impact |
| `circle` | the new shot opens out of a growing circle | whoosh |

- Every other section at most, never the same one twice in a row.
- Whip for a turn ("like", "then"), glitch for a reveal, flash into a hard stop or the CTA.
- `{"do": "flash", "at": ...}` flashes on any word, with an impact.
- Code: `V.TRANSITIONS`.
