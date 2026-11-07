# TEMPLATE (v6 "flow", from the Opus 5.5 video-prompts reel v2, 2026-09-26, the user's favourite flow).
# Copy into <video folder>/edit/. Keep stage/place_card/full_frame/g_full/prompt_box/compose; replace CLIPS, EMPH, PUNCT,
# the g_* graphics, TIMELINE and OVERLAYS. Every time comes from the storyboard (SB.cue / SB.beat / seg()).
"""Opus 5.5 one-prompt videos v2: v5 house style + full-screen X examples (9:16 source).
Usage:  python render2.py --preview 1.5,8,20 [--safe]      python render1.py
Needs: base_v2.mp4, base_v2_transcript.json, segments.json, mask_v2.mp4, mix_v2.wav"""
import sys, os, json
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # packages/core/engine; the agent also sets PYTHONPATH
from PIL import Image, ImageDraw, ImageFilter
from cutroom.core import *
from cutroom import captions as cap, layout as L, components as C
from cutroom.components import ACCENT, HILITE
from cutroom import safezone as SZ
from cutroom.storyboard import Storyboard
from cutroom import parallel as PR

BASE, MASK, OUT, MIX = "base_v2.mp4", "mask_v2.mp4", "opus_video_prompts_v2.mp4", "mix_v2.wav"
TAIL = 1.3
EA = "external_assets/"
DUR = probe_duration(BASE)
STYLE = "kallaway"
SB = Storyboard.load("storyboard.json")

def cue_dur(name):
    for b in SB.beats:
        for c in b.get("cues", []):
            if c.get("name") == name: return c.get("dur", 1.0)

# ------------------------------------------------------------------ captions
EMPH = ["video editor", "Opus 5.5", "Claude Code.", "absolutely ridiculous.", "10 to 20 grand",
        "one to two line prompts.", "external tool.", "JavaScript and Python."]
words = cap.load_words("base_v2_transcript.json", fixes={"cloud": "Claude", "Cloud": "Claude", "opus": "Opus", "i": "I"})
# whisper returned the first half lowercase with no punctuation: restore sentence case at these times
PUNCT = {0.02: "You", 7.72: "editing.", 8.20: "This", 12.48: "Code.", 12.74: "Because", 19.10: "tool.",
         19.38: "Like,", 20.70: "anymore.", 21.06: "It's", 22.46: "Code.", 22.74: "And", 25.38: "ridiculous.", 26.22: "This"}
for w in words:
    for ts, txt in PUNCT.items():
        if abs(w["s"] - ts) < 0.03: w["w"] = txt
    if w["w"] == "code" and words.index(w) > 0 and words[words.index(w) - 1]["w"] == "Claude": w["w"] = "Code"
words = cap.join_phrases(words, EMPH)
SPANS = cap.chunk(words, STYLE)
cap.STYLES[STYLE]["y"]["face"] = 1400   # this take sits low in frame: keep face captions below the chin
cap.STYLES[STYLE]["y"]["full"] = 1400   # full-screen examples: same spot as face shots, under the clip

# ------------------------------------------------------------------ assets
CLAUDE = logo("assets/claude-color.png", 256)
CC = logo("assets/claudecode-color.png", 128)
HEAD_Y = 260
TOPGRAD = vgrad(W, 700, 170, 0, power=1.3)
CARD_W = 900

def stage(t, t0, header, sub=None):
    im = C.dotted_bg(W, H)
    C.red_header(im, t - t0, header, W / 2, HEAD_Y, size=56, sub=sub, sub_size=42)
    return im

def place_card(im, content, k, y, x=None):
    g = C.glow_card(content)
    p = expo(k / 0.5)
    x = W / 2 - g.width / 2 if x is None else x - g.pad
    paste(im, g, x, y - g.pad + (1 - p) * 50, cubic(k / 0.35))

def credit_img(h):
    return C.kicker(f"Made with Claude · {h}", col=(215, 215, 220), size=26)

# ------------------------------------------------------------------ X clips
# key: (file, src_start, out_start, out_end, credit, native (w, h))
def seg(beat, i, n):
    b = SB.beat(beat); d = (b["t1"] - b["t0"]) / n
    return b["t0"] + i * d, b["t0"] + (i + 1) * d
