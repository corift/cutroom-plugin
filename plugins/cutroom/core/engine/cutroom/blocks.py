"""Reusable animation blocks with character (2026-10-09).

Why: v1 of the prompting reel was a run of boxed dark UI cards, and it read as "vibe coded". These
blocks follow what makes Kallaway's graphics read well: one big, physical object per frame, drawn straight
onto a flat canvas (no panel boxes), with real texture (paper, grain, glow, ink) and something moving
about every second.

Every block is a pure function of local time `k` (seconds since the block started), so it is chunk-safe
for parallel.render. Call signature: `block(canvas, k, ...)`. Most blocks take `cx, cy` (centre in canvas
px). Default sizes fill the top ~60% of a 1080x1920 frame, i.e. Kallaway's graphic zone (y 0..1180).

    from cutroom import blocks as B
    cv = B.canvas("paper", i)           # textured background for frame i (dark | paper)
    B.sticky_notes(cv, k, [B.Note("act like an expert", 0.2, 380, 420, -6), ...])

Showcase of every block: templates/blocks_showcase.py -> blocks_showcase.mp4
"""
import math, random, re
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from . import brand
from .core import W, H, FPS, font, serif, SFD, SFT, MONO, clamp, expo, cubic, inout, text_img, wrap, logo

SERIF_IT = brand.font("serif_italic", "/System/Library/Fonts/NewYorkItalic.ttf")
HAND = "/System/Library/Fonts/Noteworthy.ttc"           # index 1 = Bold
MARKER_FELT = "/System/Library/Fonts/MarkerFelt.ttc"

INK = (24, 22, 20)
PAPER_BG = (236, 235, 231)
DARK_BG = (9, 9, 10)
RED = brand.color("accent", (232, 48, 40))
CLAUDE = (217, 119, 87)
GOLD = (246, 196, 66)
PURPLE = (176, 92, 255)
GREEN = (52, 199, 120)
NOTE_COLS = {"yellow": (255, 226, 102), "pink": (255, 160, 190), "blue": (150, 205, 255), "green": (170, 230, 160)}

def sit(size, weight=520):
    return font(SERIF_IT, size, [min(40, max(18, size // 3)), weight, 0])

def hand(size): return font(HAND, size, index=1)

# ------------------------------------------------------------------ motion helpers
def back(x, s=1.4):
    """ease-out with a small overshoot (for slaps / landings only, never for text)."""
    x = clamp(x); x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

def shake(k, t0, amp=14, dur=0.35, freq=31):
    """decaying camera shake offset after an impact at t0 (deterministic)."""
    u = k - t0
    if not 0 <= u < dur: return 0, 0
    a = amp * (1 - u / dur) ** 2
    return a * math.sin(u * freq), a * math.cos(u * freq * 1.3) * 0.6

def ss(fn, w, h, scale=2):
    """supersampled RGBA layer: fn(draw, s) draws at scale s; returns a w x h antialiased image."""
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), scale)
    return big.resize((w, h), Image.LANCZOS)

def drop_shadow(img, blur=18, alpha=110, grow=0):
    blur = max(1, int(blur)); alpha = int(alpha)
    a = img.split()[3]
    if grow: a = a.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    m = Image.new("L", sh.size, 0); m.paste(a, (pad, pad))
    m = m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)
    sh.putalpha(m)
    sh.pad = pad
    return sh

def place(canvas, img, cx, cy, scale=1.0, rot=0.0, a=1.0, shadow=None):
    """paste img centred at (cx, cy) with scale / rotation (deg) / alpha, optional shadow (dx, dy, blur, alpha)."""
    if a <= 0.003 or scale <= 0.01: return
    im = img
    if abs(scale - 1) > 0.002:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if shadow:
        dx, dy, bl, sa = shadow
        sh = drop_shadow(im, bl, int(sa * a))
        canvas.alpha_composite(sh, (int(cx - sh.width / 2 + dx), int(cy - sh.height / 2 + dy)))
    if a < 0.999:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ------------------------------------------------------------------ canvases (flat, textured)
@lru_cache(8)
def _base(theme):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - W / 2) / W, (yy - H * 0.36) / H)
    if theme == "paper":
        col = np.array(PAPER_BG, np.float32); vig = 1 - 0.10 * d ** 1.6
    else:
        col = np.array(DARK_BG, np.float32) + 10 * np.clip(1 - d * 1.6, 0, 1)[..., None]; vig = 1 - 0.25 * d ** 1.4
        return Image.fromarray(np.dstack([np.clip(col * vig[..., None], 0, 255), np.full((H, W), 255, np.float32)]).astype(np.uint8), "RGBA")
    img = np.clip(col[None, None] * vig[..., None], 0, 255)
    return Image.fromarray(np.dstack([img, np.full((H, W), 255, np.float32)]).astype(np.uint8), "RGBA")

@lru_cache(16)
def _grain(theme, n):
    rng = np.random.default_rng(1000 + n)
    amp = 7 if theme == "paper" else 9
    g = rng.normal(0, amp, (H // 2, W // 2)).astype(np.float32)
    g = np.kron(g, np.ones((2, 2), np.float32))
    return g

def canvas(theme="dark", frame=0):
    """flat background with vignette + living film grain (cycles 8 grain plates)."""
    base = np.asarray(_base(theme)).astype(np.float32)
    g = _grain(theme, frame % 8)
    base[..., :3] = np.clip(base[..., :3] + g[..., None], 0, 255)
    return Image.fromarray(base.astype(np.uint8), "RGBA")

def fg(theme): return INK if theme == "paper" else (255, 255, 255)

# ------------------------------------------------------------------ 01 section title
def title(canvas, k, parts, cy=150, size=78, theme="dark", accent=RED, underline=True):
    """Kallaway-style section title: bold sans words + an italic serif accent word, per-word cascade.
    parts = [("Why Templates", False), ("Fail", True)]  (True = accent)."""
    words = []
    for txt, acc in parts:
        for w_ in txt.split():
            f = sit(int(size * 1.08)) if acc else font(SFD("Heavy"), size)
            words.append((w_, acc, f))
    imgs = [text_img(w_, f, fill=(accent if acc else fg(theme))) for w_, acc, f in words]
    gap = size * 0.24
    tot = sum(im.width - 2 * im.pad for im in imgs) + gap * (len(imgs) - 1)
    x = W / 2 - tot / 2
    for i, (im, (w_, acc, f)) in enumerate(zip(imgs, words)):
        p = expo((k - i * 0.08) / 0.5)
        if p > 0:
            asc = f.getmetrics()[0]
            canvas.alpha_composite(_alpha(im, p), (int(x - im.pad), int(cy - asc * 0.78 - im.pad + (1 - p) * 34)))
            if acc and underline:
                u = clamp((k - i * 0.08 - 0.35) / 0.4)
                if u > 0:
                    marker_line(canvas, [(x - 6, cy + size * 0.30), (x + (im.width - 2 * im.pad) + 8, cy + size * 0.24)], u, accent, width=int(size * 0.09), seed=i)
        x += im.width - 2 * im.pad + gap

def _alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a))); return im

# ------------------------------------------------------------------ 02 sticky notes
class Note:
    """one sticky note: text, slap time, centre x/y, rotation, colour, optional peel-off time."""
    def __init__(self, text, t, x, y, rot=0.0, color="yellow", out=None, size=330):
        self.text, self.t, self.x, self.y, self.rot, self.color, self.out, self.size = text, t, x, y, rot, color, out, size

@lru_cache(64)
def note_img(text, color="yellow", size=330):
    c = NOTE_COLS.get(color, color)
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    arr = np.zeros((s, s, 4), np.float32)
    yy, xx = np.mgrid[0:s, 0:s] / s
    shade = 1 - 0.07 * yy - 0.05 * xx                       # light falls off toward the curl
    shade[: int(s * 0.16)] *= 0.93                          # adhesive strip
    rng = np.random.default_rng(abs(hash(text)) % 2 ** 32)
    fib = rng.normal(0, 3.2, (s, s))                        # paper fibre
    for ch in range(3): arr[..., ch] = np.clip(c[ch] * shade + fib, 0, 255)
    arr[..., 3] = 255
    curl = np.clip((xx + yy - 1.72) / 0.28, 0, 1)            # bottom-right corner lifts
    arr[..., :3] *= (1 - 0.18 * curl)[..., None]
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    fs = int(s * 0.15)
    f = hand(fs)
    lines = wrap(text, f, s * 0.80)
    while len(lines) > 4 and fs > 30:
        fs -= 4; f = hand(fs); lines = wrap(text, f, s * 0.80)
    lh = fs * 1.12
    y0 = s * 0.56 - lh * len(lines) / 2
    for i, ln in enumerate(lines):
        d.text((s / 2, y0 + i * lh), ln, font=f, fill=(32, 30, 40), anchor="mt")
    return im

def sticky_notes(canvas, k, notes, theme="paper"):
    """notes slap onto the frame (overshoot + tiny shake) and peel off (lift + fly) at note.out."""
    dx = dy = 0
    for n in notes:
        sx, sy = shake(k, n.t + 0.14, amp=6, dur=0.25); dx += sx; dy += sy
    for n in notes:
        u = k - n.t
        if u < 0: continue
        p = clamp(u / 0.2)
        scale = 1.0 + 0.32 * (1 - back(p, 1.2)) if p < 1 else 1.0
        a = clamp(u / 0.08)
        x, y, rot = n.x + dx, n.y + dy, n.rot
        lift = (1 - clamp(u / 0.2)) * 34
        if n.out is not None and k >= n.out:
            v = (k - n.out) / 0.5
            if v >= 1: continue
            e = cubic(v)
            x += e * 520 * (1 if n.x > W / 2 else -1); y -= e * 380; rot += e * 38 * (1 if n.x > W / 2 else -1)
            a *= 1 - clamp((v - 0.5) / 0.5); lift = 40 * min(1, v * 3)
        place(canvas, note_img(n.text, n.color, n.size), x, y, scale, rot, a,
              shadow=(8 + lift * 0.6, 14 + lift, 12 + lift * 0.3, 120 if theme == "paper" else 200))

# ------------------------------------------------------------------ 03 glow chart
def _catmull(pts, n=24):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n):
            t = j / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in range(2)))
    out.append(pts[-1])
    return out

def _partial(path, p):
    if p >= 1: return path
    L = [0.0]
    for a, b in zip(path, path[1:]): L.append(L[-1] + math.dist(a, b))
    tgt = L[-1] * p; out = [path[0]]
    for i in range(1, len(path)):
        if L[i] <= tgt: out.append(path[i])
        else:
            f = (tgt - L[i - 1]) / max(1e-6, L[i] - L[i - 1])
            out.append((path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f)); break
    return out

