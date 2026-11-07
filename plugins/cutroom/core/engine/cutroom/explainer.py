"""Explainer-animation primitives (v7, approved 2026-10-01 on the agent-swarm reel: "the animations and updates are on point").
Lifted from `short form/2026-10-01-agent-swarm/edit/render1.py`. Scene code (office, pipeline, library…) stays per-video;
these are the reusable building blocks. See references/explainer-animations.md."""
import math
import numpy as np
from PIL import Image, ImageDraw
from .core import *
from . import components as C
from .components import HILITE

TEAM = [(96, 150, 255), (110, 205, 120), (245, 128, 80), (176, 118, 245)]   # blue/green/orange/purple (OpenAI DevDay slides)
RED = (232, 72, 60)
GREEN = (90, 210, 120)
PW, PH = 900, 500                                                            # stack card content size

# ------------------------------------------------------------------ safe paste + math
def P(canvas, img, x, y, a=1.0):
    """paste() that tolerates negative coords (PIL alpha_composite raises on them)."""
    x, y = int(round(x)), int(round(y))
    if x < 0 or y < 0:
        cx, cy = max(0, -x), max(0, -y)
        if cx >= img.width or cy >= img.height: return
        img = img.crop((cx, cy, img.width, img.height)); x += cx; y += cy
    if x >= canvas.width or y >= canvas.height: return
    paste(canvas, img, x, y, a)

def PC(canvas, img, cx, cy, a=1.0): P(canvas, img, cx - img.width / 2, cy - img.height / 2, a)
def lerp(a, b, e): return (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e)
def lerpc(a, b, e): return tuple(int(a[i] + (b[i] - a[i]) * e) for i in range(3))
def vexpo(x):
    x = np.clip(x, 0, 1); return np.where(x >= 1, 1.0, 1 - 2 ** (-10 * x))
def bez(a, c, b, u):
    """quadratic bezier point (card flights, curved hand-offs)"""
    return ((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1])

# ------------------------------------------------------------------ cards / stage
def panel(w=PW, h=PH): return C.dark_panel(w, h, grid=False, glow=False)

def kick(p, txt, x=40, y=26, col=(165, 160, 158), size=24, a=1.0):
    """small tracked kicker INSIDE a card — replaces red headers on explainer reels"""
    k = C.kicker(txt, col=col, size=size); P(p, k, x - k.pad, y - k.pad, a); return k

def place_card(im, content, k, y=370):
    g = C.glow_card(content)
    P(im, g, W / 2 - g.width / 2, y - g.pad + (1 - expo(k / 0.5)) * 50, cubic(k / 0.35))

def full_panel(t, t0, p, scale=1.16, cy=810):
    """Same stack scene, blown up full screen (band centre y=810). No glow_card: its pad makes it wider than 1080."""
    im = C.dotted_bg(W, H)
    s = rounded(p.resize((int(p.width * scale), int(p.height * scale)), Image.LANCZOS), 30)
    ImageDraw.Draw(s).rounded_rectangle((0, 0, s.width - 1, s.height - 1), 30, outline=(255, 255, 255, 70), width=2)
    k = t - t0
    P(im, s, W / 2 - s.width / 2, cy - s.height / 2 + (1 - expo(k / 0.5)) * 50, cubic(k / 0.3))
    return im

def chip_img(txt, bg=(255, 255, 255), fg=INK, f=None, h=80):
    f = f or font(SFT("Semibold"), 40)
    w = int(f.getlength(txt)) + 70
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=bg + (255,))
    d.text((35, h / 2), txt, font=f, fill=fg, anchor="lm")
    return im

def credit_pill(handle):
    cr = C.kicker(handle, col=(215, 215, 220), size=26)
    pill = Image.new("RGBA", (cr.width + 24, cr.height + 14), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), 12, fill=(0, 0, 0, 175))
    pill.alpha_composite(cr, (12, 7))
    return pill

# ------------------------------------------------------------------ glyphs
_ORB = {}
def orb(r, col):
    """glowing node (agent, model, goal). Cached. paste with PC()."""
    key = (r, col)
    if key not in _ORB:
        s = int(r * 4); yy, xx = np.mgrid[0:s, 0:s]; d = np.hypot(xx - s / 2, yy - s / 2) / r
        glow = np.clip(1 - d / 2, 0, 1) ** 2.4 * 170
        core = np.clip((0.55 - d) * r + 0.5, 0, 1)
        a = np.maximum(glow, core * 255)
        c = np.array(col, float); m = core[..., None] * 0.45
        _ORB[key] = Image.fromarray(np.dstack([c * (1 - m) + 255 * m, a]).clip(0, 255).astype(np.uint8), "RGBA")
    return _ORB[key]

