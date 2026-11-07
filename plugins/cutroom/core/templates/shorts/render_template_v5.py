# TEMPLATE (from the Opus 5.5 reel, v5). Copy into <video folder>/edit/. Keep the layout/caption/stack setup; replace the
# content: EMPH phrases, g_* graphics, MONTAGE, TIMELINE, OVERLAYS (anchor every time to the QA transcript).
"""v5 compositor (APPROVED house style) — graphics in a dotted-black top half, face filling the full-width
bottom half (seam 960), hands-only pop-out, centered fixed captions with a dark pill on the seam,
red type-on headers, glowing cards; full screen only for the end card.
Usage:  python renderN.py --preview 1.5,8,20      python renderN.py
Needs: base_vN.mp4, base_vN_transcript.json, segments.json, mask_vN.mp4 (personmask.swift), mix_vN.wav"""
import sys, os, json
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # packages/core/engine; the agent also sets PYTHONPATH
from PIL import Image, ImageDraw, ImageFilter
from cutroom.core import *
from cutroom import captions as cap, layout as L, components as C
from cutroom.components import ACCENT
from cutroom import safezone as SZ
from cutroom.storyboard import Storyboard

BASE, MASK, OUT, MIX = "base_v3.mp4", "mask_v3.mp4", "opus55_v5.mp4", "mix_v5.wav"
TAIL = 1.3
EA = "external_assets/"
DUR = probe_duration(BASE)
STYLE = "kallaway"
SB = Storyboard.load("storyboard.json")   # ONE timeline: layouts + cue times (sound reads the same file)

# ------------------------------------------------------------------ captions
EMPH = ["Opus 5.5", "best AI model", "GPT-6 Astra", "every single day.", "create videos", "AGI vibes.",
        "video editing.", "Claude Code.", "the writing.", "human readable.", "fixed it.", "copywriting.",
        "plain English.", "back over to Claude.", "power of Claude."]
words = cap.load_words("base_v3_transcript.json", fixes={"Cloud": "Claude", "Claw": "Claude"})
words = cap.join_phrases(words, EMPH)
SPANS = cap.chunk(words, STYLE)

# ------------------------------------------------------------------ assets
HERO = Image.open("assets/hero_bg.jpg").convert("RGB")
CLAUDE = logo("assets/claude-color.png", 256)
OPENAI = logo("assets/openai.png", 256)
CC = logo("assets/claudecode-color.png", 128)

GZ = 1000                     # graphic zone height (stack layout); face card starts at 1110
CARD_W = 900

HEAD_Y = 260          # safe zone: platform UI covers the top ~250 px (Shorts/Reels)

def stage(t, t0, header, sub=None, hk=0.0):
    """Dotted black graphic zone with a red type-on header."""
    im = C.dotted_bg(W, H)
    C.red_header(im, t - t0 - hk, header, W / 2, HEAD_Y, size=58, sub=sub, sub_size=44)
    return im

def place_card(im, content, k, y):
    """Glow-wrap content and rise it in (expo, 0.5 s)."""
    g = C.glow_card(content)
    p = expo(k / 0.5)
    paste(im, g, W / 2 - g.width / 2, y - g.pad + (1 - p) * 50, cubic(k / 0.35))

# ------------------------------------------------------------------ stack graphics (draw on full canvas)
def g_hero(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "Just dropped")
    card = cover(HERO, CARD_W, 530, z=1.1 - 0.05 * cubic(k / 3)).convert("RGBA")
    card.alpha_composite(vgrad(CARD_W, 530, 0, 150, power=1.5))
    paste(card, CLAUDE.resize((80, 80), Image.LANCZOS), 56, 220, cubic((k - 0.15) / 0.3))
    a, b = text_img("Claude", font(SFD("Semibold"), 108)), text_img("Opus 5.5", font(SFD("Semibold"), 108))
    reveal(card, a, 56 - a.pad - 4, 290, (k - 0.2) / 0.45)
    reveal(card, b, 56 - b.pad - 4, 400, (k - 0.28) / 0.45)
    place_card(im, card, k, 360)
    return im