def glow_chart(canvas, k, pts, labels=None, box=(110, 300, 970, 900), color=RED, dur=1.6, t0=0.25,
               fill=False, theme="dark", point_times=None):
    """neon line chart that draws on; each point lights up as the line passes it, white label chips pop.
    pts: list of (x, y) in 0..1 (y up). labels: {index: "Rising Action"}. point_times: optional {index: t}
    to light points on cue instead of on the draw."""
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    P = [(x0 + px * w, y1 - py * h) for px, py in pts]
    path = _catmull(P)
    ax = expo(k / 0.5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    axc = fg(theme)
    if ax > 0:
        d.line([(x0, y1), (x0 + w * ax, y1)], fill=axc + (200,), width=4)
        d.line([(x0, y1), (x0, y1 - h * ax)], fill=axc + (200,), width=4)
    p = clamp((k - t0) / dur)
    p = inout(p) if p < 1 else 1
    part = _partial(path, p)
    if fill and len(part) > 2:
        poly = part + [(part[-1][0], y1), (part[0][0], y1)]
        fl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(fl).polygon(poly, fill=color + (255,))
        grad = Image.linear_gradient("L").resize((W, h)).point(lambda v: int(v * 0.0 + (255 - v) * 0.45))
        m = Image.new("L", (W, H), 0); m.paste(grad, (0, y0))
        fa = np.minimum(np.asarray(fl.split()[3]), np.asarray(m)); fl.putalpha(Image.fromarray(fa))
        canvas.alpha_composite(fl)
    if len(part) > 1:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.line(part, fill=color + (255,), width=18, joint="curve")
        glow = glow.filter(ImageFilter.GaussianBlur(16))
        canvas.alpha_composite(glow); canvas.alpha_composite(glow)
        line = ss(lambda dd, s: dd.line([(x * s, y * s) for x, y in part], fill=color + (255,), width=7 * s, joint="curve"), W, H)
        canvas.alpha_composite(line)
        core = ss(lambda dd, s: dd.line([(x * s, y * s) for x, y in part], fill=(255, 235, 235, 200), width=2 * s, joint="curve"), W, H)
        canvas.alpha_composite(core)
    canvas.alpha_composite(lay)
    # points light up when the line reaches them
    seg = 24
    for i, (px, py) in enumerate(P):
        reach = (t0 + dur * _inv_inout(i * seg / max(1, len(path) - 1))) if point_times is None else point_times.get(i, 99)
        u = k - reach
        if u < 0: continue
        r = 12 + 10 * (1 - expo(u / 0.35))
        place(canvas, _dot(color), px, py, 1.0 + 0.6 * (1 - expo(u / 0.3)), 0, 1.0)
        if 0 < u < 0.6:
            rr = 14 + 60 * expo(u / 0.6)
            ImageDraw.Draw(canvas).ellipse((px - rr, py - rr, px + rr, py + rr), outline=color + (int(220 * (1 - u / 0.6)),), width=3)
        if labels and i in labels:
            lab = _chip(labels[i])
            e = expo((u - 0.05) / 0.4)
            lx = min(max(px, 70 + lab.width / 2), 1010 - lab.width / 2)
            place(canvas, lab, lx, py - 58 - (1 - e) * 20, 1.0, 0, e,
                  shadow=(0, 6, 10, 120))

def _inv_inout(y):
    y = clamp(y)
    return (y / 4) ** (1 / 3) if y < 0.5 else 1 - ((2 - 2 * y) ** (1 / 3)) / 2

@lru_cache(16)
def _dot(color):
    s = 80
    yy, xx = np.mgrid[0:s, 0:s]; r = np.hypot(xx - s / 2, yy - s / 2)
    glow = np.clip(1 - r / (s / 2), 0, 1) ** 2.2 * 200
    core = np.clip(11 - r, 0, 1) * 255
    c = np.array(color, float)
    mix = (np.clip(7 - r, 0, 1))[..., None]
    rgb = c * (1 - mix) + 255 * mix
    return Image.fromarray(np.dstack([rgb, np.maximum(glow, core)]).clip(0, 255).astype(np.uint8), "RGBA")

@lru_cache(64)
def _chip(txt, size=30, bg=(255, 255, 255), fgc=INK):
    f = font(SFT("Bold"), size)
    w_ = int(f.getlength(txt)) + 34; h_ = int(size * 1.7)
    def dr(d, s):
        d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), 10 * s, fill=bg + (255,), outline=(0, 0, 0, 255), width=2 * s)
    im = ss(dr, w_, h_)
    ImageDraw.Draw(im).text((w_ / 2, h_ / 2), txt, font=f, fill=fgc, anchor="mm")
    return im

# ------------------------------------------------------------------ 04 big number
def big_number(canvas, k, a, b, prefix="", suffix="", label=None, cx=540, cy=560, size=330, color=None,
               theme="dark", dur=0.9, glow=CLAUDE):
    """huge count-up (a -> b) with a coloured bloom and a settle; optional serif italic label under it."""
    p = expo(k / dur)
    v = a + (b - a) * p
    txt = f"{prefix}{int(round(v)):,}{suffix}" if float(b).is_integer() else f"{prefix}{v:.1f}{suffix}"
    col = color or fg(theme)
    f = font(SFD("Black"), size)
    im = text_img(txt, f, fill=col)
    sc = 1.0 + 0.10 * (1 - expo(k / 0.5))
    a_ = clamp(k / 0.12)
    if glow:
        gl = text_img(txt, f, fill=glow)
        gl = gl.resize((int(gl.width * 1.0), gl.height)).filter(ImageFilter.GaussianBlur(28))
        pulse = 0.55 + 0.45 * math.exp(-max(0, k - dur) * 2.5) if k > dur else 0.55 + 0.45 * p
        place(canvas, gl, cx, cy, sc, 0, a_ * pulse)
    place(canvas, im, cx, cy, sc, 0, a_)
    if label:
        e = expo((k - dur * 0.6) / 0.5)
        lab = text_img(label, sit(int(size * 0.2)), fill=(fg(theme)))
        place(canvas, lab, cx, cy + size * 0.62 + (1 - e) * 24, 1, 0, e)

def number_morph(canvas, k, a_txt, b_txt, label_a="", label_b="", cx=540, cy=560, size=280, theme="dark", t_switch=0.9,
                 color_b=None, dur=0.5):
    """'600 words' rolls up and out like an odometer while '3 sentences' rolls in from below, inside a
    feathered band (no strike-through). The new value lands with a small settle."""
    col = fg(theme); f = font(SFD("Black"), size)
    A = text_img(a_txt, f, fill=col); Bm = text_img(b_txt, f, fill=color_b or col)
    band = int(size * 1.3)
    ea = expo(k / 0.45)
    u = inout(clamp((k - t_switch) / dur))
    lay = Image.new("RGBA", (W, band), (0, 0, 0, 0))
    if u < 1: place(lay, A, cx, band / 2 + (1 - ea) * band * 0.7 - u * band, 1, 0, ea)
    if u > 0:
        land = clamp((k - t_switch - dur) / 0.35)
        place(lay, Bm, cx, band / 2 + (1 - u) * band, 1 + 0.05 * math.sin(land * math.pi) * (land < 1), 0, 1)
    a = np.asarray(lay).copy()
    edge = np.clip(np.minimum(np.arange(band), band - 1 - np.arange(band)) / (band * 0.18), 0, 1)
    a[..., 3] = (a[..., 3] * edge[:, None]).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(a, "RGBA"), (0, int(cy - band / 2)))
    ly = cy + size * 0.62
    if label_a and u < 1:
        place(canvas, text_img(label_a, sit(int(size * 0.2)), fill=col), cx, ly - u * 40, 1, 0, ea * (1 - u))
    if label_b and u > 0:
        place(canvas, text_img(label_b, sit(int(size * 0.2)), fill=col), cx, ly + (1 - u) * 40, 1, 0, u)

# ------------------------------------------------------------------ 05 cutout photo
@lru_cache(8)
def _sticker(path, size, border, shape):
    src = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    src = ImageOps.fit(src, (size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0); dm = ImageDraw.Draw(m)
    if shape == "circle": dm.ellipse((0, 0, size - 1, size - 1), fill=255)
    else: dm.rounded_rectangle((0, 0, size - 1, size - 1), int(size * 0.06), fill=255)
    src.putalpha(m)
    S = size + border * 2
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    def dr(d, s):
        if shape == "circle": d.ellipse((0, 0, S * s - 1, S * s - 1), fill=(255, 255, 255, 255))
        else: d.rounded_rectangle((0, 0, S * s - 1, S * s - 1), int((size * 0.06 + border) * s), fill=(255, 255, 255, 255))
    out.alpha_composite(ss(dr, S, S)); out.alpha_composite(src, (border, border))
    return out

@lru_cache(16)
def _nametag(name, sub, theme):
    fN = font(SFD("Heavy"), 54); fS = font(SFT("Semibold"), 30)
    w_ = int(max(fN.getlength(name), fS.getlength(sub))) + 70; h_ = 140
    def dr(d, s): d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), 22 * s, fill=(255, 255, 255, 255))
    im = ss(dr, w_, h_); d = ImageDraw.Draw(im)
    d.text((35, 26), name, font=fN, fill=INK)
    d.text((35, 90), sub, font=fS, fill=(120, 118, 112))
    return im

