# Words behind the head

A giant word between the wall and the person, with an italic serif line above it. The frame darkens so it reads; the head and hands cross in front. Captions hide while it's up.

```json
{"do": "behind", "at": "entire", "until": "like", "text": "ENTIRE", "sub": "this whole video"}
```

- One word, said in that moment. 4–7 letters read best. `size` (330), `y` (700): put it above the head, behind the hair.
- Adds a soft whoosh.
- Needs the person mask of the source:

```
swiftc -O "$CUTROOM_CORE/engine/personmask.swift" -o <scratch>/personmask
<scratch>/personmask SRC.mp4 540 960 | ffmpeg -f rawvideo -pix_fmt gray -s 540x960 -r <source fps> -i - -c:v libx264 -crf 8 -pix_fmt yuv420p mask.mp4
```

  On Linux use `python3 "$CUTROOM_CORE/engine/personmask.py"` in the same pipe.
- Code: `V.big_word`, `V.behind`, `V.person`, `V.darken`.