def star(d, cx, cy, r, col):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=col)

def ring(d, x, y, k, col=(255, 255, 255), dur=0.6, r0=14, r1=60):
    """expanding pulse ring for k in (0, dur) — 'this just happened' marker"""
    if not 0 < k < dur: return
    r = r0 + (r1 - r0) * expo(k / dur); a = int(230 * (1 - k / dur))
    d.ellipse((x - r, y - r, x + r, y + r), outline=col + (a,), width=4)

def mini_card(d, x, y, col=(250, 250, 250)):
    """tiny 'document' that flies between nodes"""
    d.rounded_rectangle((x - 20, y - 14, x + 20, y + 14), 5, fill=col + (255,))
    for j in range(3): d.line((x - 12, y - 6 + j * 6, x + 12 - (8 if j == 2 else 0), y - 6 + j * 6), fill=(60, 60, 66, 255), width=2)

def rect_path(d, r, p, col, w=3):
    """line-draw a rectangle outline to progress p (floor plans, boxes drawing on)"""
    if p <= 0: return
    x0, y0, x1, y1 = r; pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    Lr = 2 * ((x1 - x0) + (y1 - y0)) * p
    for a, b in zip(pts, pts[1:]):
        sg = math.dist(a, b)
        if Lr <= 0: break
        f = min(1, Lr / sg); d.line([a, lerp(a, b, f)], fill=col, width=w); Lr -= sg

# ------------------------------------------------------------------ swarms (thousands of dots, numpy)
def stamp(p, xs, ys, cols, alpha=None, s=2):
    """Draw N s×s dots in one numpy pass (10,000 dots/frame is fine). Returns a NEW image."""
    a = np.asarray(p).copy(); h, w = a.shape[:2]
    xs = xs.astype(int); ys = ys.astype(int)
    m = (xs >= 0) & (xs < w - s) & (ys >= 0) & (ys < h - s)
    xs, ys, cols = xs[m], ys[m], cols[m]
    al = alpha[m] if alpha is not None else np.ones(len(xs))
    for dy in range(s):
        for dx in range(s):
            Y, X = ys + dy, xs + dx
            a[Y, X, :3] = (a[Y, X, :3].astype(float) * (1 - al[:, None]) + cols * al[:, None]).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

class Swarm:
    """N jittering dots in a rect. swarm.xy(rect, t) -> xs, ys; .col is Nx3. Collapse/burst by lerping toward targets with vexpo."""
    def __init__(self, n=10000, seed=7, palette=TEAM):
        r = np.random.default_rng(seed)
        self.n, self.u, self.v, self.ph = n, r.random(n), r.random(n), r.random(n) * 6.28
        self.col = np.array(palette, float)[r.integers(0, len(palette), n)] * 0.8 + 255 * 0.2
        self.delay = r.random(n) * 0.3
    def xy(self, rect, t):
        x0, y0, w, h = rect
        return x0 + self.u * w + np.sin(t * 1.7 + self.ph) * 2.5, y0 + self.v * h + np.cos(t * 1.3 + self.ph) * 2.5

# ------------------------------------------------------------------ flow chart: Goal -> N lanes -> Solution
def flow_lanes(goal, sol, offsets, lanes=6, spread=15, n=80):
    """Lens-shaped bundles (like the DevDay agent-team slide). offsets = peak y offset per team. Returns [(team, pts)]."""
    u = np.linspace(0, 1, n); out = []
    for tm, Y0 in enumerate(offsets):
        for ln in range(lanes):
            Y = Y0 + (ln - (lanes - 1) / 2) * spread
            out.append((tm, list(zip(goal[0] + u * (sol[0] - goal[0]), goal[1] + Y * np.sin(np.pi * u) ** 0.75))))
    return out