def cutout(canvas, k, path, name=None, sub="", cx=540, cy=520, size=520, shape="circle", theme="dark",
           rot=-4, logo_path=None):
    """photo as a die-cut sticker (white border, real shadow) that drops in rotating; a name tag slaps on
    after, optional logo badge pops on the corner."""
    st = _sticker(path, size, max(10, size // 26), shape)
    p = clamp(k / 0.45)
    e = back(p, 1.0)
    place(canvas, st, cx, cy + (1 - e) * 260, 0.85 + 0.15 * e, rot - 10 * (1 - e) + 1.2 * math.sin(k * 1.4), clamp(k / 0.15),
          shadow=(10, 22, 22, 150 if theme == "paper" else 230))
    if name:
        u = k - 0.45
        if u > 0:
            q = clamp(u / 0.2)
            tag = _nametag(name, sub, theme)
            place(canvas, tag, cx + size * 0.18, cy + size * 0.52, 1 + 0.3 * (1 - back(q, 1.2)), 4, clamp(u / 0.08),
                  shadow=(6, 12, 12, 140))
    if logo_path:
        u = k - 0.75
        if u > 0:
            q = clamp(u / 0.25)
            badge = _badge(logo_path)
            place(canvas, badge, cx + size * 0.38, cy - size * 0.36, back(q, 1.6), 8, clamp(u / 0.1), shadow=(4, 10, 10, 140))

@lru_cache(8)
def _badge(logo_path, s=150):
    def dr(d, sc): d.ellipse((0, 0, s * sc - 1, s * sc - 1), fill=(255, 255, 255, 255))
    im = ss(dr, s, s)
    lg = logo(logo_path, int(s * 0.62))
    im.alpha_composite(lg, ((s - lg.width) // 2, (s - lg.height) // 2))
    return im

# ------------------------------------------------------------------ 06 phone
@lru_cache(4)
def _phone_frame(w=520, h=1060):
    def dr(d, s):
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), 78 * s, fill=(18, 18, 20, 255))
        d.rounded_rectangle((3 * s, 3 * s, (w - 3) * s, (h - 3) * s), 76 * s, outline=(70, 70, 78, 255), width=3 * s)
        d.rounded_rectangle((-4 * s, 230 * s, 0, 320 * s), 3 * s, fill=(40, 40, 46, 255))
        d.rounded_rectangle((w * s, 260 * s, (w + 4) * s, 380 * s), 3 * s, fill=(40, 40, 46, 255))
    return ss(dr, w, h)

@lru_cache(4)
def _phone_shot(path, sw):
    im = Image.open(path).convert("RGBA")
    return im.resize((sw, int(im.height * sw / im.width)), Image.LANCZOS)

def phone(canvas, k, shot, cx=540, cy=600, scale=1.0, scroll=(0.7, 3.2), rot=3.0, theme="dark"):
    """phone rises in with a slight tilt; its screen scrolls the screenshot (a tall capture works best)."""
    w, h, bez = 520, 1060, 16
    sw, sh = w - bez * 2, h - bez * 2
    scr = _phone_shot(shot, sw)
    s0, s1 = scroll
    u = inout(clamp((k - s0) / (s1 - s0)))
    off = int(u * max(0, scr.height - sh))
    body = _phone_frame(w, h).copy()
    view = scr.crop((0, off, sw, off + sh)) if scr.height >= sh else ImageOps.pad(scr, (sw, sh), color=(255, 255, 255))
    m = Image.new("L", (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), 62, fill=255)
    view = view.copy(); view.putalpha(m)
    body.alpha_composite(view, (bez, bez))
    di = ss(lambda d, s: d.rounded_rectangle((0, 0, 150 * s, 42 * s), 21 * s, fill=(0, 0, 0, 255)), 151, 43)
    body.alpha_composite(di, ((w - 151) // 2, bez + 18))
    glare = Image.linear_gradient("L").rotate(-35, expand=False).resize((w, h)).point(lambda v: int(max(0, v - 170) * 0.35))
    gl = Image.new("RGBA", (w, h), (255, 255, 255, 0)); gl.putalpha(Image.fromarray(np.minimum(np.asarray(glare), np.asarray(body.split()[3]))))
    body.alpha_composite(gl)
    p = clamp(k / 0.6)
    e = expo(p)
    place(canvas, body, cx, cy + (1 - e) * 700, scale * (0.96 + 0.04 * e), rot * e + (1 - e) * 12 + 0.8 * math.sin(k * 1.1),
          clamp(k / 0.2), shadow=(14, 34, 30, 170 if theme == "paper" else 255))

# ------------------------------------------------------------------ 07 marker (hand-drawn)
def _wobble(pts, seed, amp=3.0):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]
    out = []
    for i, (x, y) in enumerate(pts):
        u = i / max(1, len(pts) - 1)
        out.append((x + amp * math.sin(u * 7 + ph[0]) + amp * 0.5 * math.sin(u * 19 + ph[1]),
                    y + amp * math.cos(u * 6 + ph[2])))
    return out

def marker_line(canvas, pts, p, color=RED, width=12, seed=0, n=40):
    """hand-drawn marker stroke along a polyline (2+ points, curved through them), drawn to progress p."""
    if p <= 0: return
    path = _catmull(list(pts), n) if len(pts) > 2 else [(pts[0][0] + (pts[1][0] - pts[0][0]) * i / n,
                                                          pts[0][1] + (pts[1][1] - pts[0][1]) * i / n) for i in range(n + 1)]
    path = _partial(_wobble(path, seed, amp=width * 0.18), expo(p) if p < 1 else 1)
    xs = [x for x, _ in path]; ys = [y for _, y in path]
    pad = width * 2
    bx0, by0 = int(min(xs) - pad), int(min(ys) - pad)
    bw, bh = int(max(xs) - bx0 + pad), int(max(ys) - by0 + pad)
    def dr(d, s):
        q = [((x - bx0) * s, (y - by0) * s) for x, y in path]
        d.line(q, fill=color + (235,), width=int(width * s), joint="curve")
        r = width * s / 2
        for x, y in (q[0], q[-1]): d.ellipse((x - r, y - r, x + r, y + r), fill=color + (235,))
    canvas.alpha_composite(ss(dr, bw, bh), (bx0, by0))

def marker_circle(canvas, k, box, color=RED, width=10, dur=0.5, seed=1):
    """hand-drawn loop that hugs a text box (x0, y0, x1, y1) -- use text_box() for the exact words. One turn
    plus a short overlap, padding scales with the text height so it never runs off the words."""
    x0, y0, x1, y1 = box; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hh = y1 - y0
    rx, ry = (x1 - x0) / 2 + hh * 0.22, hh / 2 + hh * 0.32
    sq = lambda v: math.copysign(abs(v) ** (2 / 3.2), v)      # superellipse: hugs the box corners
    rnd = random.Random(seed); tilt = math.radians(rnd.uniform(-2, 2))
    pts = []
    for i in range(73):
        a = math.radians(200) + i / 72 * math.tau * 1.07
        r = 1 + 0.02 * math.sin(a * 2 + seed)
        x, y = rx * r * sq(math.cos(a)), ry * r * sq(math.sin(a))
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
    marker_line(canvas, pts[::3], clamp(k / dur), color, width, seed, n=8)

def text_box(f, text, x, y, anchor="la"):
    """exact ink box of `text` drawn at (x, y) with Pillow anchor -- feed it to marker_circle / marker_line."""
    return ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((x, y), text, font=f, anchor=anchor)

def marker_arrow(canvas, k, a, b, color=RED, width=11, dur=0.45, bend=0.25, seed=2):
    """curved hand-drawn arrow from a to b, head drawn after the shaft."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = -(b[1] - a[1]) * bend, (b[0] - a[0]) * bend
    pts = [a, (mx + nx, my + ny), b]
    marker_line(canvas, pts, clamp(k / dur), color, width, seed)
    hp = clamp((k - dur) / 0.18)
    if hp > 0:
        ang = math.atan2(b[1] - (my + ny), b[0] - (mx + nx))
        for s in (+1, -1):
            e = (b[0] - 46 * math.cos(ang + s * 0.55), b[1] - 46 * math.sin(ang + s * 0.55))
            marker_line(canvas, [b, e], hp, color, width, seed + s)

# ------------------------------------------------------------------ 08 logo burst
def logo_burst(canvas, k, logo_path, cx=540, cy=520, size=330, color=CLAUDE):
    """logo rises and turns into place on a soft bloom that breathes; no rays / rings."""
    e = expo(k / 0.7)
    breathe = 1 + 0.04 * math.sin(k * 2.2)
    place(canvas, _bloom(color, int(size * 2.8)), cx, cy, (0.7 + 0.3 * e) * breathe, 0, 0.85 * e)
    lg = logo(logo_path, size)
    place(canvas, lg, cx, cy + (1 - e) * 60 + 6 * math.sin(k * 1.6), 0.82 + 0.18 * e, -40 * (1 - e), clamp(k / 0.25))

@lru_cache(8)
def _bloom(color, s):
    yy, xx = np.mgrid[0:s, 0:s]; r = np.hypot(xx - s / 2, yy - s / 2) / (s / 2)
    a = np.clip(1 - r, 0, 1) ** 2.6 * 150
    return Image.fromarray(np.dstack([np.full((s, s), c, np.float32) for c in color] + [a]).astype(np.uint8), "RGBA")

# ------------------------------------------------------------------ 10 document + shred
@lru_cache(4)
def doc_img(lines, w=760, title="my_prompt.txt", size=27):
    """real-text paper document (no grey placeholder bars). lines = tuple of strings; '#' prefix = heading."""
    fB, fR, fT = font(SFT("Bold"), size), font(SFT("Regular"), size), font(SFT("Semibold"), 22)
    rows = []
    for ln in lines:
        if ln.startswith("#"): rows.append(("h", ln[1:].strip()))
        else:
            for r in wrap(ln, fR, w - 110): rows.append(("p", r))
    lh = int(size * 1.55)
    h_ = 110 + lh * len(rows) + 60
    im = Image.new("RGBA", (w, h_), (253, 252, 249, 255)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 70), fill=(242, 240, 235, 255))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]): d.ellipse((26 + i * 30, 26, 44 + i * 30, 44), fill=c)
    d.text((w / 2, 35), title, font=fT, fill=(110, 108, 102), anchor="mm")
    y = 104
    for kind, txt in rows:
        if kind == "h": y += 10; d.text((55, y), txt.upper(), font=fB, fill=(200, 60, 40)); y += lh
        else: d.text((55, y), txt, font=fR, fill=(52, 50, 46)); y += lh
    return im

def scroll_doc(canvas, k, lines, cx=540, top=250, view_h=820, speed=260, w=760, theme="paper", t0=0.0):
    """endless-feeling prompt doc scrolling up inside a fixed window (fades at the edges)."""
    doc = doc_img(tuple(lines), w)
    off = int(max(0, k - t0) * speed) % max(1, doc.height - view_h) if doc.height > view_h else 0
    view = doc.crop((0, off, w, off + view_h))
    m = Image.new("L", (w, view_h), 255); md = ImageDraw.Draw(m)
    for i in range(90): md.line([(0, view_h - 1 - i), (w, view_h - 1 - i)], fill=int(255 * i / 90))
    view.putalpha(m)
    place(canvas, view, cx, top + view_h / 2 + (1 - expo(k / 0.5)) * 120, 1, -1.5, clamp(k / 0.2), shadow=(0, 20, 26, 120))

@lru_cache(256)
def _row(kind, txt, size, w):
    f = font(SFT("Bold" if kind == "h" else "Regular"), size)
    lh = int(size * 1.55)
    im = Image.new("RGBA", (w, lh), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((55, int(size * 0.2)), txt.upper() if kind == "h" else txt, font=f,
                            fill=(200, 60, 40) if kind == "h" else (52, 50, 46))
    return im, int(f.getlength(txt.upper() if kind == "h" else txt))

def delete_lines(canvas, k, lines, keep, cx=540, top=260, w=760, size=26, t_sel=0.3, t_del=1.3, title_txt="my_prompt.txt",
                 theme="paper"):
    """a real 'select -> delete' edit on the prompt doc: every line except `keep` (indices into `lines`) gets a
    blue text selection that runs down the doc, then those lines collapse out and the doc shrinks around
    what is left. The 'delete most of your prompt' move."""
    fR = font(SFT("Regular"), size)
    rows = []
    for li, ln in enumerate(lines):
        if ln.startswith("#"): rows.append(("h", ln[1:].strip(), li))
        else:
            for r in wrap(ln, fR, w - 110): rows.append(("p", r, li))
    lh = int(size * 1.55)
    n_del = sum(1 for r in rows if r[2] not in keep)
    hs, sels = [], []
    j = 0
    for kind, txt, li in rows:
        if li in keep: hs.append(1.0); sels.append(0.0); continue
        sel = clamp((k - t_sel - j * 0.035) / 0.12)
        col = inout(clamp((k - t_del - j * 0.012) / 0.5))
        hs.append(1 - col); sels.append(sel); j += 1
    body = int(sum(h_ * lh for h_ in hs))
    H_ = 104 + body + 50
    doc = Image.new("RGBA", (w, H_), (253, 252, 249, 255)); d = ImageDraw.Draw(doc)
    d.rectangle((0, 0, w, 70), fill=(242, 240, 235, 255))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]): d.ellipse((26 + i * 30, 26, 44 + i * 30, 44), fill=c)
    d.text((w / 2, 35), title_txt, font=font(SFT("Semibold"), 22), fill=(110, 108, 102), anchor="mm")
    y = 100.0
    for (kind, txt, li), h_, sel in zip(rows, hs, sels):
        rh = h_ * lh
        if rh > 0.5:
            im, tw = _row(kind, txt, size, w)
            fa = clamp(1 - (1 - h_) * 3)
            if sel > 0 and rh > 8 and fa > 0:
                bc = tuple(int(253 + (c - 253) * fa) for c in (178, 212, 255))
                d.rectangle((50, int(y + 2), int(50 + (tw + 10) * sel), int(y + min(rh, lh) - 4)), fill=bc + (255,))
            if h_ < 1:
                im = _alpha(im.crop((0, 0, w, max(1, int(rh)))), clamp(1 - (1 - h_) * 3))
            doc.alpha_composite(im, (0, int(y)))
        y += rh
    m = Image.new("L", doc.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, H_ - 1), 18, fill=255)
    doc.putalpha(m)
    e = expo(k / 0.5)
    place(canvas, doc, cx, top + H_ / 2 + (1 - e) * 120, 1, -1.0, clamp(k / 0.2), shadow=(0, 20, 26, 120))

# ------------------------------------------------------------------ 11 heavy thud (paper stack / binder)
@lru_cache(4)
def paper_stack(label="HOW TO THINK", sub="a 3-page script", w=560, h=700, sheets=7):
    S = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    def dr(d, s):
        for i in range(sheets, 0, -1):
            o = i * 7
            d.rectangle(((o) * s, (60 - o) * s, (w + o) * s, (h + 60 - o) * s), fill=(250 - i * 3, 248 - i * 3, 242 - i * 3, 255),
                        outline=(205, 200, 190, 255), width=2 * s)
        d.rectangle((0, 60 * s, w * s, (h + 60) * s), fill=(253, 252, 248, 255), outline=(190, 185, 175, 255), width=2 * s)
        d.rectangle((0, 60 * s, 34 * s, (h + 60) * s), fill=(214, 62, 50, 255))
        for j in range(3): d.ellipse((8 * s, (180 + j * 200) * s, 26 * s, (198 + j * 200) * s), fill=(60, 20, 18, 255))
    S.alpha_composite(ss(dr, w + 60, h + 60))
    d = ImageDraw.Draw(S)
    f1 = font(SFD("Black"), 64); f2 = sit(42); f3 = font(SFT("Regular"), 22)
    d.text((w / 2 + 17, 230), label, font=f1, fill=INK, anchor="mm")
    d.text((w / 2 + 17, 300), sub, font=f2, fill=(110, 105, 98), anchor="mm")
    for j in range(9):
        d.text((80, 390 + j * 34), ["1. Always think before you…", "2. Never answer without…", "3. Consider every angle…",
                                     "4. Use exactly three…", "5. Do not use bullet…", "6. Step back and re-read…",
                                     "7. Act like an expert in…", "8. If unsure, think step…", "9. Always cite…"][j],
               font=f3, fill=(120, 116, 108))
    d.text((w - 30, h + 20), "p. 1 / 3", font=f3, fill=(150, 145, 136), anchor="rm")
    return S

def thud(canvas, k, img=None, cx=540, cy=600, t_land=0.32, theme="paper"):
    """a heavy object falls in (ease-in), lands with squash + camera shake + a dust puff."""
    img = img or paper_stack()
    if k < t_land:
        p = clamp(k / t_land) ** 2
        place(canvas, img, cx, cy - (1 - p) * 1100, 1.06, -6 * (1 - p), 1.0, shadow=(0, 60 * (1 - p) + 20, 30, int(150 * p)))
        return
    u = k - t_land
    sq = math.exp(-u * 10) * math.cos(u * 30)
    dx, dy = shake(k, t_land, amp=20, dur=0.4)
    im = img.resize((int(img.width * (1 + 0.05 * sq)), int(img.height * (1 - 0.06 * sq))), Image.BICUBIC)
    place(canvas, im, cx + dx, cy + dy + img.height * 0.03 * sq, 1, 0, 1.0, shadow=(0, 22, 18, 160))
    if u < 0.9:
        rnd = random.Random(11)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        base = cy + img.height / 2 + 10
        dust = (150, 140, 128) if theme == "paper" else (200, 200, 200)
        for i in range(40):
            side = -1 if i % 2 else 1
            sp = rnd.uniform(160, 520); r = rnd.uniform(6, 22) * (1 + u * 1.5)
            x = cx + side * (img.width * 0.42 + sp * expo(u / 0.9) * 0.9)
            y = base - rnd.uniform(0, 70) * expo(u / 0.6) - 30 * u
            al = int(120 * (1 - u / 0.9))
            d.ellipse((x - r, y - r, x + r, y + r), fill=dust + (al,))
        canvas.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5)))

# ------------------------------------------------------------------ 12 glowing numbered list
@lru_cache(16)
def num_tile(n, color=GOLD, s=124):
    """rounded square with a soft vertical gradient and a heavy white numeral."""
    def dr(d, sc):
        S = s * sc
        for yy in range(int(S)):
            u = yy / S
            c = tuple(int(color[i] * (1.08 - 0.28 * u)) for i in range(3))
            d.line([(0, yy), (S, yy)], fill=tuple(min(255, v) for v in c) + (255,))
    grad = ss(dr, s, s)
    m = Image.new("L", (s * 2, s * 2), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, s * 2 - 1, s * 2 - 1), int(s * 0.56), fill=255)
    grad.putalpha(m.resize((s, s), Image.LANCZOS))
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle((3, 3, s - 4, s - 4), int(s * 0.27), outline=(255, 255, 255, 90), width=2)
    grad.alpha_composite(hl)
    ImageDraw.Draw(grad).text((s / 2, s / 2 + 2), str(n), font=font(SFD("Heavy"), int(s * 0.56)), fill=(255, 255, 255), anchor="mm")
    return grad

def glow_list(canvas, k, items, x=150, y0=330, gap=200, color=GOLD, theme="dark", times=None, dim=True):
    """numbered tiles pop in one by one with their line; earlier lines dim (focus on the newest).
    times: list of start times per item (word-cued); default every 0.9s."""
    times = times or [i * 0.9 for i in range(len(items))]
    f = font(SFD("Bold"), 54)
    cur = max([i for i, t in enumerate(times) if k >= t], default=-1)
    for i, (txt, t) in enumerate(zip(items, times)):
        u = k - t
        if u < 0: continue
        y = y0 + i * gap
        a = 1.0 if (not dim or i == cur) else 0.4
        place(canvas, _bloom(color, 280), x, y, 1, 0, (0.55 if i == cur else 0.15) * expo(u / 0.4))
        place(canvas, num_tile(i + 1, color), x, y, 0.6 + 0.4 * back(clamp(u / 0.3), 1.2), 0, a * clamp(u / 0.1))
        lines = wrap(txt, f, W - x - 170)
        for j, ln in enumerate(lines):
            e = expo((u - 0.1 - j * 0.06) / 0.45)
            im = text_img(ln, f, fill=fg(theme))
            canvas.alpha_composite(_alpha(im, e * a), (int(x + 100 - im.pad + (1 - e) * 40), int(y - 36 - im.pad + j * 62 - (len(lines) - 1) * 31)))

# ------------------------------------------------------------------ 13 person quote card
@lru_cache(8)
def _avatar(path, s):
    im = ImageOps.fit(ImageOps.exif_transpose(Image.open(path)).convert("RGBA"), (s * 2, s * 2), Image.LANCZOS)
    m = Image.new("L", (s * 2, s * 2), 0); ImageDraw.Draw(m).ellipse((0, 0, s * 2 - 1, s * 2 - 1), fill=255)
    im.putalpha(m); return im.resize((s, s), Image.LANCZOS)

def person_quote(canvas, k, avatar, name, sub, quote, logo_path=None, mark=None, t_quote=0.5, t_mark=None,
                 cx=540, cy=560, w=960, size=56):
    """dark card: round avatar + big bold name + small logo/role line, a divider that draws, then the quote in
    serif types on; optional yellow marker on one phrase (`mark`) at t_mark."""
    fN = font(SFD("Bold"), 64); fS = font(SFT("Medium"), 34); fQ = serif(size, 520)
    qlines = wrap(quote, fQ, w - 120)
    lh = int(size * 1.32)
    h_ = 300 + lh * len(qlines) + 60
    e = expo(k / 0.5)
    card = Image.new("RGBA", (w, h_), (0, 0, 0, 0))
    def dr(d, s): d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 34 * s, fill=(8, 8, 9, 255), outline=(255, 255, 255, 90), width=2 * s)
    card.alpha_composite(ss(dr, w, h_))
    d = ImageDraw.Draw(card)
    av = _avatar(avatar, 150)
    pa = clamp(k / 0.35)
    if pa > 0: place(card, av, 60 + 75, 50 + 75, 0.7 + 0.3 * back(pa, 1.3), 0, clamp(k / 0.12))
    nk = expo((k - 0.12) / 0.45)
    nm = text_img(name, fN, fill=(255, 255, 255))
    card.alpha_composite(_alpha(nm, nk), (240 - nm.pad, int(62 - nm.pad + (1 - nk) * 24)))
    sk = expo((k - 0.24) / 0.45)
    if sk > 0:
        x = 242
        if logo_path:
            lg = logo(logo_path, 40); card.alpha_composite(_alpha(lg, sk), (x, int(150 + (1 - sk) * 20))); x += 54
        sb = text_img(sub, fS, fill=(190, 186, 180))
        card.alpha_composite(_alpha(sb, sk), (x - sb.pad, int(150 - sb.pad + (1 - sk) * 20)))
    dl = expo((k - 0.3) / 0.6)
    if dl > 0: d.line((60, 245, 60 + (w - 120) * dl, 245), fill=(255, 255, 255, 50), width=2)
    n = int(len(quote) * clamp((k - t_quote) / max(0.6, len(quote) / 38)))
    left = n; y = 285
    mp = expo((k - t_mark) / 0.6) if (mark and t_mark is not None and k > t_mark) else 0
    for ln in qlines:
        part = ln[:max(0, left)]; left -= len(ln) + 1
        if mark and mark in ln and mp > 0 and len(part) >= ln.index(mark) + len(mark):
            x0 = 60 + fQ.getlength(ln[:ln.index(mark)]); ww = fQ.getlength(mark)
            d.rectangle((x0 - 6, y + size * 0.12, x0 + (ww + 12) * mp - 6, y + size * 1.12), fill=(255, 214, 10, 255))
            d.text((60, y), part, font=fQ, fill=(255, 255, 255))
            d.text((x0, y), mark, font=fQ, fill=INK)
        else:
            d.text((60, y), part, font=fQ, fill=(255, 255, 255))
        y += lh
    place(canvas, card, cx, cy + (1 - e) * 60, 1, 0, clamp(k / 0.25), shadow=(0, 24, 30, 200))

# ------------------------------------------------------------------ 14 X post + highlighter
def post(canvas, k, avatar, name, handle, text, marks=(), meta="", stats="", cx=540, cy=560, w=980, size=44, dim=True):
    """an X post, verbatim: avatar, name + verified tick, handle · date, body text; marks=[(phrase, t_on)]
    sweep a yellow highlighter word by word (marked words flip to ink, the rest dims once a mark is on);
    optional stats line ('1.3M views'). The 'he even said X' receipt."""
    fT = font(SFT("Regular"), size); sp = fT.getlength(" "); lh = int(size * 1.36)
    lay, x, y = [], 0, 0
    for wd in text.split(" "):
        wl = fT.getlength(wd)
        if x > 0 and x + wl > w - 110: x = 0; y += lh
        lay.append([wd, x, y, wl]); x += wl + sp
    th = y + lh
    h_ = 190 + th + (90 if stats else 40)
    card = Image.new("RGBA", (w, h_), (0, 0, 0, 0))
    def dr(d, s): d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 30 * s, fill=(0, 0, 0, 255), outline=(255, 255, 255, 70), width=2 * s)
    card.alpha_composite(ss(dr, w, h_)); d = ImageDraw.Draw(card)
    card.alpha_composite(_avatar(avatar, 100), (50, 46))
    fN = font(SFT("Bold"), 40); d.text((172, 70), name, font=fN, fill=(255, 255, 255), anchor="lm")
    bx = 172 + fN.getlength(name) + 26
    tick = ss(lambda dd, s: dd.ellipse((0, 0, 34 * s, 34 * s), fill=(29, 155, 240, 255)), 35, 35)
    ImageDraw.Draw(tick).line([(9, 18), (15, 24), (26, 11)], fill=(255, 255, 255), width=4)
    card.alpha_composite(tick, (int(bx - 17), 53))
    d.text((172, 118), handle + (f" · {meta}" if meta else ""), font=font(SFT("Regular"), 32), fill=(113, 118, 123), anchor="lm")
    norm = [re.sub(r"[^a-z0-9]", "", x[0].lower()) for x in lay]
    state = [0.0] * len(lay); act = 0.0
    for phrase, ton in marks:
        ph = [re.sub(r"[^a-z0-9]", "", x.lower()) for x in phrase.split()]
        s0 = next(i for i in range(len(norm)) if norm[i:i + len(ph)] == ph)
        pr = expo((k - ton) / 0.7) if k > ton else 0; act = max(act, pr)
        tot = sum(lay[s0 + j][3] for j in range(len(ph))); c = 0
        for j in range(len(ph)):
            wl = lay[s0 + j][3]; state[s0 + j] = clamp((pr * tot - c) / wl); c += wl
    mx, my = 50, 180
    for (wd, x, y, wl), v in zip(lay, state):
        if v > 0: d.rectangle((mx + x - 5, my + y + 4, mx + x + (wl + (sp if v >= 1 else 0)) * v + 3, my + y + size * 1.2), fill=(255, 214, 10, 255))
    for (wd, x, y, wl), v in zip(lay, state):
        g = int(231 - (231 - 110) * act * 0.75) if dim else 231
        d.text((mx + x, my + y), wd, font=fT, fill=INK if v > 0.5 else (g, g + 2, g + 4))
    if stats: d.text((50, h_ - 50), stats, font=font(SFT("Regular"), 30), fill=(113, 118, 123), anchor="lm")
    e = expo(k / 0.5)
    place(canvas, card, cx, cy + (1 - e) * 60, 0.97 + 0.03 * e, 0, clamp(k / 0.25), shadow=(0, 24, 30, 200))

# ------------------------------------------------------------------ face inset with head pop-out (Kallaway)
def face_inset(canvas, frame, mask=None, box=(60, 1300, 1020, 1920), src_y=690, radius=38, pop=300, theme="dark"):
    """the face as a rounded inset sitting flush on the bottom of the frame (only the top corners round). With a
    person mask (personmask.swift output, any size) the head breaks out over the inset's top edge, like Kallaway's
    hat. src_y = source row that lands on the inset's top edge (pick it so ~150 px of head sits above the edge)."""
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    flush = y1 >= canvas.height
    s = w / frame.width
    big = frame.convert("RGBA").resize((w, int(frame.height * s)), Image.BICUBIC)
    top = int(src_y * s)
    hh = min(h + (radius if flush else 0), big.height - top)
    inner = rounded_rect(big.crop((0, top, w, top + hh)), radius)
    if flush: inner = inner.crop((0, 0, w, min(h, inner.height)))
    sh = drop_shadow(inner, 18, 120 if theme == "paper" else 200)
    sx, sy = x0 - sh.pad, y0 - sh.pad + 14
    canvas.alpha_composite(sh.crop((0, 0, sh.width, max(1, canvas.height - sy))), (sx, sy))
    canvas.alpha_composite(inner, (x0, y0))
    if mask is not None and pop:
        m = mask.convert("L").resize(big.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
        a = max(0, top - pop)
        if top > a:
            head = big.crop((0, a, w, top)); head.putalpha(m.crop((0, a, w, top)))
            canvas.alpha_composite(head, (x0, y0 - (top - a)))

def rounded_rect(img, r):
    m = Image.new("L", (img.width * 2, img.height * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width * 2 - 1, img.height * 2 - 1), r * 2, fill=255)
    out = img.convert("RGBA"); out.putalpha(m.resize(img.size, Image.LANCZOS)); return out

# ------------------------------------------------------------------ 15 Claude prompt bar (typed prompt + Enter)
def prompt_bar(canvas, k, parts, enter_t=None, cx=540, cy=900, w=960, size=36, attach=None, model="Opus 5.5",
               placeholder="How can I help you today?"):
    """claude.ai-style composer (dark) rising in; `parts` = [(text, t_start, dur)] type on one after another
    (word-synced appends: 'a landing page' ... ', for students who…'), caret blinks at the end; the orange
    send button presses at enter_t (scale dip + glow) and the typed text lifts/fades a beat after.
    attach = optional file chip inside the bar ('my_prompt.txt · 412 lines')."""
    fT = font(SFT("Regular"), size); lh = int(size * 1.38)
    txt = ""
    for s_, t0, dur in parts:
        if k <= t0: break
        txt += s_[:int(len(s_) * clamp((k - t0) / max(0.05, dur)))]
    lines = wrap(txt, fT, w - 100) if txt else []
    n = max(1, len(lines))
    top = 36 + (86 if attach else 0)
    h_ = top + n * lh + 104
    card = Image.new("RGBA", (w, h_), (0, 0, 0, 0))
    def dr(d, s): d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 30 * s, fill=(48, 48, 46, 255), outline=(78, 77, 72, 255), width=2 * s)
    card.alpha_composite(ss(dr, w, h_)); d = ImageDraw.Draw(card)
    if attach:
        f2 = font(SFT("Medium"), 26); cw = int(f2.getlength(attach)) + 92
        chip = ss(lambda dd, s: dd.rounded_rectangle((0, 0, cw * s - 1, 64 * s - 1), 14 * s, fill=(64, 64, 61, 255), outline=(92, 91, 86, 255), width=2 * s), cw, 64)
        ImageDraw.Draw(chip).text((28, 32), "▤", font=font(SFT("Regular"), 26), fill=(200, 198, 192), anchor="mm")
        ImageDraw.Draw(chip).text((56, 32), attach, font=f2, fill=(232, 230, 226), anchor="lm")
        card.alpha_composite(chip, (36, 30))
    sent = enter_t is not None and k >= enter_t + 0.25
    fade = 1 - clamp((k - enter_t - 0.25) / 0.3) if sent else 1
    if not txt:
        d.text((44, top), placeholder, font=fT, fill=(140, 138, 132))
    else:
        for i, ln in enumerate(lines):
            g = int(236 * fade + 48 * (1 - fade))
            d.text((44, top + i * lh - (1 - fade) * 20), ln, font=fT, fill=(g, g - 2, g - 6))
        if (k * 2.2) % 1 < 0.6 and not sent and lines:
            cx_ = 44 + fT.getlength(lines[-1]) + 4; cy_ = top + (len(lines) - 1) * lh
            d.rectangle((cx_, cy_ + 4, cx_ + 3, cy_ + size * 1.12), fill=(217, 119, 87))
    by = h_ - 62
    d.text((48, by), "+", font=font(SFT("Light"), 44), fill=(170, 168, 162), anchor="lm")
    fm = font(SFT("Medium"), 26)
    mx = w - 140 - fm.getlength(model)
    d.text((mx, by), model, font=fm, fill=(170, 168, 162), anchor="lm")
    vx = mx + fm.getlength(model) + 14
    d.line([(vx, by - 4), (vx + 7, by + 4), (vx + 14, by - 4)], fill=(170, 168, 162), width=3)
    press = 0
    if enter_t is not None and k >= enter_t:
        u = k - enter_t; press = math.exp(-u * 9) * (u < 0.6)
    bs = 64
    btn = ss(lambda dd, s: dd.rounded_rectangle((0, 0, bs * s - 1, bs * s - 1), 16 * s, fill=CLAUDE + (255,) if txt else (110, 80, 66, 255)), bs, bs)
    bd = ImageDraw.Draw(btn)
    bd.line([(bs / 2, 46), (bs / 2, 20)], fill=(255, 255, 255), width=5)
    bd.line([(bs / 2 - 11, 31), (bs / 2, 19), (bs / 2 + 11, 31)], fill=(255, 255, 255), width=5, joint="curve")
    if press > 0.01: place(card, _bloom(CLAUDE, 200), w - 40 - bs / 2, by, 1, 0, press)
    place(card, btn, w - 40 - bs / 2, by, 1 - 0.14 * press, 0, 1)
    e = expo(k / 0.5)
    place(canvas, card, cx, cy + (1 - e) * 60, 1, 0, clamp(k / 0.25), shadow=(0, 24, 30, 200))

# ------------------------------------------------------------------ 16 un-blur reveal (Kallaway)
def unblur_text(canvas, k, txt, t_word, cx=540, cy=560, size=96, color=None, lead=0.6, italic=False, shine=True,
                theme="dark"):
    """Kallaway's slow text reveal: the text is already there, blurred and dim, `lead` s before it's spoken; it
    sharpens exactly on the word (t_word, local time) in ~0.25s with a white shine sweeping across, then drifts.
    Stagger several calls on word times for ladders, tiers and lists (DeHIGAYRMkj @ 1-5s: 1,000 -> 1M)."""
    t0 = t_word - lead
    if k < t0: return
    f = sit(size, 640) if italic else font(SFD("Bold"), size)
    im = text_img(txt, f, fill=color or fg(theme), shadow=150 if theme == "dark" else 0)
    p = expo(clamp((k - t_word) / 0.25)) if k >= t_word else 0.0
    if shine and t_word <= k < t_word + 0.3:              # diagonal white band across the glyphs
        a = np.asarray(im).astype(np.float32)
        hh, ww = a.shape[:2]
        pos = -0.3 * ww + (k - t_word) / 0.3 * 1.6 * ww
        xx = np.arange(ww)[None, :] + 0.35 * np.arange(hh)[:, None]
        band = np.clip(1 - np.abs(xx - pos) / (0.12 * ww), 0, 1)[..., None] * 0.85
        a[..., :3] = a[..., :3] * (1 - band) + 255 * band
        im = Image.fromarray(a.astype(np.uint8), "RGBA")
    blur = 16 * (1 - p)
    if blur > 0.4: im = im.filter(ImageFilter.GaussianBlur(blur))
    alpha = clamp((k - t0) / 0.2) * (0.4 + 0.6 * p)
    s = (1.04 - 0.04 * p) * (1 + 0.02 * clamp((k - t_word) / 2.5))
    place(canvas, im, cx, cy, s, 0, alpha)

# ------------------------------------------------------------------ 17 polish helpers (style-guide §Polish rules, 2026-10-12)
def focus_in(canvas, k, img, cx, cy, d=0.3, scale=1.0, a=1.0, shadow=None):
    """Kallaway entrance: blur 14 -> 0 and 1.12x -> 1.0 in ~d s (expo). Use instead of drop-ins / back() bounces."""
    if k <= 0: return
    p = expo(clamp(k / d))
    im = img.filter(ImageFilter.GaussianBlur(14 * (1 - p))) if p < 0.97 else img
    place(canvas, im, cx, cy, scale * (1.12 - 0.12 * p), 0, a * clamp(k / 0.1), shadow)

def tag(canvas, k, txt, cx, cy, size=34, accent=RED):
    """The only label chip: dark, flat, red left bar, no tilt; focuses in."""
    f = font(SFT("Semibold"), size); w_ = int(f.getlength(txt)) + 56; h_ = int(size * 1.8)
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w_ - 1, h_ - 1), 10, fill=(22, 22, 24, 235))
    d.rectangle((0, 0, 7, h_ - 1), fill=accent)
    d.text((32, h_ / 2), txt, font=f, fill=(255, 255, 255), anchor="lm")
    focus_in(canvas, k, im, cx, cy)

def ripple(canvas, k, cx, cy, r0=40, r1=370, dur=0.5, color=RED):
    """thin ring expanding from the emphasised object, fading over ~15 frames."""
    if not 0 < k < dur: return
    e = expo(k / dur); r = r0 + (r1 - r0) * e
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (int(230 * (1 - e)),), width=6)
    canvas.alpha_composite(lay)

