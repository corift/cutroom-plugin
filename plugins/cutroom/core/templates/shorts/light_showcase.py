"""Demo reel for the light product UI look (cutroom.light), cut like @charliehills' reel: hook card, then each
step of the pipeline as a card that changes state, a proof count, the CTA. Face panel below, caption between.

    python3 light_showcase.py OUT.mp4 [--face base.mp4 --face-start 0] [--preview t1,t2,...]
"""
import sys, os, argparse
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from cutroom import light as L
from cutroom.core import W, H, FPS, font, SFT, Reader
from cutroom import parallel

def stand_in_face():
    yy, xx = np.mgrid[0:1920, 0:1080].astype(np.float32)
    bg = np.dstack([205 - 30 * yy / 1920, 200 - 28 * yy / 1920, 196 - 20 * xx / 1080])
    im = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse((140, 1060, 940, 2300), fill=(58, 66, 84))
    d.ellipse((370, 420, 710, 860), fill=(222, 178, 146))
    d.ellipse((350, 380, 730, 600), fill=(52, 38, 30))
    return im.filter(ImageFilter.GaussianBlur(3)).convert("RGB")

FACE = stand_in_face()
WORDS = ["4.12s", "Claude"], ["4.40s", "edited"], ["4.71s", "this"], ["4.93s", "entire"], ["5.40s", "video."], ["6.02s", "Not"], \
        ["6.20s", "one"], ["6.48s", "cut"], ["6.80s", "by"], ["7.02s", "me."]
VO = ("Claude edited this entire video. Here's the prompt. It transcribes every word, then cuts only in the silences. "
      "It follows one design file. Then it checks its own work, so I can trust it. When I leave a note, it remembers. "
      "One recording, ten thousand views. Comment EDIT and I'll send you the prompts.").split()

def S_hook(cv, k): L.hook_card(cv, k, "Claude edited this entire video", name="Sully")
def S_prompt(cv, k):
    L.prompt_card(cv, k, "Edit this video. Cut the silences, keep my style, and check every frame before you finish.",
                  file="raw.mp4", t_file=0.1, t_type=0.3, cps=34, t_send=3.0, t_check=3.3,
                  statuses=[(0, "Step 1 of 4", False)])
def S_words(cv, k):
    L.words_card(cv, k, [(ts, w, 0.3 + i * 0.18) for i, (ts, w) in enumerate(WORDS)],
                 statuses=[(0, "Step 2 of 4", False), (2.2, "212 words", True)])
def S_wave(cv, k): L.wave_card(cv, k, statuses=[(0, "Step 2 of 4", False), (2.2, "1 cut", True)])
def S_style(cv, k):
    L.style_card(cv, k, [("Type", "SF Pro, one line", 0.3), ("Colour", [(255, 255, 255), (22, 22, 26), L.BLUE], 0.8),
                         ("Graphics", "White, one blue", 1.4)], statuses=[(0, "Step 3 of 4", False)])
def S_trust(cv, k): L.slam_word(cv, k, "trust.")
def S_check(cv, k):
    L.check_card(cv, k, [("Every cut", "lands in a silence", 0.4), ("Every frame", "nothing off-screen", 0.9),
                         ("Every second", "captions in sync", 1.4)],
                 statuses=[(0, "Step 4 of 4", False), (1.8, "All passed", True), (2.4, "Ready to post", True)])
def S_memory(cv, k):
    L.memory_card(cv, k, "keep captions below the visuals", ["Captions: one line, SF Pro", "Cut only in silences"],
                  "Captions sit below the visuals", t_save=1.5)
def S_count(cv, k): L.count_card(cv, k, FACE, 2500, 10000, title="Posted · one take")
def S_cta(cv, k): L.cta_card(cv, k, "EDIT")

SEGS = [("hook_card", 2.4, S_hook), ("prompt_card", 4.0, S_prompt), ("words_card", 2.8, S_words), ("wave_card", 3.2, S_wave),
        ("style_card", 2.6, S_style), ("slam_word", 1.2, S_trust), ("check_card", 3.0, S_check), ("memory_card", 3.0, S_memory),
        ("count_card", 2.4, S_count), ("cta_card", 2.8, S_cta)]
STARTS, acc = [], 0.0
for s in SEGS: STARTS.append(acc); acc += s[1]
TOTAL = acc
VO_T = [(w, 0.15 + i * (TOTAL - 0.8) / len(VO)) for i, w in enumerate(VO)]

def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= STARTS[i]: return i, t - STARTS[i]
    return 0, t

def make_frame(i, srcs):
    t = i / FPS
    si, k = seg_at(t)
    name, dur, fn = SEGS[si]
    cv = L.canvas(i)
    fn(cv, k)
    L.face_panel(cv, srcs[0].next() if srcs else FACE)
    L.caption(cv, t, VO_T)
    ImageDraw.Draw(cv).text((48, 60), f"light · {name}", font=font(SFT("Medium"), 26), fill=L.MUTED, anchor="lm")
    return cv

def open_sources(t0, a):
    return (Reader(a.face, 1080, 1920, start=a.face_start + t0),) if a.face else ()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--face"); ap.add_argument("--face-start", type=float, default=0.0)
    ap.add_argument("--preview"); ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            srcs = open_sources(t, a)
            make_frame(int(round(t * FPS)), srcs).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
            for s in srcs: s.close()
    else:
        parallel.render(a.out, int(TOTAL * FPS), make_frame, lambda t0: open_sources(t0, a), workers=a.workers)