def draw_flow(d, lanes, t, k, cols=TEAM, particles=2):
    """line-draw each lane (cascade by team/lane), then stream particles along the drawn part"""
    for i, (tm, pts) in enumerate(lanes):
        ln = i % 6
        e = expo((k - 0.05 - ln * 0.02 - tm * 0.06) / 0.75); n = int(len(pts) * e)
        if n > 1: d.line(pts[:n], fill=cols[tm] + (140,), width=3)
        for m in range(particles):
            uu = (t * 0.6 + m / particles + i * 0.137) % 1; idx = int(uu * (len(pts) - 1))
            if idx < n - 1:
                x, y = pts[idx]; d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=lerpc(cols[tm], (255, 255, 255), 0.4) + (255,))

# ------------------------------------------------------------------ verbatim receipt card with marker sweeps
_QL = {}
def _norm(w): return "".join(ch for ch in w.lower() if ch.isalnum())
def quote_card(t, text, marks, w=960, size=46, lh=64, logo_img=None, org="OpenAI", meta="", source=""):
    """Source text VERBATIM on a black card; marks=[(phrase, t_on)] sweep a yellow marker word by word,
    marked words flip to ink, the rest dims once a mark is active (rpn style)."""
    f = font(SFD("Medium"), size)
    key = (text, w, size)
    if key not in _QL:
        lay, x, y, sp = [], 0, 0, f.getlength(" ")
        for wd in text.split(" "):
            wl = f.getlength(wd)
            if x > 0 and x + wl > w - 100: x = 0; y += lh
            lay.append([wd, x, y, wl]); x += wl + sp
        _QL[key] = (lay, y + lh, sp)
    lay, th, sp = _QL[key]
    h = 120 + th + 80
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 28, fill=(6, 6, 7, 255), outline=(255, 255, 255, 70), width=2)
    tx = 50
    if logo_img is not None: P(p, logo_img, 50, 60 - logo_img.height / 2); tx = 104
    fo = font(SFD("Semibold"), 34)
    d.text((tx, 60), org, font=fo, fill=WHITE, anchor="lm")
    if meta: d.text((tx + fo.getlength(org) + 22, 60), meta, font=font(SFT("Medium"), 28), fill=(150, 150, 156), anchor="lm")
    norm = [_norm(x[0]) for x in lay]
    state = [0.0] * len(lay); act = 0
    for phrase, ton in marks:
        ph = [_norm(x) for x in phrase.split()]
        s = next(i for i in range(len(norm)) if norm[i:i + len(ph)] == ph)
        pr = expo((t - ton) / 0.7) if t > ton else 0
        act = max(act, pr)
        tot = sum(lay[s + j][3] for j in range(len(ph))); c = 0
        for j in range(len(ph)):
            wl = lay[s + j][3]; state[s + j] = clamp((pr * tot - c) / wl); c += wl
    mx, my = 50, 120
    for (wd, x, y, wl), v in zip(lay, state):
        if v > 0:
            d.rectangle((mx + x - 4, my + y + 2, mx + x + (wl + (sp if v >= 1 else 0)) * v + 2, my + y + size * 1.18), fill=HILITE + (255,))
    for (wd, x, y, wl), v in zip(lay, state):
        d.text((mx + x, my + y), wd, font=f, fill=INK if v > 0.5 else lerpc((240, 240, 240), (125, 125, 130), act * 0.7))
    if source: d.text((50, h - 46), source, font=font(SFT("Medium"), 24), fill=(120, 120, 126), anchor="lm")
    return p

# ------------------------------------------------------------------ marker on a real screenshot (white text on dark page)
def marked_copy(img, rect):
    """Pre-render the 'highlighted' version of a dark-page screenshot region: yellow marker, text flipped to ink."""
    a = np.asarray(img.convert("RGB")).astype(float); x0, y0, x1, y1 = rect
    Lm = a[y0:y1, x0:x1].mean(axis=2, keepdims=True) / 255
    b = a.copy(); b[y0:y1, x0:x1] = np.array(HILITE, float) * (1 - Lm) + np.array(INK, float) * Lm
    return Image.fromarray(b.astype(np.uint8))

def sweep(img, img_marked, rect, p):
    """left-to-right marker sweep, p in 0..1"""
    out = img.copy()
    if p > 0:
        xe = int(rect[0] + (rect[2] - rect[0]) * p)
        if xe > rect[0]: out.paste(img_marked.crop((rect[0], rect[1], xe, rect[3])), (rect[0], rect[1]))
    return out