def push_layer(canvas, layer, k, dur, amount=0.06, cx=540, cy=640):
    """never frozen: composite a full-canvas layer pushed in 1.0 -> 1+amount across dur s (zoom about cx, cy)."""
    s = 1.0 + amount * clamp(k / max(0.1, dur))
    if s < 1.001: canvas.alpha_composite(layer); return
    big = layer.resize((int(W * s), int(H * s)), Image.BILINEAR)
    ox, oy = int(cx * s - cx), int(cy * s - cy)
    canvas.alpha_composite(big.crop((ox, oy, ox + W, oy + H)))

# ------------------------------------------------------------------ 18 Muse Wonder blocks
def versus_bars(canvas, k, rows, vmax=None, title=None, x0=260, y0=470, gap=210, wmax=600, bh=84, accent=0, decimals=0):
    """subject vs named rivals. rows=[(name, value, logo_path, t_on)]: on its t_on (the spoken name) each row's logo
    badge + name focus in, the bar grows (~0.6s) and the number counts in 0.25s (always lands before a cut).
    Row `accent` is red with a glow; others light grey. Faint track shows the full value from the start."""
    vmax = vmax or max(r[1] for r in rows) * 1.07
    if title: focus_in(canvas, k, text_img(title, font(SFT("Semibold"), 34), fill=(150, 150, 156)), 540, y0 - 140)
    fN, fV = font(SFT("Semibold"), 40), font(SFD("Bold"), 68)
    for j, (name, v, logo_path, ton) in enumerate(rows):
        u = k - ton
        if u <= 0: continue
        y = y0 + j * gap; e = expo(clamp(u / 0.6)); full = wmax * v / vmax
        if logo_path: focus_in(canvas, u, _badge(logo_path, 136), x0 - 110, y + 58, d=0.25, shadow=(0, 14, 20, 200))
        nm = text_img(name, fN, fill=(255, 255, 255))
        focus_in(canvas, u, nm, x0 + nm.width / 2 - 12, y - 18, d=0.25)
        bw = max(2, int(full * e)); col = RED if j == accent else (205, 205, 210)
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle((x0, y + 16, x0 + full, y + 16 + bh), 14, fill=(255, 255, 255, 18))
        if j == accent:
            gl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle((x0, y + 16, x0 + bw, y + 16 + bh), 14, fill=RED + (200,))
            canvas.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)))
        d.rounded_rectangle((x0, y + 16, x0 + bw, y + 16 + bh), 14, fill=col + (255,))
        canvas.alpha_composite(lay)
        val = v * expo(clamp(u / 0.25))
        num = text_img(f"{val:.{decimals}f}" if decimals else f"{round(val)}", fV, fill=(255, 255, 255), shadow=140)
        place(canvas, num, x0 + bw + 22 + num.width / 2, y + 16 + bh / 2, 1, 0, clamp(u / 0.15))