HD, SQ, SQ2, V = (1920, 1080), (1440, 1440), (1080, 1080), (1080, 1920)
CLIPS = {
    "leon":   ("external_leonabboud_showreel.mp4", 1.6, *seg("hook", 0, 1), "@leonabboud", (960, 540)),
    "jack":   ("external_jackfriks_short_9x16.mp4", 11.0, *seg("hookfull", 0, 5), "@jackfriks", V),
    "peter":  ("external_petergyang_goldengate.mp4", 3.0, *seg("hookfull", 1, 5), "@petergyang", HD),
    "lc":     ("external_lcslates_mosaic.mp4", 11.5, *seg("hookfull", 2, 5), "@LCSlates", SQ2),
    "robots": ("external_konstantinsaifo_manufacturing.mp4", 88.5, *seg("hookfull", 3, 5), "@konstantinsaifo", HD),
    "leon2":  ("external_leonabboud_showreel.mp4", 4.2, *seg("hookfull", 4, 5), "@leonabboud", HD),
    "two":    ("external_twoclipping_keynote.mp4", 6.5, *seg("examples", 0, 2), "@twoclipping", SQ),
    "ships":  ("external_konstantinsaifo_manufacturing.mp4", 79.5, *seg("examples", 1, 2), "@konstantinsaifo", HD),
    "ik":     ("external_ik_builds_launch.mp4", 2.4, *seg("agency", 0, 1), "@ik_builds", HD),
    "deedy":  ("external_deedydas_inference.mp4", 3.2, *seg("r1", 0, 1), "@deedydas", HD),
    "moritz": ("external_moritzkremb_saas.mp4", 0.5, *seg("r2", 0, 1), "@moritzkremb", HD),
    "paper":  ("external_deedydas_paper.mp4", 29.5, SB.beat("code")["t0"], 63.5, "@deedydas", HD),
    "chh":    ("external_chhddavid_motion.mp4", 41.0, 63.5, 64.7, "@chhddavid", HD),
    "globe":  ("external_konstantinsaifo_manufacturing.mp4", 99.0, 64.7, 99.0, "@konstantinsaifo", HD),
}
readers, FRAMES = {}, {}
def advance(t):
    for k, (f, s, a, b, h, wh) in CLIPS.items():
        if a - 0.04 <= t < b + 0.04:
            if k not in readers: readers[k] = Reader(EA + f, wh[0], wh[1], s + PR.clip_offset(t, a))
            FRAMES[k] = readers[k].next()
        elif k in readers and t >= b + 0.04:
            readers.pop(k).close()

def clip_card(im, key, t, y, w=CARD_W, h=506, k_in=None):
    f, s, a, b, handle, wh = CLIPS[key]
    ct = t - a
    card = cover(FRAMES[key], w, h, z=1.0 + 0.04 * clamp(ct / 4)).convert("RGBA")
    place_card(im, card, ct if k_in is None else k_in, y)
    cr = credit_img(handle)
    paste(im, cr, W / 2 - cr.width / 2, y + h + 14, cubic((ct - 0.3) / 0.3))

def g_clip(key, header, sub=None):
    def fn(t, t0, t1):
        im = stage(t, t0, header, sub)
        clip_card(im, key, t, 370, k_in=t - t0 - 0.1)
        return im
    return fn

