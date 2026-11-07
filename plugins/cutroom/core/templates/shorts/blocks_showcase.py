"""Showcase of the CURRENT blocks (2026-10-12): only what passes style-guide §Polish rules (two fonts, red the one
accent, nothing tilted, no sticker chips / handwriting, focus-in entrances, nothing frozen), plus the Muse Wonder
set from the news-story reel. Default inset layout: dark canvas, graphic zone y 250-1090, face inset (160,1380,920,1920) with the
head popping out. Off-style blocks (sticky_notes, marker_*, cutout, logo_burst, title, thud, phone) are left out
on purpose; the old showcase is in git history (before 2026-10-12).

    python3 blocks_showcase.py OUT.mp4 [--face base.mp4 --mask mask.mp4 --face-start 18] [--preview t1,t2,...]
"""
import sys, os, argparse
REPO = os.environ.get("CUTROOM_SHOWCASE_ROOT", "")   # a folder with assets/logos and the showcase clips
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # packages/core/engine; the agent also sets PYTHONPATH
from PIL import Image, ImageOps
from cutroom import blocks as B, layout as L
from cutroom.core import W, H, FPS, font, SFT, MONO, Reader, text_img, logo
from cutroom import parallel

LG = lambda n: REPO + f"/assets/logos/{n}.png"
MUSE = REPO + "/showcase_assets/"   # the showcase clips/images (avatar, benchmark chart, app icon)
AV, CHART, ICON = MUSE + "external_finkd_avatar.jpg", MUSE + "external_finkd_wonder_benchmarks.webp", MUSE + "external_muse_app_icon.png"
FACE_BOX, SRC_Y = (160, 1380, 920, 1920), 920
GREY = (150, 150, 156)

def src_line(cv, txt, k, y=1066):
    if k > 0: B.place(cv, text_img(txt, font(SFT("Medium"), 24), fill=GREY), 540, y, 1, 0, B.clamp(k / 0.3))