def rewind_counter(canvas, k, a=2026, b=2021, settle="Oct 2021", label="rewind", dur=0.9, cx=540, cy=680,
                   top_y=410, size=220, alpha=1.0):
    """time-jump counter for "go back N years": the year rolls a -> b over `dur` (inout) with an italic label under
    it, then shrinks and rises to top_y as the settled date (`settle`) for the rest of the beat. alpha lets the caller
    fade it out (e.g. as a photo sharpens)."""
    if k <= 0 or alpha <= 0: return
    p = inout(clamp(k / dur)); yr = round(a + (b - a) * p)
    m = expo(clamp((k - dur - 0.1) / 0.4))
    im = text_img(str(yr) if m < 0.5 else settle, font(SFD("Bold"), int(size - (size - 70) * m)), fill=(255, 255, 255), shadow=160)
    place(canvas, im, cx, cy - (cy - top_y) * m, 1.0 + 0.04 * (1 - p), 0, clamp(k / 0.1) * alpha)
    if label and k < dur + 0.1:
        place(canvas, text_img(label, sit(54, 640), fill=(220, 220, 224), shadow=150), cx, cy + 150, 1, 0,
              clamp(k / 0.15) * (1 - m) * alpha)

def flip_tile(canvas, k, front, back, cx, cy, dur=0.36, a=1.0, shadow=(0, 18, 24, 200)):
    """card flip on its word (old brand -> new brand, before -> after): front shows until k=0, squashes to an edge,
    back opens out with a small lift. front/back are same-size RGBA tiles."""
    if k <= 0: place(canvas, front, cx, cy, 1, 0, a, shadow); return
    p = clamp(k / dur); sx = abs(math.cos(p * math.pi))
    face_ = front if p < 0.5 else back
    im = face_.resize((max(2, int(face_.width * sx)), face_.height), Image.LANCZOS)
    place(canvas, im, cx, cy, 1.0 + 0.06 * math.sin(p * math.pi), 0, a, shadow)

