"""Showcase of the reel blocks (2026-10-20): the pieces the Claude-editing reels lean on that Cutroom lacked.
Needs no footage: the screen, face and result clips are drawn stand-ins, so swap in real ones when using a block.

    python3 reel_blocks_showcase.py OUT.mp4 [--preview t1,t2,...]
"""
import sys, os, argparse
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from cutroom import blocks as B
from cutroom.core import W, H, FPS, font, SFD, SFT, text_img
from cutroom import parallel

MENU_X, MENU_Y, ROW_H, MENU_W = 140, 760, 104, 800
MODELS = [("Opus 5.5", "Most capable"), ("Sonnet 5.5", "Fast and smart"), ("Haiku 5.5", "Fastest")]
OPUS_BOX = (MENU_X + 16, MENU_Y + 24, MENU_X + MENU_W - 16, MENU_Y + 24 + ROW_H)
EFFORT_Y = MENU_Y + 48 + ROW_H * 3 + 20
EFFORT_BOX = (MENU_X + MENU_W - 250, EFFORT_Y - 4, MENU_X + MENU_W - 24, EFFORT_Y + 76)

def app_screen():
    cv = B.canvas("dark", 0)
    d = ImageDraw.Draw(cv)
    d.text((540, 300), "Good evening, Sully", font=font(SFD("Bold"), 64), fill=(236, 234, 228), anchor="mm")
    mh = 48 + ROW_H * 3 + 130
    cv.alpha_composite(B.ss(lambda dd, s: dd.rounded_rectangle((0, 0, MENU_W * s - 1, mh * s - 1), 26 * s, fill=(44, 44, 42, 255),
                                                               outline=(84, 83, 78, 255), width=2 * s), MENU_W, mh), (MENU_X, MENU_Y))
    fN, fS = font(SFT("Semibold"), 38), font(SFT("Regular"), 28)
    for i, (n, sub) in enumerate(MODELS):
        y = MENU_Y + 24 + i * ROW_H + ROW_H / 2
        d.text((MENU_X + 48, y - 16), n, font=fN, fill=(240, 238, 234), anchor="lm")
        d.text((MENU_X + 48, y + 22), sub, font=fS, fill=(150, 148, 142), anchor="lm")
        if i == 0: d.text((MENU_X + MENU_W - 60, y), "✓", font=font(SFT("Semibold"), 40), fill=B.CLAUDE, anchor="mm")
    d.line([(MENU_X + 30, EFFORT_Y - 22), (MENU_X + MENU_W - 30, EFFORT_Y - 22)], fill=(70, 70, 66), width=2)
    d.text((MENU_X + 48, EFFORT_Y + 36), "Effort", font=fN, fill=(240, 238, 234), anchor="lm")
    d.text((MENU_X + MENU_W - 137, EFFORT_Y + 36), "Max", font=fN, fill=B.CLAUDE, anchor="mm")
    B.prompt_bar(cv, 3.0, [("Cut this into a 30s reel in my style", 0.2, 1.2)], cy=1480)
    return cv

def stand_in_face():
    yy, xx = np.mgrid[0:600, 0:600].astype(np.float32)
    bg = np.dstack([90 + 80 * yy / 600, 70 + 50 * yy / 600, 60 + 30 * xx / 600])
    im = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse((60, 430, 540, 900), fill=(36, 38, 46))
    d.ellipse((195, 120, 405, 360), fill=(214, 168, 136))
    d.ellipse((185, 95, 415, 230), fill=(48, 34, 28))
    return im.filter(ImageFilter.GaussianBlur(2))

def still(fn, k, theme="dark"):
    cv = B.canvas(theme, 0); fn(cv, k); return cv.convert("RGB")