BENCH = [("Agentic coding", "Terminal-Bench 4.0", [("Opus 5.5", 66.4, "66.4%", 100, True), ("GPT-6 Astra", 57.9, "57.9%", 100, False)]),
         ("Knowledge work", "GDPval-AA · Elo", [("Opus 5.5", 1846, "1846", 2000, True), ("GPT-6 Astra", 1542, "1542", 2000, False)])]
def g_bench(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "Opus 5.5 vs GPT-6 Astra")
    panel = C.bars_panel(k - 0.3, CARD_W, 530, "", BENCH, source="Source: Anthropic, Opus 5.5 announcement (Sep 22, 2026)", grid=False, gap=230)
    place_card(im, panel, k - 0.3, 360)
    return im

# montage clips: (file, src_start, out_start, out_end, credit, precrop)
MONTAGE = [
    ("external_oldnoob007_gpt6_remake.mp4", 1.0, 17.90, 21.10, "@Oldnoob007", "crop=iw*0.8:ih*0.78,"),
    ("external_anishmoonka_van_gogh.mp4", 243.5, 21.10, 23.00, "@anishmoonka", ""),
    ("external_abhi81i_beacon.mp4", 107.0, 23.00, 24.90, "@abhi81i", ""),
    ("external_klehmann79_product_film.mp4", 29.5, 24.90, 26.90, "@Klehmann79", ""),
    ("external_jmythoren_launch.mp4", 3.6, 26.90, 29.00, "@jmythoren", ""),
]
CW, CH = 1080, 608
readers, FRAMES = {}, {}
def clip_reader(i):
    f, s, a, b, h, pre = MONTAGE[i]
    if i not in readers: readers[i] = Reader(EA + f, CW, CH, s, precrop=pre)
    return readers[i]

def credit_img(h):
    return C.kicker(f"Made with Claude · {h}", col=(215, 215, 220), size=26)

def g_clip(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "Made entirely in Claude", sub="No tools. No video editor.")
    fr = FRAMES[0]
    card = cover(fr, CARD_W, 460, z=1.0 + 0.04 * clamp(k / 3)).convert("RGBA")
    place_card(im, card, k - 0.1, 400)
    cr = credit_img(MONTAGE[0][4])
    paste(im, cr, W / 2 - cr.width / 2, 872, cubic((k - 0.4) / 0.3))
    return im

TERM_LINES = [("●", "Reading brief + brand assets"), ("●", "Writing scenes + captions"),
              ("●", "Rendering 1080x1920 @ 30fps"), ("✓", "launch_video.mp4 ready")]
def g_terminal(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "All inside Claude Code")
    panel = C.terminal_panel(k - 0.25, CARD_W, 530, CC, "Claude Code", "make a 30s launch video for our product, animated captions",
                             TERM_LINES, type_cps=48, bare=True)
    place_card(im, panel, k - 0.2, 360)
    return im

CHECKS = [(SB.cue("tick1"), "Copywriting"), (SB.cue("tick2"), "Plain-English updates")]   # ticks = ding cues
def g_check(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "So much better at")
    panel = C.checklist_panel(t, CARD_W, 400, "", CHECKS, y0=70, grid=False)
    place_card(im, panel, k - 0.2, 430)
    return im