def dot_stream(canvas, k, src, targets, n=70, seed=7, spread=120, r=9):
    """users / data leaving one thing for others: white dots stream on curved paths from src=(x, y) to targets
    [((x, y), t_on)], split evenly across the targets that are already on. k = seconds since the stream starts."""
    if k <= 0: return
    rnd = random.Random(seed); lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for j in range(n):
        ph, sp, bend = rnd.random(), rnd.uniform(0.7, 1.1), rnd.uniform(-spread, spread)
        if k < j * 0.02: continue
        live = [p for p, ton in targets if k >= ton] or [targets[0][0]]
        to = live[j % len(live)]
        u = (k * sp * 0.9 + ph) % 1.0
        x = src[0] + 120 + (to[0] - src[0] - 200) * u
        y = src[1] + (to[1] - src[1]) * u + bend * math.sin(u * math.pi)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(230 * math.sin(u * math.pi))))
    canvas.alpha_composite(lay)

def post_receipt(canvas, k, avatar, name, handle, text, chart, crop, cols=(), meta="", stats="", t_chart=0.3,
                 post_cy=548, chart_y=790, chart_w=980, size=38):
    """launch receipt: the founder's real X post (verbatim via `post`) with the real chart under it. chart = RGBA
    image, crop = (x0, y0, x1, y1) in chart px (just the columns/rows that matter, so it reads on a phone);
    cols=[(x0, x1, t_on)] in chart px get a red tint + outline on their word. Hold the beat >= 2.1s."""
    post(canvas, k, avatar, name, handle, text, meta=meta, stats=stats, cx=540, cy=post_cy, w=980, size=size, dim=False)
    u = k - t_chart
    if u <= 0: return
    s = chart_w / (crop[2] - crop[0])
    tab = chart.crop(crop).resize((chart_w, int((crop[3] - crop[1]) * s)), Image.LANCZOS).convert("RGBA")
    for c0, c1, ton in cols:
        kw = k - ton
        if kw <= 0: continue
        x0, x1, e = (c0 - crop[0]) * s, (c1 - crop[0]) * s, expo(kw / 0.3)
        tint = Image.new("RGBA", tab.size, (0, 0, 0, 0))
        ImageDraw.Draw(tint).rectangle((x0, 0, x1, tab.height), fill=RED + (int(40 * e),))
        tab.alpha_composite(tint)
        ImageDraw.Draw(tab).rounded_rectangle((x0 + 3, 4, x1 - 3, tab.height - 4), 14, outline=RED + (int(255 * e),), width=7)
    tab = rounded_rect(tab, 22); e = expo(u / 0.4)
    place(canvas, tab, 540, chart_y + tab.height / 2 + (1 - e) * 60, 1.0 + 0.02 * clamp(k / 2), 0, clamp(u / 0.2),
          shadow=(0, 24, 30, 220))

# ------------------------------------------------------------------ 19 reel blocks (2026-10-20, from the Claude-editing reels study)
EMOJI_FONTS = (("/System/Library/Fonts/Apple Color Emoji.ttc", 160), ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109))

@lru_cache(32)
def emoji_img(ch, size):
    """colour emoji as an RGBA image `size` px tall (Apple on macOS, Noto on Linux); None if neither font exists."""
    for path, base in EMOJI_FONTS:
        try: f = ImageFont.truetype(path, base)
        except OSError: continue
        im = Image.new("RGBA", (base * 3, base * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((base * 1.5, base), ch, font=f, embedded_color=True, anchor="mm")
        im = im.crop(im.getbbox()); r = size / im.height
        return im.resize((max(1, int(im.width * r)), size), Image.LANCZOS)
    return None

@lru_cache(16)
def _title_box_img(text, emoji, w, size):
    f = font(SFD("Bold"), size); lh = int(size * 1.24); px, py = 46, 30
    es = int(size * 1.05) if emoji else 0
    lines = wrap(text, f, w - 2 * px)
    if len(lines) > 1:
        full = f.getlength(text) + es
        lines = next(ls for ls in (wrap(text, f, full / len(lines) + size * j) for j in range(40)) if len(ls) <= len(lines))
    lw = [f.getlength(l) for l in lines]
    if emoji and lw[-1] + es + 14 > w - 2 * px: lines.append(""); lw.append(0)
    widths = list(lw)
    if emoji: widths[-1] += es + (14 if lw[-1] else 0)
    bw = int(max(widths)) + 2 * px; bh = len(lines) * lh + 2 * py
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, bw * s - 1, bh * s - 1), 28 * s, fill=(255, 255, 255, 255)), bw, bh)
    d = ImageDraw.Draw(im)
    for i, (ln, ww) in enumerate(zip(lines, widths)):
        x = (bw - ww) / 2; y = py + i * lh + lh / 2
        if ln: d.text((x, y), ln, font=f, fill=INK, anchor="lm")
        if emoji and i == len(lines) - 1:
            e = emoji_img(emoji, es)
            if e: im.alpha_composite(e, (int(x + lw[-1] + (14 if ln else 0)), int(y - e.height / 2)))
    return im

def title_box(canvas, k, text, emoji=None, cy=250, w=940, size=56, out=None):
    """hook title: white rounded box at the top, black bold text, one emoji at the end. Focuses in;
    held across beats; `out` (local s) lifts and fades it so a cta_box can take its place."""
    im = _title_box_img(text, emoji, w, size)
    if out is not None and k >= out:
        u = expo((k - out) / 0.3)
        place(canvas, im, 540, cy - 30 * u, 1, 0, 1 - u, shadow=(0, 14, 26, 120)); return
    focus_in(canvas, k, im, 540, cy, d=0.32, shadow=(0, 14, 26, 120))