SCREEN, FACE = app_screen(), stand_in_face()
RESULTS = [still(lambda cv, k: B.big_number(cv, k, 0, 5_000_000, cx=540, cy=900, size=170, glow=B.RED, dur=1.0), 2.0),
           still(lambda cv, k: B.glow_chart(cv, k, [(0, .9), (.3, .7), (.6, .55), (1, .1)], box=(150, 600, 930, 1200), color=B.RED, theme="paper"), 3.0, "paper"),
           still(lambda cv, k: B.unblur_text(cv, k, "Edited by Claude", 0.2, cy=900, size=110, color=B.RED, theme="paper"), 2.0, "paper"),
           still(lambda cv, k: B.number_morph(cv, k, "4h", "4m", "by hand", "with Claude", cy=900), 2.5)]

def S_title(cv, k):
    B.title_box(cv, k - 0.1, "Claude can now edit videos for you", emoji="😮")

def S_captions(cv, k):
    ws = "Claude edited this entire video. Every cut.".split()
    B.word_captions(cv, k, [(w, 0.15 + i * 0.3) for i, w in enumerate(ws)], keys=("entire", "every"), cy=900)

def S_bubble(cv, k):
    B.push_layer(cv, SCREEN, k, 2.6, amount=0.05, cx=540, cy=1000)
    B.face_bubble(cv, k - 0.2, FACE, cx=850, cy=330, r=170)

def S_highlight(cv, k):
    B.push_layer(cv, SCREEN, k, 3.0, amount=0.03, cx=540, cy=1000)
    if k < 1.5: B.ui_highlight(cv, k - 0.2, OPUS_BOX, label="Opus 5.5", label_pos="above")
    else: B.ui_highlight(cv, k - 1.5, EFFORT_BOX, label="Max effort")

def S_files(cv, k):
    B.file_card(cv, k - 0.1, "audio.json", "JSON", ['{ "words": 412,', '  "silences": [3.2, 7.9, 12.4],', '  "cut_at": "silence" }'], cy=560)
    B.file_card(cv, k - 1.0, "design.md", "MD", ["# Look", "two fonts, one accent", "focus-in, nothing tilted"], cy=1060)

def S_results(cv, k):
    i = min(len(RESULTS) - 1, int(k / 0.75))
    B.result_card(cv, k - i * 0.75, RESULTS[i], cy=900, w=760)

def S_endcard(cv, k):
    B.endcard_grid(cv, k, RESULTS + [SCREEN.convert("RGB")] + RESULTS[:1], header="6 edit templates", cy=720, w=900)
    B.cta_box(cv, k - 0.9, "TEMPLATES", cy=1480)

def S_swap(cv, k):
    B.title_box(cv, k, "Claude can now edit videos for you", emoji="😮", out=1.2)
    B.cta_box(cv, k - 1.35, "EDIT", tail="and I'll send you the setup", cy=270)

SEGS = [("title_box", 2.4, S_title), ("word_captions", 2.8, S_captions), ("face_bubble", 2.6, S_bubble),
        ("ui_highlight", 3.0, S_highlight), ("file_card", 2.8, S_files), ("result_card", 3.0, S_results),
        ("endcard_grid + cta_box", 3.2, S_endcard), ("title_box out, cta_box in", 3.0, S_swap)]
STARTS, acc = [], 0.0
for s in SEGS: STARTS.append(acc); acc += s[1]
TOTAL = acc

def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= STARTS[i]: return i, t - STARTS[i]
    return 0, t

def make_frame(i, srcs):
    si, k = seg_at(i / FPS)
    name, dur, fn = SEGS[si]
    cv = B.canvas("dark", i)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(lay, k)
    B.push_layer(cv, lay, k, dur, amount=0.03, cx=540, cy=900)
    B.tag(cv, 1.0, f"{si + 1:02d}/{len(SEGS)}  {name}", 540, 1800, size=32)
    return cv

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--preview"); ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            make_frame(int(round(t * FPS)), ()).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
    else:
        parallel.render(a.out, int(TOTAL * FPS), make_frame, lambda t0: (), workers=a.workers)
