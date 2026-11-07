# TEMPLATE (from the Opus 5.5 reel, v4). Copy into <video folder>/edit/, then replace KEEPS/TIGHT with the new video's content.
"""v3 step 1: silence-snapped cut plan -> base_v3.mp4 (+ segments.json). --dry reports, --qa re-transcribes.
Pauses are planned on the DRIED voice (cp.speech_env: Apple voice isolation, cached as <src>_iso100.wav) and trimmed to
~0.16 s joins (MAX_PAUSE 0.25, HANDLE 0.08). Write KEEPS from the ElevenLabs Scribe transcript (verbatim: retakes,
false starts and repeats show up; Groq hides them), and QA with Scribe too (ELEVENLABS_API_KEY in .env.local)."""
import os, sys, json
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # packages/core/engine; the agent also sets PYTHONPATH
from cutroom import cutplan as cp

SRC = "../IMG_4540.MOV"
SPEED = 1.03    # default; adjust per video, e.g. 1.0 if it feels rushed

# Content decisions (source seconds), sentence level. Cuts between keeps are content cuts;
# pauses inside a keep are only shortened by the planner rules.
KEEPS = [
    (0.00, 12.95),          # hook -> "...every single day."   (drops redundant "most powerful" line)
    (16.40, 40.40),         # "So if you're not on it" -> "...directly in Claude Code."
    (41.85, 43.00, 0.02),   # "The next thing is the writing."  (hard stop before retake's "So")
    (46.50, 60.95, 0.02),   # "So if you've ever used Claude" -> "...copywriting,"  (skips "speaking with")
    (62.00, 71.62),         # "even when it codes" -> "give it a try."
    (73.22, 74.62, 0.05),   # "That's just the power of Claude."
]
# Face is covered by full-screen B-roll here -> pauses can be trimmed harder (hidden jump cuts)
TIGHT = [(24.90, 33.45)]

if __name__ == "__main__":
    env, th = cp.speech_env(SRC)
    segs = cp.trim_edges(cp.plan(KEEPS, env, tight=TIGHT, thresh=th), env, thresh=th)
    print(cp.report(segs))
    if "--dry" in sys.argv: sys.exit()
    cp.build(SRC, segs, "base_v3.mp4", speed=SPEED)
    if "--qa" in sys.argv:
        cp.qa("base_v3.mp4", "base_v3_transcript.json")