@lru_cache(16)
def _cta_parts(lead, word, tail, size, accent):
    f = font(SFD("Bold"), size); f2 = font(SFT("Medium"), int(size * 0.62))
    pw = int(font(SFD("Heavy"), size).getlength(word)) + 56; ph = int(size * 1.5)
    pill = ss(lambda d, s: d.rounded_rectangle((0, 0, pw * s - 1, ph * s - 1), 18 * s, fill=accent + (255,)), pw, ph)
    ImageDraw.Draw(pill).text((pw / 2, ph / 2), word, font=font(SFD("Heavy"), size), fill=(255, 255, 255), anchor="mm")
    lw = int(f.getlength(lead)); row = lw + 20 + pw
    tw = int(f2.getlength(tail)) if tail else 0
    bw = max(row, tw) + 96; bh = ph + 64 + (int(size * 0.95) if tail else 0)
    box = ss(lambda d, s: d.rounded_rectangle((0, 0, bw * s - 1, bh * s - 1), 30 * s, fill=(255, 255, 255, 255)), bw, bh)
    d = ImageDraw.Draw(box); x0 = (bw - row) / 2
    d.text((x0, 32 + ph / 2), lead, font=f, fill=INK, anchor="lm")
    if tail: d.text((bw / 2, 32 + ph + size * 0.5), tail, font=f2, fill=(110, 108, 104), anchor="mm")
    return box, pill, (x0 + lw + 20 + pw / 2 - bw / 2, 32 + ph / 2 - bh / 2)

def cta_box(canvas, k, word, lead="Comment", tail="and I'll send it to you", cy=1480, size=58, accent=RED):
    """end CTA: white box 'Comment [WORD]' with the keyword in an accent pill, a grey line under it.
    The pill breathes (1.0 -> 1.05) every 1.2s so the held frame never freezes."""
    box, pill, (dx, dy) = _cta_parts(lead, word, tail, size, accent)
    if k <= 0: return
    focus_in(canvas, k, box, 540, cy, d=0.32, shadow=(0, 16, 28, 140))
    p = expo(clamp((k - 0.2) / 0.3)); u = max(0.0, k - 0.6) % 1.2
    pulse = 0.05 * math.sin(math.pi * clamp(u / 0.4)) if k > 0.6 else 0
    place(canvas, pill, 540 + dx, cy + dy, (1.12 - 0.12 * p) * (1 + pulse), 0, clamp((k - 0.2) / 0.1))

def word_captions(canvas, k, words, cy=1180, size=104, keys=(), accent=RED, hold=0.5):
    """one word at a time, bold white uppercase; key words sit on an accent box. words = [(word, t)] in local s."""
    cur = None
    for i, (w_, t) in enumerate(words):
        end = words[i + 1][1] if i + 1 < len(words) else t + hold
        if t <= k < end: cur = (w_, t)
    if not cur: return
    w_, t = cur; key = w_.lower().strip(".,!?") in {x.lower() for x in keys}
    im = text_img(w_.upper(), font(SFD("Heavy"), size), fill=(255, 255, 255), shadow=0 if key else 170)
    if key:
        bw, bh = im.width - 2 * im.pad + 48, int(size * 1.18)
        bx = ss(lambda d, s: d.rounded_rectangle((0, 0, bw * s - 1, bh * s - 1), 16 * s, fill=accent + (255,)), bw, bh)
        bx.alpha_composite(im, (int((bw - im.width) / 2), int((bh - im.height) / 2 + size * 0.04))); im = bx
    focus_in(canvas, k - t, im, 540, cy, d=0.14)

def _round_rect_path(box, r, n=12):
    x0, y0, x1, y1 = box; r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = [((x0 + x1) / 2, y0)]
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * j / n)), cy + r * math.sin(math.radians(a0 + 90 * j / n))) for j in range(n + 1)]
    return pts + [pts[0]]

def ui_highlight(canvas, k, box, label=None, color=RED, dur=0.45, dim=0.5, radius=18, width=7, label_pos="below"):
    """point at part of a screen recording: the rest dims, an accent rounded box draws itself round `box`
    (x0, y0, x1, y1), an optional tag sits below or above it (label_pos)."""
    if k <= 0: return
    a = clamp(k / 0.25)
    if dim:
        m = Image.new("L", canvas.size, int(255 * dim * a))
        ImageDraw.Draw(m).rounded_rectangle(box, radius, fill=0)
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 255)); sh.putalpha(m); canvas.alpha_composite(sh)
    x0, y0, x1, y1 = box; pad = width * 2
    path = [(x - x0 + pad, y - y0 + pad) for x, y in _round_rect_path(box, radius)]
    seg = _partial(path, expo(k / dur))
    lw, lh = int(x1 - x0 + pad * 2), int(y1 - y0 + pad * 2)
    if len(seg) > 1:
        ring = ss(lambda d, s: d.line([(x * s, y * s) for x, y in seg], fill=color + (255,), width=width * s, joint="curve"), lw, lh)
        canvas.alpha_composite(ring, (int(x0 - pad), int(y0 - pad)))
    if label: tag(canvas, k - dur * 0.7, label, (x0 + x1) / 2, y1 + 58 if label_pos == "below" else y0 - 58, size=32, accent=color)

@lru_cache(8)
def _bubble_base(r, ring):
    d = 2 * r + ring * 2
    base = ss(lambda dd, sc: dd.ellipse((0, 0, d * sc - 1, d * sc - 1), fill=(255, 255, 255, 255)), d, d)
    m = ss(lambda dd, sc: dd.ellipse((0, 0, 2 * r * sc - 1, 2 * r * sc - 1), fill=(255, 255, 255, 255)), 2 * r, 2 * r).split()[3]
    return base, m

def face_bubble(canvas, k, face, cx=850, cy=330, r=170, ring=8):
    """round face over a screen recording: `face` (this frame's face image) centre-cropped into a circle
    with a white ring and a soft shadow; focuses in."""
    base, m = _bubble_base(r, ring)
    f_ = ImageOps.fit(face.convert("RGBA"), (2 * r, 2 * r), Image.LANCZOS); f_.putalpha(m)
    im = base.copy(); im.alpha_composite(f_, (ring, ring))
    focus_in(canvas, k, im, cx, cy, d=0.3, shadow=(0, 16, 30, 170))

def _edged(im, radius):
    """thin light edge so a dark thumbnail still reads against the dark canvas."""
    ring = ss(lambda d, s: d.rounded_rectangle((0, 0, im.width * s - 1, im.height * s - 1), radius * s, outline=(255, 255, 255, 46), width=2 * s), im.width, im.height)
    out = im.copy(); out.alpha_composite(ring); return out

def result_card(canvas, k, frame, cy=880, w=820, radius=40, dur=1.2):
    """flash a finished result: the frame fills the screen blurred and dark, a sharp rounded copy sits on top
    and pushes in 1.0 -> 1.04 over `dur`. `frame` = this frame of the result clip (any aspect)."""
    s = max(W / frame.width, H / frame.height)
    bg = frame.convert("RGB").resize((max(1, int(frame.width * s / 8)), max(1, int(frame.height * s / 8))), Image.BILINEAR)
    bg = bg.filter(ImageFilter.GaussianBlur(6)).resize((int(frame.width * s), int(frame.height * s)), Image.BILINEAR)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45).convert("RGBA")
    if k > 0: canvas.alpha_composite(_alpha(bg, clamp(k / 0.15)))
    h_ = int(frame.height * w / frame.width)
    card = _edged(rounded_rect(frame.convert("RGB").resize((w, h_), Image.LANCZOS), radius), radius)
    focus_in(canvas, k, card, 540, cy, d=0.25, scale=1 + 0.04 * clamp(k / dur), shadow=(0, 26, 40, 210))

@lru_cache(16)
def _file_card_img(name, kind, lines, w, size):
    fN = font(SFT("Semibold"), size); fS = font(SFT("Regular"), int(size * 0.7)); fM = font(MONO, int(size * 0.66))
    lh = int(size * 1.0); top = 150; h_ = top + 30 + len(lines) * lh + (30 if lines else 0)
    card = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 26 * s, fill=(38, 38, 36, 255), outline=(78, 77, 72, 255), width=2 * s), w, h_)
    ic = ss(lambda d, s: d.rounded_rectangle((0, 0, 86 * s - 1, 96 * s - 1), 14 * s, fill=(58, 58, 55, 255), outline=(96, 95, 90, 255), width=2 * s), 86, 96)
    ImageDraw.Draw(ic).text((43, 48), kind[:4], font=font(SFT("Bold"), 20), fill=CLAUDE, anchor="mm")
    card.alpha_composite(ic, (36, 30)); d = ImageDraw.Draw(card)
    d.text((146, 62), name, font=fN, fill=(240, 238, 234), anchor="lm")
    d.text((146, 102), f"{kind} · {len(lines)} lines", font=fS, fill=(150, 148, 142), anchor="lm")
    if lines: d.line([(36, top), (w - 36, top)], fill=(64, 64, 61), width=2)
    return card, top + 30, lh, fM

def file_card(canvas, k, name, kind="JSON", lines=(), cx=540, cy=640, w=840, size=40, t_lines=0.35, stagger=0.1):
    """the files Claude writes (audio.json, design.md, memory.md) as a claude.ai-style card; preview lines
    fade in one by one so it reads like Claude writing it."""
    lines = tuple(lines)
    card, y0, lh, fM = _file_card_img(name, kind, lines, w, size)
    card = card.copy(); d = ImageDraw.Draw(card)
    for i, ln in enumerate(lines):
        a = clamp((k - t_lines - i * stagger) / 0.18)
        if a > 0:
            c = int(80 + 120 * a)
            d.text((40 + (1 - a) * 14, y0 + i * lh), ln, font=fM, fill=(c, c - 2, c - 6))
    focus_in(canvas, k, card, cx, cy, d=0.3, shadow=(0, 22, 34, 190))