# ------------------------------------------------------------------ checklist
CHECKS = [(SB.cue("tick1"), "Animates"), (SB.cue("tick2"), "Comes up with concepts"), (SB.cue("tick3"), "Directs")]
def g_can(t, t0, t1):
    k = t - t0
    im = stage(t, t0, "What Opus 5.5 does now")
    panel = C.checklist_panel(t, CARD_W, 470, "", CHECKS, y0=40, grid=False)
    place_card(im, panel, k - 0.2, 360)
    ak = t - SB.cue("allcc")
    if ak > 0:
        row = Image.new("RGBA", (560, 70), (0, 0, 0, 0))
        row.alpha_composite(CC.resize((56, 56), Image.LANCZOS), (0, 7))
        tx = text_img("All inside Claude Code", font(SFD("Semibold"), 40))
        row.alpha_composite(tx, (74 - tx.pad, 35 - tx.height // 2))
        paste(im, row, W / 2 - 250, 846 + (1 - expo(ak / 0.4)) * 20, cubic(ak / 0.3))
    return im

# ------------------------------------------------------------------ simple Claude Code prompt box
FCODE = font(CODE, 38)
FT = font(SFT("Semibold"), 28)
def prompt_box(t, lines, w=CARD_W, hl=None):
    """Simple Claude Code input: small label row, rounded input, '>' lines typed on in sync.
    lines: [(text, t_start, dur)]; hl: (line_index, t_on) yellow marker behind that line."""
    wrapped = []
    for txt, ts, du in lines:
        n = int(len(txt) * clamp((t - ts) / du)) if t >= ts else 0
        wrapped.append((wrap(txt, FCODE, w - 150), n, ts, du, txt))
    rows = sum(max(1, len(wl)) for wl, *_ in wrapped)
    h = 76 + rows * 54 + 44
    im = Image.new("RGBA", (w, h), (24, 22, 21, 255))
    d = ImageDraw.Draw(im)
    im.alpha_composite(CC.resize((36, 36), Image.LANCZOS), (28, 20))
    d.text((74, 23), "Claude Code", font=FT, fill=(240, 235, 230))
    d.text((w - 28, 26), "Opus 5.5", font=font(SFT("Medium"), 24), fill=(150, 142, 136), anchor="ra")
    d.rounded_rectangle((20, 70, w - 20, h - 20), 14, outline=(96, 90, 86), width=2)
    y = 88
    cursor = None
    for li, (wl, n, ts, du, txt) in enumerate(wrapped):
        d.text((44, y), ">", font=FCODE, fill=ACCENT)
        if hl and hl[0] == li and t > hl[1]:
            hw = FCODE.getlength(txt) * expo((t - hl[1]) / 0.45)
            d.rectangle((80, y, 88 + hw, y + 50), fill=HILITE + (110,))
        left = n
        for ln in (wl or [""]):
            part = ln[:max(0, left)]
            d.text((84, y), part, font=FCODE, fill=(236, 231, 226))
            if 0 <= left <= len(ln) and t >= ts - 0.8:
                cursor = (84 + FCODE.getlength(part), y)
            left -= len(ln) + 1
            y += 54
    if cursor and (int(t * 2.2) % 2 == 0 or any(ts <= t < ts + du for _, _, ts, du, _ in wrapped)):
        d.rectangle((cursor[0] + 3, cursor[1] + 4, cursor[0] + 23, cursor[1] + 48), fill=(236, 231, 226))
    return im

P1 = "make a modern, slick, punchy video for a startup that works on inference"
P2 = "I want you to create a highly professional SaaS launch video for my product."
def g_prompt(t, t0, t1):
    """p1 / p2: just the box typing; Enter is pressed, then the result cuts to full screen (r1 / r2)."""
    first = t < SB.beat("p2")["t0"]
    im = stage(t, t0 if first else SB.beat("p1")["t0"], "One prompt, one video")
    lines = [(P1, SB.cue("type1"), cue_dur("type1"))] if first else [(P2, SB.cue("type2"), cue_dur("type2"))]
    box = prompt_box(t, lines)
    y = 400
    place_card(im, box, t - t0 - 0.1, y)
    ex, ey = W / 2 + CARD_W / 2 - 50, y + box.height - 50
    C.press(im, t - SB.cue("enter1" if first else "enter2"), ex, ey)
    return im

# ------------------------------------------------------------------ full-screen examples
CLIP_Y, CLIP_H = 330, 960
def credit_pill(handle):
    cr = credit_img(handle)
    pill = Image.new("RGBA", (cr.width + 24, cr.height + 14), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), 12, fill=(0, 0, 0, 175))
    pill.alpha_composite(cr, (12, 7))
    return pill

def full_frame(key, t):
    """Every clip fills a full-width band (y 330-1290) over a blurred, darkened copy of itself; 16:9
    clips drift slowly so more of the frame is seen. 9:16 clips are banded too: their own on-screen
    text would otherwise collide with the header."""
    f, s, a, b, handle, wh = CLIPS[key]
    fr, ct = FRAMES[key], t - a
    pop = 1.0 + 0.05 * (1 - expo(ct / 0.35))        # small settle on every cut
    bg = cover(fr, 270, 480).filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    im = Image.blend(bg, Image.new("RGB", (W, H), (8, 8, 9)), 0.55).convert("RGBA")
    vert = wh[1] > wh[0]
    drift = 0.5 if wh[0] <= wh[1] else 0.35 + 0.3 * inout(clamp(ct / max(0.8, b - a)))
    band = cover(fr, W, CLIP_H, z=pop + 0.04 * clamp(ct / 3), cx=drift, cy=0.55 if vert else 0.5).convert("RGBA")
    im.alpha_composite(band, (0, CLIP_Y))
    return im, CLIP_Y + 20

def g_full(keys, header):
    def fn(t, t0, t1):
        key = next(k for k in keys if CLIPS[k][2] - 0.001 <= t < CLIPS[k][3]) if t < CLIPS[keys[-1]][3] else keys[-1]
        im, cy = full_frame(key, t)
        im.alpha_composite(TOPGRAD)
        C.red_header(im, t - t0, header, W / 2, HEAD_Y, size=56)
        ck = t - CLIPS[key][2]
        paste(im, credit_pill(CLIPS[key][4]), 90, cy + (1 - expo(ck / 0.4)) * 12, cubic((ck - 0.1) / 0.3))
        return im
    return fn

L1 = "make a launch video for my product"
L2 = "Don't use any external tools."
def g_how(t, t0, t1):
    im = stage(t, t0, "How to start")
    box = prompt_box(t, [(L1, SB.cue("type3"), cue_dur("type3")), (L2, SB.cue("type4"), cue_dur("type4"))],
                     hl=(1, SB.cue("hl")))
    place_card(im, box, t - t0 - 0.1, 400)
    return im

# ------------------------------------------------------------------ timeline + face overlays
TIMELINE = SB.timeline({"hook": g_clip("leon", "Made with one prompt"),
                        "hookfull": g_full(["jack", "peter", "lc", "robots", "leon2"], "Made with one prompt"),
                        "can": g_can,
                        "examples": g_full(["two", "ships"], "The examples"),
                        "agency": g_full(["ik"], "\u201cI was quoted $3,000 for this\u201d"),
                        "p1": g_prompt, "r1": g_full(["deedy"], "The result"),
                        "p2": g_prompt, "r2": g_full(["moritz"], "The result"),
                        "how": g_how,
                        "code": g_full(["paper", "chh", "globe"], "Just JavaScript + Python")})
def ov_header(text, sub=None):
    def fn(c, k, a):
        C.red_header(c, k, text, W / 2, HEAD_Y, size=56, sub=sub, sub_size=44)
    return fn
OVERLAYS = SB.overlays({"edited": ov_header("This video? Edited by Opus 5.5"),
                        "prompts": ov_header("Just 1\u20132 line prompts"),
                        "skills": ov_header("Old skills? Not needed")})

BASE_CUTS = [m["out_start"] for m in json.load(open("segments.json"))[1:]]
FACE_STARTS = [t1 for t0, t1, *_ in TIMELINE]
FRAMING = L.Framing(BASE_CUTS + FACE_STARTS, wide=1.12, tight=1.2, face_cy=1.0)
STACK = L.Stack(FRAMING, src_top=0.25)   # head sits at 0.29-0.73 of this source

def compose(t, base, mask):
    mode, fn, t0, t1 = L.resolve(t, TIMELINE)
    if mode == "face":
        punch = next((b["punch"] for b in SB.beats if "punch" in b and b["t0"] <= t < b["t1"]), None)   # Kallaway punch-in
        canvas = FRAMING.face(base, t, punch).convert("RGBA")
        for a0, a1, ov in OVERLAYS:
            e = env(t, a0, a1, 0.01, 0.2)
            if e > 0:
                canvas.alpha_composite(with_alpha(TOPGRAD, min(1, (t - a0) / 0.25) * e))
                ov(canvas, t - a0, e)
    elif mode == "full":
        canvas = fn(t, t0, t1)
    else:
        canvas = fn(t, t0, t1)
        STACK.draw(canvas, base, mask, t)
    cap.draw(canvas, t, SPANS, mode, STYLE)
    return canvas.convert("RGB")

def open_sources(t0):
    return Reader(BASE, W, H, t0, fill=False), Reader(MASK, 540, 960, t0, fill=False)

def make_frame(i, srcs):
    t = i / FPS
    b, m = srcs[0].next(), srcs[1].next().convert("L")
    advance(t)
    return compose(t, b, m)

def main():
    n = int((DUR + TAIL) * FPS)
    if "--preview" in sys.argv:   # seek straight to each still (~0.4s per still)
        os.makedirs("previews", exist_ok=True)
        for x in sys.argv[sys.argv.index("--preview") + 1].split(","):
            i = int(round(float(x) * FPS)); t = i / FPS
            for r in readers.values(): r.close()
            readers.clear()
            srcs = open_sources(t)
            im = make_frame(i, srcs)
            for r in srcs: r.close()
            if "--safe" in sys.argv: im = SZ.overlay(im).convert("RGB")
            im.save(f"previews/p_{t:05.2f}.jpg", quality=85)
        return
    # parallel chunks on all cores (~40 fps vs ~3 fps sequential); --workers N to override
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else None
    PR.render(OUT, n, make_frame, open_sources, audio=MIX if os.path.exists(MIX) else None, workers=workers)

if __name__ == "__main__":
    main()