# ------------------------------------------------------------------ full-screen scenes (only where needed)
def full_montage(canvas, t, t0, t1):
    idx = max(i for i in range(1, len(MONTAGE)) if MONTAGE[i][2] <= t or i == 1)
    fr = FRAMES[idx]
    ct = t - MONTAGE[idx][2]
    canvas.paste(C.dotted_bg(W, H))
    z = 1.28
    cw, ch = int(CW * z), int(CH * z)
    big = fr.resize((cw, ch), Image.BICUBIC)
    drift = (cw - W) * (0.2 + 0.6 * clamp(ct / 2.2))
    cy = 600
    canvas.paste(big.crop((int(drift), 0, int(drift) + W, ch)), (0, int(cy - ch / 2)))
    d = ImageDraw.Draw(canvas)
    d.line([(0, cy - ch / 2), (W, cy - ch / 2)], fill=(255, 255, 255, 120), width=2)
    d.line([(0, cy + ch / 2), (W, cy + ch / 2)], fill=(255, 255, 255, 120), width=2)
    cr = credit_img(MONTAGE[idx][4])
    paste(canvas, cr, W / 2 - cr.width / 2, cy + ch / 2 + 30, cubic(ct / 0.3))
    for i in range(1, len(MONTAGE)):
        c = WHITE if i == idx else (70, 70, 76)
        x = W / 2 - 2 * 40 + (i - 1) * 40
        d.rectangle((x, cy + ch / 2 + 80, x + 28, cy + ch / 2 + 83), fill=c + (255,))
    C.red_header(canvas, t - t0, "Made with Claude", W / 2, 120, size=54, sub="Truly insane.", sub_size=46)

T_FIX = SB.cue("wipe")                 # wipe = whoosh cue
OPUS5 = [("h", "What I found"),
         ("p", "The extra drop isn’t the free tier — it’s a regression in 0552feb (“extract billing period boundaries into periods.py”, labelled “No behaviour change”)."),
         ("h", "The bug"), ("p", "aggregate.monthly_usage used to do a half-open interval:"),
         ("c", "start, end = month_start(year, month),"), ("c", "    next_month_start(year, month)"),
         ("c", "if start <= e.ts < end:"), ("p", "It now does:"), ("c", "if period.contains(e.ts)"),
         ("p", "and in periods.py:"), ("c", "@property"), ("c", "def last_day(self) -> datetime:"),
         ("c", "    return next_month_start(...) - timedelta(days=1)"),
         ("p", "last_day is a datetime at midnight, not a whole day. Subtracting one day from Sep 1 00:00 gives Aug 31 00:00, and the comparison is inclusive, so the period effectively ends at the first instant of the 31st.")]
OPUS55 = [("H", "The extra drop is a bug in the billing refactor"),
          ("p", "The free-tier change accounts for only $1.50 of acme’s August drop. The other $9.92 comes from a bug in commit 0552feb."),
          ("p", "That commit was labelled “No behaviour change,” but it stops counting usage from the last day of the month.")]
DOC_W = 820
DOC5, _ = C.render_doc(OPUS5, (70, 68, 66), width=DOC_W, sizes=(40, 40, 62, 27))
DOC55, MARKS55 = C.render_doc(OPUS55, INK, width=DOC_W, sizes=(40, 40, 62, 27))
TAG5, TAG55 = C.model_tag("Claude Opus 5", False, 36), C.model_tag("Claude Opus 5.5", True, 36)
CHIPS = [C.chip("Main point first"), C.chip("Less jargon")]
PAGE_W, PAGE_H = 900, 460
FADE = C.paper_fade(PAGE_W, 140)
W_SRC = C.kicker("Real outputs · Anthropic Opus 5.5 announcement", col=(150, 150, 156), size=22)