def endcard_grid(canvas, k, tiles, header=None, cols=3, cy=760, w=960, gap=22, radius=22, stagger=0.06):
    """end card: a grid of 9:16 thumbnails (what's in the pack) focusing in one after another, optional header above."""
    tw = (w - gap * (cols - 1)) // cols; th = int(tw * 16 / 9)
    rows = math.ceil(len(tiles) / cols); gh = rows * th + gap * (rows - 1)
    y0 = cy - gh / 2 + th / 2; x0 = 540 - w / 2 + tw / 2
    if header: focus_in(canvas, k, text_img(header, font(SFD("Bold"), 64), fill=(255, 255, 255), shadow=150), 540, cy - gh / 2 - 80)
    for i, t_ in enumerate(tiles):
        im = ImageOps.fit(t_.convert("RGB"), (tw, th), Image.LANCZOS)
        focus_in(canvas, k - 0.15 - i * stagger, _edged(rounded_rect(im, radius), radius), x0 + (i % cols) * (tw + gap), y0 + (i // cols) * (th + gap),
                 d=0.28, shadow=(0, 14, 24, 170))

# ------------------------------------------------------------------ 20 library formats (2026-10-31, from the IG format study)
TIER_COLS = [(255, 127, 127), (255, 191, 127), (255, 223, 127), (191, 255, 127), (127, 191, 255)]

def person_over(canvas, frame, mask, scale=1.0, z=1.0, cy=0.5):
    """the person from a full-frame shot, keyed by the person mask, drawn over whatever is on the canvas
    (depth reels: UI or images behind the head). scale < 1 shrinks them toward the bottom edge."""
    from .core import cover
    f = cover(frame.convert("RGBA"), W, H, z=z, cy=cy)
    m = cover(mask.convert("L"), W, H, z=z, cy=cy).filter(ImageFilter.GaussianBlur(1.2))
    f.putalpha(m)
    if scale != 1.0:
        f = f.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
        sh = drop_shadow(f, blur=30, alpha=150)
        canvas.alpha_composite(sh.crop((0, 0, sh.width, sh.height - sh.pad)), (int((W - f.width) / 2) - sh.pad, H - f.height - sh.pad))
    canvas.alpha_composite(f, (int((W - f.width) / 2), H - f.height))

def tier_list(canvas, k, items, labels="SABCD", x0=90, y0=980, w=900, rh=150, t0=0.0):
    """ranking board: coloured tier labels on the left, logos focus into their row as each is named.
    items = [(row, logo_path, t_on)]; rows fill left to right."""
    a = clamp((k - t0) / 0.3)
    if a <= 0: return
    board = Image.new("RGBA", (w, rh * len(labels)), (0, 0, 0, 0)); d = ImageDraw.Draw(board)
    for i, lab in enumerate(labels):
        y = i * rh
        d.rectangle((0, y, rh - 1, y + rh - 3), fill=TIER_COLS[i % 5] + (255,))
        d.rectangle((rh, y, w - 1, y + rh - 3), fill=(26, 26, 30, 235))
        d.text((rh / 2, y + rh / 2), lab, font=font(SFD("Heavy"), int(rh * 0.42)), fill=INK, anchor="mm")
    place(canvas, board, x0 + w / 2, y0 + board.height / 2, 1.0, 0, a)
    count = {}
    for row, path, t_on in items:
        n = count.get(row, 0); count[row] = n + 1
        cx, cy = x0 + rh + 30 + (rh - 30) / 2 + n * rh, y0 + row * rh + rh / 2 - 1
        focus_in(canvas, k - t_on, _badge(path, int(rh * 0.78)), cx, cy, shadow=(0, 8, 14, 160))

def ui_wall(canvas, k, tiles, cols=3, w=330, gap=22, speed=40, top=-80, radius=22):
    """a wall of screenshots or thumbnails that drifts up slowly; draw it first, then person_over() so the head
    sits in front of it."""
    th = int(w * 16 / 9)
    x0 = (W - (cols * w + (cols - 1) * gap)) / 2
    off = k * speed
    for i, t_ in enumerate(tiles):
        c, r = i % cols, i // cols
        im = rounded_rect(ImageOps.fit(t_.convert("RGB"), (w, th), Image.LANCZOS), radius)
        cy = top + r * (th + gap) + th / 2 - off + (th / 3 if c == 1 else 0)
        focus_in(canvas, k - 0.05 * i, im, x0 + c * (w + gap) + w / 2, cy, a=0.92)

def views_card(canvas, k, views, name, sub, avatar=None, cx=540, cy=1240, w=820, t_count=0.9):
    """the payoff card on a depth reel: big view count that counts up, channel row and a Subscribe pill."""
    if k <= 0: return
    h_ = 300
    im = Image.new("RGBA", (w, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h_ - 1), 34, fill=(18, 18, 20, 235))
    n = int(views * expo(clamp(k / t_count)))
    d.text((44, 96), f"{n:,}", font=font(SFD("Bold"), 110), fill=(255, 255, 255), anchor="lm")
    d.text((44 + font(SFD("Bold"), 110).getlength(f"{views:,}") + 16, 118), "views", font=font(SFT("Medium"), 34),
           fill=(200, 200, 204), anchor="lm")
    if avatar:
        av = ImageOps.fit(Image.open(avatar).convert("RGB"), (72, 72))
        m = Image.new("L", (72, 72), 0); ImageDraw.Draw(m).ellipse((0, 0, 71, 71), fill=255)
        im.paste(av, (44, 200), m)
    d.text((134, 218), name, font=font(SFT("Bold"), 34), fill=(255, 255, 255), anchor="lm")
    d.text((134, 254), sub, font=font(SFT("Regular"), 26), fill=(160, 160, 166), anchor="lm")
    d.rounded_rectangle((w - 230, 206, w - 44, 266), 30, fill=(255, 255, 255))
    d.text((w - 137, 236), "Subscribe", font=font(SFT("Semibold"), 28), fill=INK, anchor="mm")
    focus_in(canvas, k, im, cx, cy, shadow=(0, 18, 30, 200))

def image_grid(canvas, k, images, gap=0, stagger=0.12):
    """2x2 full-bleed grid of images that focus in one by one; put person_over() on top for a cutout grid."""
    cw, ch = (W - gap) // 2, (H - gap) // 2
    for i, img in enumerate(images[:4]):
        im = ImageOps.fit(img.convert("RGB"), (cw, ch), Image.LANCZOS).convert("RGBA")
        focus_in(canvas, k - i * stagger, im, (i % 2) * (cw + gap) + cw / 2, (i // 2) * (ch + gap) + ch / 2, d=0.35)

def price_tag(canvas, k, text, cx, cy, size=64):
    """flat white price tag with a punched hole; focuses in on the spoken price."""
    f = font(SFD("Bold"), size)
    tw = int(f.getlength(text)); w_, h_ = tw + 130, int(size * 1.7)
    def dr(d, s):
        pts = [(0, h_ / 2), (44, 0), (w_ - 1, 0), (w_ - 1, h_ - 1), (44, h_ - 1)]
        d.polygon([(x * s, y * s) for x, y in pts], fill=(255, 255, 255, 255))
        d.ellipse((30 * s, (h_ / 2 - 9) * s, 48 * s, (h_ / 2 + 9) * s), fill=(0, 0, 0, 0))
    im = ss(dr, w_, h_)
    ImageDraw.Draw(im).text((70 + tw / 2, h_ / 2), text, font=f, fill=INK, anchor="mm")
    focus_in(canvas, k, im, cx, cy, shadow=(0, 12, 20, 170))

def relay_line(canvas, k, stations, y=640, x0=130, x1=950, color=GOLD):
    """a hairline runs left to right through labelled stations; a glowing token travels it and each station
    lights as it's reached. stations = [(label, t_on)]."""
    if k <= 0: return
    n = len(stations)
    xs = [x0 + (x1 - x0) * i / max(1, n - 1) for i in range(n)]
    d = ImageDraw.Draw(canvas)
    p = expo(clamp(k / 0.5))
    d.line([(x0, y), (x0 + (x1 - x0) * p, y)], fill=(120, 120, 126), width=5)
    for i, ((lab, t_on), x) in enumerate(zip(stations, xs)):
        on = k >= t_on
        r = 24
        d.ellipse((x - r, y - r, x + r, y + r), fill=(color if on else (40, 40, 44)), outline=(150, 150, 156), width=3)
        lab_im = text_img(lab, font(SFT("Semibold"), 44), fill=(255, 255, 255) if on else (120, 120, 126))
        place(canvas, lab_im, x, y + 84, 1, 0, clamp(k / 0.3))
    done = [t for _, t in stations if t <= k]
    if done:
        i = len(done) - 1
        nxt = stations[i + 1][1] if i + 1 < n else None
        tx = xs[i] if nxt is None else xs[i] + (xs[i + 1] - xs[i]) * inout(clamp((k - stations[i][1]) / max(0.01, nxt - stations[i][1])))
        glow = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((70, 70, 150, 150), fill=color + (255,))
        place(canvas, glow.filter(ImageFilter.GaussianBlur(24)), tx, y, 1, 0, 1)
        d.ellipse((tx - 13, y - 13, tx + 13, y + 13), fill=(255, 255, 255))

def score_ring(canvas, k, value, cx=540, cy=600, r=210, label=None, color=GREEN, dur=1.0):
    """a ring fills to `value` percent while the number counts up in the middle; optional label under it."""
    if k <= 0: return
    p = expo(clamp(k / dur))
    def dr(d, s):
        box = (14 * s, 14 * s, (2 * r - 14) * s, (2 * r - 14) * s)
        d.arc(box, 0, 360, fill=(255, 255, 255, 30), width=22 * s)
        d.arc(box, -90, -90 + 360 * value / 100 * p, fill=color + (255,), width=22 * s)
    ring = ss(dr, 2 * r, 2 * r)
    place(canvas, ring, cx, cy, 1, 0, clamp(k / 0.2))
    num = text_img(f"{int(round(value * p))}%", font(SFD("Bold"), int(r * 0.62)), fill=(255, 255, 255))
    place(canvas, num, cx, cy, 1, 0, clamp(k / 0.2))
    if label: focus_in(canvas, k - dur * 0.6, text_img(label, sit(52), fill=(220, 220, 224)), cx, cy + r + 60)

def _folder(w=150, color=(64, 156, 255)):
    h_ = int(w * 0.78)
    def dr(d, s):
        d.rounded_rectangle((0, 0, w * 0.45 * s, h_ * 0.3 * s), 8 * s, fill=tuple(int(c * 0.82) for c in color) + (255,))
        d.rounded_rectangle((0, h_ * 0.14 * s, w * s - 1, h_ * s - 1), 12 * s, fill=color + (255,))
    return ss(dr, w, h_)

def folder_tree(canvas, k, root, children, cy=420, theme="dark"):
    """a folder with its subfolders branching out one by one. children = [(name, t_on)]."""
    if k <= 0: return
    col = fg(theme)
    focus_in(canvas, k, _folder(230), 540, cy)
    place(canvas, text_img(root, font(MONO, 40), fill=col), 540, cy + 130, 1, 0, clamp(k / 0.3))
    n = len(children); span = min(900, 300 * n)
    xs = [540 - span / 2 + span * (i + 0.5) / n for i in range(n)]
    d = ImageDraw.Draw(canvas)
    ybar, yc = cy + 210, cy + 370
    shown = [i for i, (_, t) in enumerate(children) if k >= t]
    if shown:
        d.line([(540, cy + 168), (540, ybar)], fill=col + (140,), width=4)
        d.line([(xs[0], ybar), (xs[max(shown)], ybar)], fill=col + (140,), width=4)
    for i in shown:
        name, t_on = children[i]
        d.line([(xs[i], ybar), (xs[i], yc - 70)], fill=col + (140,), width=4)
        focus_in(canvas, k - t_on, _folder(170), xs[i], yc)
        place(canvas, text_img(name, font(MONO, 36), fill=col), xs[i], yc + 100, 1, 0, clamp((k - t_on) / 0.3))

def value_pair(canvas, k, a, b, label=None, chapter=None, cy=640, t_b=0.8):
    """two dark value boxes side by side (before | after), the second counting up on its word; optional
    chapter tab above ("01  Contrast") and a label under them. a, b = (prefix, number)."""
    if chapter: tag(canvas, k, chapter, 540, cy - 230, size=40)
    for i, ((prefix, val), t_on, w_) in enumerate(((a, 0.0, 300), (b, t_b, 440))):
        if k < t_on: continue
        n = int(val * expo(clamp((k - t_on) / 0.7))) if i else val
        box = Image.new("RGBA", (w_, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(box)
        d.rounded_rectangle((0, 0, w_ - 1, 189), 22, fill=(32, 32, 36, 240), outline=(255, 255, 255, 30), width=2)
        d.text((w_ / 2, 95), f"{prefix}{n:,}", font=font(SFD("Bold"), 92), fill=(255, 255, 255), anchor="mm")
        focus_in(canvas, k - t_on, box, 255 if i == 0 else 690, cy)
    if t_b < k:
        glow = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((150, 150, 350, 350), fill=CLAUDE + (150,))
        place(canvas, glow.filter(ImageFilter.GaussianBlur(70)), 540, cy + 250, 1, 0, clamp((k - t_b) / 0.6))
    if label: focus_in(canvas, k - t_b - 0.4, text_img(label, font(SFT("Semibold"), 44), fill=(255, 255, 255)), 540, cy + 300)