def tile(path, s, white=False):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    if white:                                             # brand mark on a white rounded tile
        bg = Image.new("RGBA", (s, s), (255, 255, 255, 255)); m = logo(path, int(s * 0.7))
        bg.alpha_composite(m, ((s - m.width) // 2, (s - m.height) // 2)); im = bg
    else: im = im.resize((s, s), Image.LANCZOS)
    return B.rounded_rect(im, int(s * 0.225))

# ------------------------------------------------------------------ segments: fn(cv, k)
def S_unblur(cv, k):
    for j, (txt, tw) in enumerate([("1,000", 0.6), ("10K", 1.2), ("100K", 1.8), ("1M", 2.4)]):
        B.unblur_text(cv, k, txt, tw, cy=360 + j * 190, size=120 + j * 14, color=B.RED if j == 3 else None)

def S_focus_tag(cv, k):
    B.focus_in(cv, k - 0.1, logo(LG("meta-color"), 320), 540, 560, d=0.35)
    B.tag(cv, k - 0.8, "Muse Wonder · Oct 12", 540, 820, size=38)
    if k > 1.6: B.ripple(cv, k - 1.6, 540, 560, r0=80, r1=380)

def S_number(cv, k):
    B.big_number(cv, k - 0.2, 0, 5_000_000, cx=540, cy=560, size=150, glow=B.RED, dur=1.0)
    B.unblur_text(cv, k, "downloads in 3 weeks", 1.0, cy=720, size=56, italic=True, shine=False)
    if k > 1.25: B.ripple(cv, k - 1.25, 540, 560, r0=90, r1=420)
    src_line(cv, "big_number + unblur_text + ripple", k)

STOCK = [(0.00, 0.96), (0.12, 0.88), (0.25, 0.80), (0.38, 0.70), (0.50, 0.64), (0.62, 0.50), (0.75, 0.42),
         (0.88, 0.26), (1.00, 0.12)]
def S_chart(cv, k):
    B.glow_chart(cv, k, STOCK, labels={0: "$384", len(STOCK) - 1: "$88"}, box=(150, 420, 930, 900), color=B.RED,
                 dur=1.2, t0=0.2, point_times={0: 0.2, len(STOCK) - 1: 1.4})
    B.focus_in(cv, k - 0.1, text_img("META stock  ·  2021 → 2022", font(SFT("Semibold"), 32), fill=GREY), 540, 330)

def S_versus(cv, k):
    rows = [("Muse Wonder Full", 56, LG("meta-color"), 0.3), ("GPT-6 Astra", 53, LG("openai-light"), 1.0),
            ("Claude Fable 5.1", 53, LG("claude-color"), 1.6)]
    B.versus_bars(cv, k, rows, vmax=60, title="Artificial Analysis Index")
    src_line(cv, "versus_bars: each bar grows on its spoken name", k)

POST = ("Introducing Muse Wonder, our new family of frontier models with state of the art performance "
        "for personal and professional agentic work.")
def S_receipt(cv, k):
    chart = Image.open(CHART).convert("RGBA")
    B.post_receipt(cv, k, AV, "Mark Zuckerberg", "@finkd", POST, chart, (420, 0, 1150, 244),
                   cols=[(442, 795, 1.5)], meta="Oct 12", stats="2.8M views", post_cy=500, chart_y=740)

def S_rewind(cv, k):
    kf = k - 1.9
    B.rewind_counter(cv, k, 2026, 2021, settle="Oct 2021", alpha=1.0)
    front, back = tile(LG("facebook-color"), 240), tile(LG("meta-color"), 240, white=True)
    if k > 1.1: B.flip_tile(cv, kf, front, back, 540, 760, a=B.clamp((k - 1.1) / 0.2))

def S_stream(cv, k):
    src, tg, tc = (270, 640), (800, 470), (800, 810)
    B.focus_in(cv, k, tile(ICON, 240), *src, shadow=(0, 20, 26, 200))
    B.dot_stream(cv, k - 0.6, src, [(tg, 0.2), (tc, 1.0)])
    for path, kk, pos in ((LG("openai-light"), 0.8, tg), (LG("claude-color"), 1.6, tc)):
        if k > kk: B.focus_in(cv, k - kk, B._badge(path, 200), *pos, shadow=(0, 18, 24, 200))

def S_morph(cv, k):
    B.number_morph(cv, k, "600", "3", "words of prompt", "sentences", cy=600, size=300, t_switch=1.2, color_b=B.RED)

def S_prompt(cv, k):
    B.prompt_bar(cv, k, [("build me a landing page", 0.3, 0.8), (" for my budgeting app", 1.2, 0.7)], enter_t=2.3, cy=640)

DOC = ["# Role", "You are a world-class senior expert with 20+ years of experience.", "# Rules",
       "Always think step by step. Never use bullet points unless asked.",
       "Build me a landing page for my budgeting app, for students who hate spreadsheets.",
       "# Format", "Respond in markdown with H2 headings.", "# Tone", "Confident but humble."]
def S_delete(cv, k):
    B.delete_lines(cv, k, DOC, keep={4}, top=300, t_sel=0.4, t_del=1.5, size=28, theme="dark")

SEGS = [("unblur_text", 3.3, S_unblur), ("focus_in + tag + ripple", 2.6, S_focus_tag), ("big_number", 2.8, S_number),
        ("glow_chart", 3.0, S_chart), ("versus_bars", 3.4, S_versus), ("post_receipt", 3.0, S_receipt),
        ("rewind_counter + flip_tile", 3.2, S_rewind), ("dot_stream", 3.2, S_stream), ("number_morph", 2.8, S_morph),
        ("prompt_bar", 3.2, S_prompt), ("delete_lines", 3.2, S_delete), ("punch-in  Framing.face(punch=)", 3.0, None)]
STARTS, acc = [], 0.0
for s in SEGS: STARTS.append(acc); acc += s[1]
TOTAL = acc

def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= STARTS[i]: return i, t - STARTS[i]
    return 0, t

FRAMING = L.Framing([], wide=1.0, tight=1.1, face_cy=0.4)
def make_frame(i, srcs):
    t = i / FPS
    si, k = seg_at(t)
    name, dur, fn = SEGS[si]
    face = srcs[0].next() if srcs else None
    mask = srcs[1].next().convert("L") if len(srcs) > 1 else None
    if fn is None:                                        # punch-in: full face, hard 1.2x cut at 1.4s
        cv = (FRAMING.face(face, t, punch=STARTS[si] + 1.4) if face else B.canvas("dark", i)).convert("RGBA")
    else:
        cv = B.canvas("dark", i)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(lay, k)
        B.push_layer(cv, lay, k, dur, amount=0.04, cx=540, cy=660)   # never frozen
        if face: B.face_inset(cv, face, mask, FACE_BOX, src_y=SRC_Y, theme="dark")
    B.tag(cv, 1.0, f"{si + 1:02d}/{len(SEGS)}  {name}", 540, 1400 if fn is None else 1160, size=32)   # where the caption would sit
    return cv

def open_sources(t0, a):
    if not a.face: return ()
    srcs = [Reader(a.face, 1080, 1920, start=a.face_start + t0)]
    if a.mask and os.path.exists(a.mask): srcs.append(Reader(a.mask, 540, 960, start=a.face_start + t0))
    return tuple(srcs)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--face"); ap.add_argument("--mask"); ap.add_argument("--face-start", type=float, default=18.0)
    ap.add_argument("--preview"); ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            srcs = open_sources(t, a)
            make_frame(int(round(t * FPS)), srcs).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
            for s in srcs: s.close()
    else:
        parallel.render(a.out, int(TOTAL * FPS), make_frame, lambda t0: open_sources(t0, a), workers=a.workers)