def full_writing(canvas, t, t0, t1):
    """Dotted black stage, red header, a glowing paper page that swaps from 5 -> 5.5."""
    k = t - t0
    canvas.paste(C.dotted_bg(W, H))
    before = t < T_FIX
    C.red_header(canvas, k, "Same prompt, both models", W / 2, HEAD_Y, size=50,
                 sub="“Please explain the issue to me.”", sub_size=38)
    page = Image.new("RGBA", (PAGE_W, PAGE_H), PAPER + (255,))
    x = 40
    if before:
        paste(page, TAG5, x - 2, 36, 1)
        scroll = (DOC5.height - (PAGE_H - 160)) * inout(clamp((k - 1.4) / (T_FIX - t0 - 1.6)))
        page.alpha_composite(DOC5.crop((0, int(scroll), DOC_W, int(scroll) + PAGE_H - 140)), (x, 130))
        page.alpha_composite(FADE, (0, PAGE_H - 140))
    else:
        f = t - T_FIX
        new = Image.new("RGBA", (PAGE_W, PAGE_H), PAPER + (255,))
        paste(new, TAG55, x - 2, 36, 1)
        nd = ImageDraw.Draw(new)
        hp = expo((f - 0.5) / 0.7)
        for my, mw in MARKS55:
            if hp > 0: nd.rectangle((x - 6, 130 + my + 10, x - 6 + (mw + 12) * hp, 130 + my + 74), fill=C.HILITE + (150,))
        new.alpha_composite(DOC55, (x, 130))
        for i, ch in enumerate(CHIPS):
            ck = f - 1.1 - i * 0.18
            paste(new, ch, x + i * 320, 130 + DOC55.height + 30 + (1 - expo(ck / 0.4)) * 20, cubic(ck / 0.3))
        wx = int(PAGE_W * expo(f / 0.45))
        if wx < PAGE_W:
            paste(page, TAG5, x - 2, 36, 1)
            page.alpha_composite(DOC5.crop((0, int(DOC5.height - (PAGE_H - 160)), DOC_W, int(DOC5.height - 20))), (x, 130))
            page.alpha_composite(new.crop((0, 0, wx, PAGE_H)), (0, 0))
            ImageDraw.Draw(page).rectangle((wx - 3, 0, wx + 3, PAGE_H), fill=C.RED + (255,))
        else:
            page = new
    place_card(canvas, page, k - 0.25, 400)
    paste(canvas, W_SRC, W / 2 - W_SRC.width / 2, 874, cubic((k - 1.0) / 0.4))

def g_writing(t, t0, t1):
    im = Image.new("RGBA", (W, H)); full_writing(im, t, t0, t1); return im

def g_montage(t, t0, t1):
    """Montage as a stack: clip card on top (continues g_clip's layout), face below."""
    idx = max(i for i in range(1, len(MONTAGE)) if MONTAGE[i][2] <= t or i == 1)
    ct = t - MONTAGE[idx][2]
    im = stage(t, t0, "Made with Claude", sub="Truly insane.")
    card = cover(FRAMES[idx], CARD_W, 460, z=1.0 + 0.05 * clamp(ct / 2.2)).convert("RGBA")
    place_card(im, card, t - t0, 400)
    cr = credit_img(MONTAGE[idx][4])
    paste(im, cr, W / 2 - cr.width / 2, 872, cubic(ct / 0.3))
    d = ImageDraw.Draw(im)
    for i in range(1, len(MONTAGE)):
        c = WHITE if i == idx else (70, 70, 76)
        x = W / 2 - 2 * 40 + (i - 1) * 40
        d.rectangle((x, 906, x + 28, 909), fill=c + (255,))
    return im

END_T1 = text_img("Claude", font(SFD("Semibold"), 150))
END_T2 = text_img("Opus 5.5", font(SFD("Semibold"), 150))
def full_end(canvas, t, t0, t1):
    k = t - t0
    canvas.paste(cover(HERO, W, H, z=1.02 + 0.04 * cubic(k / 2.5)))
    canvas.alpha_composite(vgrad(W, 900, 0, 190, power=1.5), (0, H - 900))
    x = 80
    paste(canvas, CLAUDE.resize((96, 96), Image.LANCZOS), x, 1030, cubic(k / 0.3))
    reveal(canvas, END_T1, x - END_T1.pad - 6, 1140, (k - 0.06) / 0.45)
    reveal(canvas, END_T2, x - END_T2.pad - 6, 1300, (k - 0.14) / 0.45)

# ------------------------------------------------------------------ timeline (output seconds)
# beat id (storyboard.json) -> draw function. Beat times/layouts come from the storyboard.
TIMELINE = SB.timeline({"hook": g_hero, "bench": g_bench, "clip": g_clip, "montage": g_montage,
                        "terminal": g_terminal, "writing": g_writing, "checks": g_check, "end": full_end})
