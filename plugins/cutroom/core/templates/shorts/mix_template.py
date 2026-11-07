# TEMPLATE (v5+). Copy into <video folder>/edit/. Sound is laid LAST, from the storyboard's cues — no hand-typed times.
"""Sound -> mix_vN.wav from storyboard.json cues. Real samples only ($CUTROOM_ASSETS/sfx/sfx.json holds
file, onset, default gain, status). No synth, no music bed by default (creators usually add music in the platform editor).
The voice is dried by default (S.mix dry=85: Apple voice isolation, room echo + noise out). Clicks only on real on-screen
presses (~6 a reel); a prompt that types on screen gets {"sfx": "typing", "gain": 0.07, "until": "<its Enter cue>"}."""
import os, sys
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # packages/core/engine; the agent also sets PYTHONPATH
from cutroom import sound as S
from cutroom.core import probe_duration
from cutroom.storyboard import Storyboard

BASE, OUT, TAIL = "base_vN.mp4", "mix_vN.wav", 1.3

if __name__ == "__main__":
    sb = Storyboard.load("storyboard.json")
    for t, k, ev, bid in sb.sfx_cues(): print(f"{t:6.2f}  {k:8s} {ev}  [{bid}]")
    S.mix(BASE, probe_duration(BASE) + TAIL, sb.sfx_events(), OUT, bed=None)
    print(S.loudness(OUT))