def ov_header(text, sub=None):
    return lambda c, k, a: C.red_header(c, k, text, W / 2, HEAD_Y, size=56, sub=sub, sub_size=48)
def ov_swap(c, k, a):
    cx, cy = W / 2, 440
    oa = C.tile(OPENAI, 170, r=40, bg=(20, 20, 22))
    cl = C.tile(CLAUDE, 170, r=40, bg=(250, 247, 242))
    sw = expo((k - 1.05) / 0.45)
    C.float_img(c, k, oa, cx - 130 * sw, cy, a=a * (1 - 0.6 * sw))
    if sw > 0:
        ImageDraw.Draw(c).line([(cx - 130 * sw - 70, cy + 70), (cx - 130 * sw + 70, cy - 70)],
                               fill=C.RED + (int(255 * a * sw),), width=8)
        C.float_img(c, k - 1.05, cl, cx + 130 * sw, cy, a=a)
OVERLAYS = SB.overlays({"best_model": ov_header("The best AI model", sub="available right now."),
                        "ch1": ov_header("1. It makes videos"), "ch2": ov_header("2. The writing"),
                        "swap": ov_swap})
# Any `click` cue needs a visible press: C.press(canvas, t - SB.cue("<name>"), x, y) in that beat's draw fn.

BASE_CUTS = [m["out_start"] for m in json.load(open("segments.json"))[1:]]
FACE_STARTS = [t1 for t0, t1, *_ in TIMELINE]
FRAMING = L.Framing(BASE_CUTS + FACE_STARTS, wide=1.28, tight=1.38, face_cy=1.0)   # tight + bottom-anchored so the centered caption (y=960) sits on the chin, not the mouth
STACK = L.Stack(FRAMING)   # v5 defaults: full-width bottom half, seam 960, headroom, hands-only pop-out
TOPGRAD = vgrad(W, 700, 170, 0, power=1.3)

def compose(t, base, mask):
    mode, fn, t0, t1 = L.resolve(t, TIMELINE)
    if mode == "face":
        canvas = FRAMING.face(base, t).convert("RGBA")
        for a0, a1, ov in OVERLAYS:
            e = env(t, a0, a1, 0.01, 0.2)
            if e > 0:
                canvas.alpha_composite(with_alpha(TOPGRAD, min(1, (t - a0) / 0.25) * e))
                ov(canvas, t - a0, e)
    elif mode == "stack":
        canvas = fn(t, t0, t1)
        STACK.draw(canvas, base, mask, t)
    else:
        canvas = Image.new("RGBA", (W, H), DARK + (255,))
        fn(canvas, t, t0, t1)
    cap.draw(canvas, t, SPANS, mode, STYLE)
    return canvas.convert("RGB")

def advance(t):
    for i, m in enumerate(MONTAGE):
        if m[2] - 0.04 <= t < m[3] + 0.04:
            FRAMES[i] = clip_reader(i).next()

def main():
    n = int((DUR + TAIL) * FPS)
    base = Reader(BASE, W, H, 0, fill=False)
    mreader = Reader(MASK, 540, 960, 0, fill=False)
    grab = lambda: (base.next(), mreader.next().convert("L"))
    if "--preview" in sys.argv:
        times = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        want = {int(round(x * FPS)) for x in times}
        os.makedirs("previews", exist_ok=True)
        for i in range(max(want) + 1):
            b, m = grab(); t = i / FPS
            advance(t)
            if i in want:
                im = compose(t, b, m)
                if "--safe" in sys.argv: im = SZ.overlay(im).convert("RGB")   # review only
                im.save(f"previews/p_{t:05.2f}.jpg", quality=85)
        return
    enc = Encoder(OUT, audio=MIX if os.path.exists(MIX) else None)
    for i in range(n):
        b, m = grab(); t = i / FPS
        advance(t)
        enc.write(compose(t, b, m))
        if i % 300 == 0: print(f"frame {i}/{n}", flush=True)
    enc.close()
    for r in readers.values(): r.close()
    print("done", OUT)

if __name__ == "__main__":
    main()
