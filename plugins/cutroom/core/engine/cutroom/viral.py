"""Viral reel kit (2026-10-21), from the 10 fps study of the Claude Code reels in reel-templates/styles.md.

What makes those edits feel fast: the pauses are cut out (jump cuts), the camera punches in and out on hard
cuts every phrase or two, the caption style changes from section to section, stickers and chips pop with a
small overshoot, keywords blur in, and a few loud transitions (whip, glitch, crack, flash, circle) mark the
turns. Sound follows the picture: a whoosh on a whip, an impact on a slam, taps under typing, a ding on a tick.

    from cutroom import viral as V
    tl = V.Timeline.from_audio(voice, total)    # jump-cut plan: source <-> output time
    cv = V.shot(frame, z=1.3, fy=0.34)          # punch-in, face held at the same height
    V.karaoke(cv, t, tl.map_words(words))       # one of seven caption styles
    cv = V.glitch(cv, t - t_cut)                # transitions work on the finished frame

Everything depends only on the time passed in, so it is chunk-safe for parallel.render.
"""
import math, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from .core import W, H, FPS, font, display, MONO, clamp, expo, cubic, inout, text_img, Reader, dilate
from .blocks import back, sit, emoji_img, drop_shadow, place, ss

HEAVY = 800
BOLD = 700
SEMI = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 216, 0)
RED = (232, 44, 48)
ORANGE = (255, 140, 66)
GREEN = (52, 199, 89)
CLAUDE = (217, 119, 87)
UPCOMING = (150, 150, 156)


def clean(w_):
    return w_.strip(",.!?\"'")


def key_of(w_):
    return "".join(c for c in w_.lower() if c.isalnum())


# ------------------------------------------------------------------ jump cuts
class Timeline:
    """Which stretches of the source survive. Output time t plays source time src(t)."""

    def __init__(self, segs):
        self.segs = [(float(a), float(b)) for a, b in segs if b - a > 0.02]
        self.starts, o = [], 0.0
        for a, b in self.segs:
            self.starts.append(o)
            o += b - a
        self.duration = o
        self.cuts = self.starts[1:]

    @classmethod
    def from_audio(cls, voice, total, sr=48000, floor_db=None, min_gap=0.22, pad=0.07, hop=0.01):
        """floor_db: speech threshold below the loudest 10ms. None sets it 8 dB above the room tone (the
        quietest 15%), between -40 and -20."""
        n = int(sr * hop)
        m = len(voice) // n
        rms = np.sqrt((voice[: m * n].reshape(m, n) ** 2).mean(1)) + 1e-9
        db = 20 * np.log10(rms / rms.max())
        if floor_db is None:
            floor_db = clamp(float(np.percentile(db, 15)) + 8, -40, -20)
        talk = db > floor_db
        segs, start = [], None
        for i, v in enumerate(talk):
            if v and start is None:
                start = i
            if not v and start is not None:
                segs.append([start * hop, i * hop])
                start = None
        if start is not None:
            segs.append([start * hop, m * hop])
        merged = []
        for a, b in segs:
            if merged and a - merged[-1][1] < min_gap:
                merged[-1][1] = b
            else:
                merged.append([a, b])
        if not merged:
            return cls([(0, total)])
        merged = [[max(0.0, a - pad), min(total, b + pad)] for a, b in merged]
        merged[-1][1] = min(total, merged[-1][1] + 0.35)
        return cls(merged)

    def src(self, t):
        for (a, b), o in zip(self.segs, self.starts):
            if t < o + (b - a):
                return a + max(0.0, t - o)
        return self.segs[-1][1]

    def out(self, ts):
        for (a, b), o in zip(self.segs, self.starts):
            if ts < b:
                return o + max(0.0, ts - a)
        return self.duration

    def map_words(self, words):
        return [{"w": w_["w"], "s": self.out(w_["s"]), "e": self.out(w_["e"]), "src": w_["s"]} for w_ in words]

    def cut_audio(self, voice, sr=48000, fade=0.006):
        f = int(fade * sr)
        parts = []
        for a, b in self.segs:
            x = voice[int(a * sr): int(b * sr)].copy()
            if len(x) > 2 * f:
                x[:f] *= np.linspace(0, 1, f)
                x[-f:] *= np.linspace(1, 0, f)
            parts.append(x)
        return np.concatenate(parts) if parts else voice


class JumpReader:
    """Frames of a source read through a Timeline: skips forward over the cut pauses."""

    REOPEN = 45

    def __init__(self, path, tl, t0, w=W, h=H):
        self.tl, self.path, self.w, self.h = tl, path, w, h
        first = round(tl.src(t0) * FPS)
        self.r = Reader(path, w, h, start=first / FPS)
        self.i = first - 1

    def at(self, t):
        target = round(self.tl.src(t) * FPS)
        if target - self.i > self.REOPEN:
            self.r.close()
            self.r = Reader(self.path, self.w, self.h, start=target / FPS)
            self.i = target - 1
        while self.i < target:
            self.r.next()
            self.i += 1
        return self.r.last

    def close(self):
        self.r.close()


# ------------------------------------------------------------------ camera
def shot(frame, z=1.0, fy=0.34, dx=0.0, dy=0.0, out=(W, H)):
    """punch-in: zoom z with the face (at height fy in the source) held at the same screen height.
    dx/dy (px) shift the crop for shake; they only move the picture when z > 1."""
    ow, oh = out
    iw, ih = frame.size
    s = max(ow / iw, oh / ih) * z
    cw, ch = ow / s, oh / s
    x0 = clamp((iw - cw) / 2 - dx / s, 0, iw - cw)
    y0 = clamp((ih - ch) * fy - dy / s, 0, ih - ch)
    box = (x0, y0, x0 + cw, y0 + ch)
    if frame.mode == "L":
        return frame.resize((ow, oh), Image.BICUBIC, box=box)
    if (iw, ih) == (ow, oh) and (cw, ch) == (iw, ih):
        return frame.convert("RGBA")
    return frame.convert("RGB").resize((ow, oh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")


def punch(u, z0, z1, d=0.12):
    """snap zoom: from z0 to z1 in d seconds (expo), so a hard punch-in still reads as a move."""
    return z1 if u >= d else z0 + (z1 - z0) * expo(clamp(u / d))


def blur_band(canvas, cy, h=240, radius=28):
    """soften a horizontal band (hides text burned into the footage)."""
    y0, y1 = int(cy - h / 2), int(cy + h / 2)
    band = canvas.crop((0, y0, W, y1)).filter(ImageFilter.GaussianBlur(radius))
    m = Image.new("L", band.size, 255)
    edge = 40
    for i in range(edge):
        v = int(255 * i / edge)
        ImageDraw.Draw(m).line([(0, i), (W, i)], fill=v)
        ImageDraw.Draw(m).line([(0, band.height - 1 - i), (W, band.height - 1 - i)], fill=v)
    canvas.paste(band, (0, y0), m)


# ------------------------------------------------------------------ transitions (u = seconds since the cut)
def whip(canvas, u, d=0.2, direction=1):
    """whip pan into the new shot: six offset copies averaged, strongest mid-move, gone after d."""
    if not 0 <= u < d:
        return canvas
    amt = math.sin(math.pi * u / d) * 160
    if amt < 4:
        return canvas
    a = np.asarray(canvas.convert("RGB"), np.float32)
    acc = np.zeros_like(a)
    for s in range(6):
        acc += np.roll(a, int(direction * amt * (s / 5 - 0.5)), 1)
    return Image.fromarray((acc / 6).astype(np.uint8)).convert("RGBA")


def glitch(canvas, u, d=0.1, seed=3):
    """digital glitch: RGB split plus torn horizontal bands, for about three frames either side of the cut."""
    if not -d <= u < d:
        return canvas
    a = 1 - abs(u) / d
    rng = np.random.default_rng(seed * 1000 + int(round(u * FPS)) + 50)
    arr = np.asarray(canvas.convert("RGB")).copy()
    sh = int(26 * a)
    arr[..., 0] = np.roll(arr[..., 0], sh, 1)
    arr[..., 2] = np.roll(arr[..., 2], -sh, 1)
    for _ in range(int(4 + 8 * a)):
        y = int(rng.integers(0, H - 40))
        h_ = int(rng.integers(12, 140))
        arr[y: y + h_] = np.roll(arr[y: y + h_], int(rng.integers(-160, 160) * a), 1)
    if rng.random() < 0.5 * a:
        y = int(rng.integers(0, H - 60))
        arr[y: y + 30] = np.clip(arr[y: y + 30].astype(np.int16) + 90, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


def flash(canvas, u, d=0.12, color=WHITE):
    if not 0 <= u < d:
        return canvas
    ov = Image.new("RGBA", canvas.size, color + (int(235 * (1 - u / d) ** 1.6),))
    return Image.alpha_composite(canvas, ov)


def zoom_in(canvas, u, d=0.16, z=1.3):
    """zoom transition: the new shot lands from z down to 1 with a radial smear."""
    if not 0 <= u < d:
        return canvas
    p = expo(u / d)
    zz = z - (z - 1) * p
    cw, ch = W / zz, H / zz
    box = ((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)
    im = canvas.convert("RGB").resize((W, H), Image.BICUBIC, box=box)
    if p < 0.8:
        bz = zz * 1.06
        cw, ch = W / bz, H / bz
        b2 = canvas.convert("RGB").resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        im = Image.blend(im, b2.filter(ImageFilter.GaussianBlur(6)), 0.5 * (1 - p))
    return im.convert("RGBA")


@lru_cache(4)
def _crack_lines(seed, cx, cy):
    rng = np.random.default_rng(seed)
    lines = []
    for i in range(9):
        ang = i / 9 * math.tau + rng.uniform(-0.25, 0.25)
        pts, x, y = [(cx, cy)], cx, cy
        for _ in range(7):
            step = rng.uniform(70, 190)
            ang += rng.uniform(-0.5, 0.5)
            x, y = x + math.cos(ang) * step, y + math.sin(ang) * step
            pts.append((x, y))
        lines.append(pts)
    return lines


def crack(canvas, u, d=0.4, cx=540, cy=820, seed=5):
    """the screen cracks from a point: white fracture lines, a bright first frame, the pieces nudge apart."""
    if not 0 <= u < d:
        return canvas
    a = 1 - (u / d) ** 2
    im = canvas.copy()
    if u < 0.1:
        sh = int(10 * (1 - u / 0.1))
        left = im.crop((0, 0, W // 2, H))
        im.paste(left, (-sh, sh // 2))
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for pts in _crack_lines(seed, cx, cy):
        dr.line(pts, fill=(0, 0, 0, int(140 * a)), width=9, joint="curve")
        dr.line(pts, fill=(255, 255, 255, int(255 * a)), width=4, joint="curve")
    im = Image.alpha_composite(im, ov)
    return flash(im, u, 0.06)


def circle(canvas, u, d=0.24, cx=540, cy=820, color=BLACK):
    """circle wipe: the new shot opens out of a growing circle."""
    if not 0 <= u < d:
        return canvas
    r = expo(u / d) * math.hypot(W, H)
    m = Image.new("L", (W // 4, H // 4), 0)
    ImageDraw.Draw(m).ellipse(((cx - r) / 4, (cy - r) / 4, (cx + r) / 4, (cy + r) / 4), fill=255)
    m = m.resize((W, H), Image.BILINEAR)
    bg = Image.new("RGBA", (W, H), color + (255,))
    return Image.composite(canvas, bg, m)


TRANSITIONS = {"whip": whip, "glitch": glitch, "flash": flash, "zoom": zoom_in, "crack": crack, "circle": circle}


def transition(canvas, name, u, **kw):
    return TRANSITIONS[name](canvas, u, **kw) if name else canvas


# ------------------------------------------------------------------ text
@lru_cache(2048)
def word_img(txt, size, fill=WHITE, weight=HEAVY, stroke=0, shadow=True, box=None, box_pad=(22, 6), rot=0.0):
    """one word (or line) as RGBA: optional black stroke, soft shadow, and a rounded colour box behind it."""
    f = display(size, weight)
    l, t, r, b = f.getbbox(txt, stroke_width=stroke)
    px, py = (box_pad if box else (stroke + 4, stroke + 4))
    w_, h_ = r - l + px * 2, int(size * 1.0) + py * 2
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if box:
        im = ss(lambda dd, s: dd.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), int(size * 0.18) * s, fill=box + (255,)), w_, h_)
        d = ImageDraw.Draw(im)
    d.text((w_ / 2, h_ / 2), txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=BLACK)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if shadow:
        sh = drop_shadow(im, 10, 150)
        out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 5))
        out.alpha_composite(im, (sh.pad, sh.pad))
        return out
    return im


def line_img(parts, gap=0.26):
    """[(img, size)] laid left to right on a shared centre line."""
    size = max(s for _, s in parts)
    sp = int(size * gap) - 64
    w_ = sum(im.width for im, _ in parts) + sp * (len(parts) - 1)
    h_ = max(im.height for im, _ in parts)
    out = Image.new("RGBA", (max(1, w_), h_), (0, 0, 0, 0))
    x = 0
    for im, _ in parts:
        out.alpha_composite(im, (x, (h_ - im.height) // 2))
        x += im.width + sp
    return out


def fit(im, width=980):
    return im if im.width <= width else im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)


def groups(words, n=3, gap=0.35, hold=0.6):
    """words -> [(words, t0, t1)] phrases of up to n words, split on pauses; each holds until the next."""
    out, cur = [], []
    for w_ in words:
        if cur and (len(cur) >= n or w_["s"] - cur[-1]["e"] > gap or cur[-1]["w"][-1:] in ".?!"):
            out.append(cur)
            cur = []
        cur.append(w_)
    if cur:
        out.append(cur)
    return [(g, g[0]["s"], out[i + 1][0]["s"] if i + 1 < len(out) else g[-1]["e"] + hold) for i, g in enumerate(out)]


def _active(gs, t):
    for g, t0, t1 in gs:
        if t0 <= t < t1:
            return g, t - t0
    return None, 0


def _spoken(g, t):
    return max([i for i, w_ in enumerate(g) if w_["s"] <= t] or [0])


def _blur_in(im, u, d=0.07, r=14):
    return im if u >= d else im.filter(ImageFilter.GaussianBlur(r * (1 - u / d)))


def karaoke(canvas, t, words, cy=1250, size=92, n=3, box=RED):
    """@thecoachbraydon: heavy white caps with a black edge; a red box jumps to the word being said."""
    g, u = _active(groups(words, n), t)
    if not g:
        return
    j = _spoken(g, t)
    parts = [(word_img(clean(w_["w"]).upper(), size, WHITE, HEAVY, 6 if i != j else 0, i != j, box if i == j else None), size)
             for i, w_ in enumerate(g)]
    place(canvas, fit(line_img(parts)), W / 2, cy, 0.9 + 0.1 * back(u / 0.1, 1.6))


def boxed(canvas, t, words, keys=(), cy=1250, size=78, n=4, box=YELLOW):
    """@simonbeard: a white heavy phrase; the keyword sits black on a tilted yellow box. The phrase pops in."""
    g, u = _active(groups(words, n), t)
    if not g:
        return
    parts = []
    for w_ in g:
        c = clean(w_["w"])
        if key_of(c) in keys:
            parts.append((word_img(c, int(size * 1.12), BLACK, HEAVY, 0, True, box, (24, 10), -3.0), size))
        else:
            parts.append((word_img(c, size, WHITE, HEAVY, 6, True), size))
    place(canvas, fit(line_img(parts)), W / 2, cy, 0.78 + 0.22 * back(u / 0.16, 1.8))


def one_word(canvas, t, words, keys=(), cy=1150, size=150, color=YELLOW):
    """one word at a time in giant caps; keywords bigger and yellow and slam in from large, the rest pop up."""
    w_ = next((x for x in reversed(words) if x["s"] <= t), None)
    if w_ is None or t > w_["e"] + 0.5:
        return
    c = clean(w_["w"]).upper()
    hit = key_of(c) in keys
    im = fit(word_img(c, int(size * (1.25 if hit else 1)), color if hit else WHITE, HEAVY, 8, True), 1000)
    u = t - w_["s"]
    s = (1.35 - 0.35 * expo(u / 0.08)) if hit else (0.7 + 0.3 * back(u / 0.12, 1.8))
    place(canvas, im, W / 2, cy, s)


def pill(canvas, t, words, cy=1270, size=50, n=5):
    """@zachdoesai_: plain sentence on a dark translucent pill. Hard swaps, no motion."""
    g, _ = _active(groups(words, n), t)
    if not g:
        return
    im = _pill_img(" ".join(clean(w_["w"]) for w_ in g), size)
    place(canvas, im, W / 2, cy)


@lru_cache(64)
def _pill_img(txt, size):
    f = display(size, SEMI)
    w_, h_ = int(f.getlength(txt)) + 64, int(size * 1.7)
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), h_ // 2 * s, fill=(24, 24, 26, 215)), w_, h_)
    ImageDraw.Draw(im).text((w_ / 2, h_ / 2), txt, font=f, fill=WHITE, anchor="mm")
    return fit(im, 1000)


def stack2x(canvas, t, words, keys=(), cy=1200, size=64, n=4, color=YELLOW):
    """@tenfoldmarc: the phrase on one line, its keyword on its own line at twice the size, blurred in."""
    g, u = _active(groups(words, n), t)
    if not g:
        return
    ki = next((i for i, w_ in enumerate(g) if key_of(clean(w_["w"])) in keys), None)
    rest = " ".join(clean(w_["w"]) for i, w_ in enumerate(g) if i != ki)
    if rest:
        place(canvas, fit(word_img(rest, size, WHITE, BOLD, 5, True)), W / 2, cy - (size * 0.95 if ki is not None else 0))
    if ki is not None:
        k_ = g[ki]
        if t >= k_["s"]:
            big = fit(word_img(clean(k_["w"]).upper(), int(size * 2.2), color, HEAVY, 8, True), 1000)
            place(canvas, _blur_in(big, t - k_["s"]), W / 2, cy + size * 0.75)


def serif_key(canvas, t, words, keys=(), cy=1250, size=72, n=4, color=ORANGE):
    """@iamajene / @duncanrogoff: bold sans words, the keyword in an orange italic serif, blurred in."""
    g, u = _active(groups(words, n), t)
    if not g:
        return
    parts = []
    for w_ in g:
        c = clean(w_["w"])
        if key_of(c) in keys:
            im = _serif_word(c, int(size * 1.25), color)
            parts.append((_blur_in(im, t - w_["s"]) if t >= w_["s"] else Image.new("RGBA", im.size), size))
        else:
            parts.append((word_img(c, size, WHITE, BOLD, 0, True), size))
    place(canvas, fit(line_img(parts, 0.3)), W / 2, cy)


@lru_cache(64)
def _serif_word(txt, size, color):
    f = sit(size, 560)
    l, t, r, b = f.getbbox(txt)
    im = Image.new("RGBA", (r - l + 30, int(size * 1.3)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((im.width / 2, im.height / 2), txt, font=f, fill=color, anchor="mm")
    sh = drop_shadow(im, 10, 150)
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 5))
    out.alpha_composite(im, (sh.pad, sh.pad))
    return out


def grey_next(canvas, t, words, cy=1250, size=60, n=6, upcoming=UPCOMING):
    """@charliehills: the whole phrase is up; said words are white, the ones still coming are grey."""
    g, _ = _active(groups(words, n), t)
    if not g:
        return
    half = (len(g) + 1) // 2
    rows = [g[:half], g[half:]] if len(g) > 3 else [g]
    for r_i, row in enumerate(rows):
        parts = [(word_img(clean(w_["w"]), size, WHITE if w_["s"] <= t else upcoming, BOLD, 0, True), size) for w_ in row]
        place(canvas, fit(line_img(parts, 0.3)), W / 2, cy + (r_i - (len(rows) - 1) / 2) * size * 1.2)


CAPTIONS = {"karaoke": karaoke, "boxed": boxed, "one_word": one_word, "pill": pill, "stack2x": stack2x,
            "serif_key": serif_key, "grey_next": grey_next}


# ------------------------------------------------------------------ stickers
def pop(canvas, im, k, cx, cy, rot=0.0, d=0.16, out=None, shadow=(0, 14, 22, 150)):
    """scale-pop with overshoot (on in about five frames); shrinks away over 0.08s after `out`."""
    if im is None or k < 0 or (out is not None and k > out + 0.08):
        return
    s = 0.35 + 0.65 * back(k / d, 1.9)
    if out is not None and k > out:
        s *= 1 - (k - out) / 0.08
    place(canvas, im, cx, cy, s, rot, clamp(k / 0.04), shadow)


def slam(canvas, im, k, cx, cy, rot=0.0, d=0.09, out=None):
    """lands from 2x in three frames (pair it with an impact and shake)."""
    if im is None or k < 0 or (out is not None and k > out):
        return
    place(canvas, im, cx, cy, 2.0 - expo(k / d), rot, clamp(k / 0.03), (0, 16, 26, 170))


@lru_cache(64)
def chip(text, bg=WHITE, fg=BLACK, size=48, emoji=None):
    """rounded label chip, heavy text, optional colour emoji on the left."""
    f = display(size, HEAVY)
    e = emoji_img(emoji, int(size * 1.1)) if emoji else None
    ew = e.width + 16 if e else 0
    w_, h_ = int(f.getlength(text)) + 64 + ew, int(size * 1.75)
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), int(h_ * 0.32) * s, fill=bg + (255,)), w_, h_)
    if e:
        im.alpha_composite(e, (32, (h_ - e.height) // 2))
    ImageDraw.Draw(im).text((32 + ew + (w_ - 64 - ew) / 2, h_ / 2), text, font=f, fill=fg, anchor="mm")
    return im


@lru_cache(32)
def big_emoji(ch, size=220):
    return emoji_img(ch, size)


@lru_cache(16)
def card(lines, w=880, size=34, title=None, bg=(18, 18, 20), mono=True):
    """dark terminal-style card with a title row."""
    from .core import MONO
    f = font(MONO, size) if mono else display(size, SEMI)
    lh = int(size * 1.6)
    top = 90 if title else 40
    h_ = top + lh * len(lines) + 40
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 30 * s, fill=bg + (245,), outline=(70, 70, 76, 255), width=2 * s), w, h_)
    d = ImageDraw.Draw(im)
    if title:
        for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            d.ellipse((34 + i * 34, 34, 54 + i * 34, 54), fill=c)
        d.text((w / 2, 44), title, font=display(28, SEMI), fill=(170, 170, 176), anchor="mm")
    for i, (col, txt) in enumerate(lines):
        d.text((44, top + i * lh), txt, font=f, fill=col)
    return im


def typed(canvas, k, lines, cx, cy, cps=40, out=None, **kw):
    """a card whose lines type themselves out, popping in first."""
    if k < 0 or (out is not None and k > out + 0.08):
        return
    shown, budget = [], k * cps
    for col, txt in lines:
        n = int(clamp(budget, 0, len(txt)))
        shown.append((col, txt[:n]))
        budget -= len(txt)
    pop(canvas, card(tuple(shown), **kw), k, cx, cy, out=out)


# ------------------------------------------------------------------ the reel-edit look (skills/reel-edit)
GOLD = (255, 214, 92)
INK = (18, 18, 18)
BLUE = (38, 92, 255)
SLAB = {"orange": ((255, 98, 20), INK), "ink": (INK, WHITE), "gold": (GOLD, INK), "white": (WHITE, INK),
        "blue": (BLUE, WHITE), "claude": (CLAUDE, WHITE)}


SYMBOLS = next((p for p in ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Menlo.ttc",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(p)), None)
_glyphs = {}


def _has(f, ch):
    k = (id(f), ch)
    if k not in _glyphs:
        _glyphs[k] = ch == " " or bytes(f.getmask(ch)) != bytes(f.getmask("\U000F0000"))
    return _glyphs[k]


def _say(d, xy, text, f, fill):
    """text centred on xy; any character the font lacks (✓, ✂…) is drawn from a symbol font."""
    runs = []
    for ch in text:
        own = SYMBOLS is None or _has(f, ch)
        if runs and runs[-1][0] == own:
            runs[-1][1] += ch
        else:
            runs.append([own, ch])
    fonts = [f if own else font(SYMBOLS, int(f.size * 0.9)) for own, _ in runs]
    widths = [ff.getlength(txt) for ff, (_, txt) in zip(fonts, runs)]
    x = xy[0] - sum(widths) / 2
    for ff, (_, txt), wd in zip(fonts, runs, widths):
        d.text((x, xy[1]), txt, font=ff, fill=fill, anchor="lm")
        x += wd


def _rrect(w, h, r, fill):
    return ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), r * s, fill=fill), w, h)


def _soft(im, blur=18, alpha=90, dy=10):
    sh = drop_shadow(im, blur, alpha)
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy))
    out.alpha_composite(im, (sh.pad, sh.pad))
    return out


def pop_caps(canvas, t, words, cy=1470, n=3, color=GOLD):
    """heavy white caps with a black edge, three words at a time; each word pops in as it's said and the
    one being said turns gold. Shrinks to fit the width."""
    g, _ = _active(groups(words, n), t)
    if not g:
        return
    toks = [clean(w_["w"]).upper() for w_ in g]
    size, gap = 96, 26
    while True:
        f = display(size, 900)
        widths = [f.getlength(x) for x in toks]
        if sum(widths) + gap * (len(toks) - 1) < 940 or size < 50:
            break
        size -= 6
    x = W / 2 - (sum(widths) + gap * (len(toks) - 1)) / 2
    for w_, tok, wd in zip(g, toks, widths):
        if t >= w_["s"] - 0.02:
            hot = w_["s"] <= t < w_["e"] + 0.05
            im = _stroked(tok, size, color if hot else WHITE)
            place(canvas, im, x + wd / 2, cy, 0.7 + 0.3 * back((t - w_["s"]) / 0.12))
        x += wd + gap


@lru_cache(512)
def _stroked(tok, size, fill):
    f = display(size, 900)
    l, t, r, b = f.getbbox(tok, stroke_width=10)
    im = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - l, 10 - t), tok, font=f, fill=fill, stroke_width=10, stroke_fill=BLACK)
    return im


def serif_caps(canvas, t, words, keys=(), cy=1460, n=3, color=GOLD):
    """a bold sans phrase with its keywords in a big gold italic serif; the whole line blurs in and rises."""
    gs = groups(words, n)
    g, u = _active(gs, t)
    if not g:
        return
    im = _serif_line(tuple(clean(w_["w"]) for w_ in g), tuple(sorted(keys)), color)
    p = clamp(u / 0.18)
    if p < 1:
        im = im.filter(ImageFilter.GaussianBlur(14 * (1 - p)))
    place(canvas, im, W / 2, cy - 30 + 20 * (1 - cubic(p)), 1.0, 0.0, min(1, p * 1.5))


@lru_cache(128)
def _serif_line(toks, keys, color):
    fs, fk = display(64, 700), sit(96, 560)
    marks = [key_of(x) in keys for x in toks]
    widths = [(fk if k else fs).getlength(x) for x, k in zip(toks, marks)]
    gap = 20
    lay = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = W / 2 - (sum(widths) + gap * (len(toks) - 1)) / 2
    for tok, k, wd in zip(toks, marks, widths):
        d.text((x, 160), tok, font=fk if k else fs, fill=color if k else WHITE, anchor="ls")
        x += wd + gap
    return fit(_soft(lay, 10, 200, 0), 1060)


def sticker_caps(canvas, t, words, cy=1800):
    """one word at a time, lower case on a white sticker that tilts left, then right, with each new word."""
    w_ = next((x for x in reversed(words) if x["s"] <= t + 0.02), None)
    if w_ is None or t > w_["e"] + 0.6:
        return
    i = words.index(w_)
    im = _sticker(clean(w_["w"]).lower(), -3 + 6 * (i % 2))
    place(canvas, im, W / 2, cy, 0.85 + 0.15 * back((t - w_["s"]) / 0.1))


@lru_cache(256)
def _sticker(tok, rot):
    f = display(84, HEAVY)
    wd = int(f.getlength(tok)) + 60
    box = _rrect(wd, 120, 18, WHITE + (255,))
    ImageDraw.Draw(box).text((wd / 2, 62), tok, font=f, fill=INK, anchor="mm")
    return _soft(box.rotate(rot, Image.BICUBIC, expand=True), 16, 90, 8)


CAPTIONS.update({"pop": pop_caps, "serif": serif_caps, "sticker": sticker_caps})


def darken(canvas, amt):
    """the frame dimmed (up to 45%) so a word behind the person reads."""
    if amt <= 0:
        return canvas
    a = np.asarray(canvas.convert("RGB"), np.float32) * (1 - 0.45 * clamp(amt))
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


def person(frame, mask):
    p = frame.convert("RGBA").copy()
    p.putalpha(mask.convert("L").resize(p.size))
    return p


def big_word(k, txt, size=330, color=WHITE, cy=700, sub=None, sub_color=GOLD):
    """a full-frame layer: a giant word scaling down from 1.25 with a blur-in, an italic serif line above it.
    Draw it, then the person over it (behind)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = clamp(k / 0.22)
    f = display(size, 900)
    while f.getlength(txt) > 1000 and size > 60:
        size -= 10
        f = display(size, 900)
    im = text_img(txt, f, fill=color)
    sc = 1.25 - 0.25 * cubic(p)
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BICUBIC)
    if p < 1:
        im = im.filter(ImageFilter.GaussianBlur(18 * (1 - p)))
    place(lay, im, W / 2, cy, 1.0, 0.0, min(1, p * 1.4))
    if sub:
        place(lay, text_img(sub, sit(64, 520), fill=sub_color), W / 2, cy - size * 0.62, 1.0, 0.0, clamp((k - 0.1) / 0.2))
    return lay


def behind(canvas, layer, cutout):
    canvas.alpha_composite(layer)
    canvas.alpha_composite(cutout)


def slab(k, word, bg=(255, 98, 20), fg=INK):
    """a full-screen word on a flat colour, landing from 1.15x in three frames."""
    cv = Image.new("RGBA", (W, H), bg + (255,))
    im = text_img(word, display(260, 900), fill=fg)
    im = fit(im, 1000)
    place(cv, im, W / 2, 900, 1.15 - 0.15 * cubic(k / 0.1))
    return cv


def split(frame, t, words, k, fy=0.34, title="audio.json", sub="every word, with its time", mark=None, chip_k=None,
          chip_text="✂ cut the gaps"):
    """top half: a transcript card sliding down, each word lighting up as it's said (mark gets a highlight and,
    from chip_k, a chip). Bottom half: the face."""
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    pan = Image.new("RGBA", (W, 960), (244, 245, 249, 255))
    card = _rrect(940, 760, 40, WHITE + (255,))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((44, 44, 100, 100), 14, fill=BLUE)
    d.text((124, 56), title, font=display(46, 700), fill=INK, anchor="lm")
    d.text((124, 96), sub, font=display(26, 500), fill=(140, 140, 150), anchor="lm")
    fw, ft = display(56, 700), font(MONO, 24)
    for i, w_ in enumerate(words[:12]):
        col, row = i // 6, i % 6
        x, y = 70 + col * 440, 190 + row * 92
        tok = clean(w_["w"])
        while fw.getlength(tok) > 300 and len(tok) > 4:
            tok = tok[:-2] + "…"
        said, now = t >= w_["s"], w_["s"] <= t < w_["e"] + 0.05
        d.text((x, y), f"{w_.get('src', w_['s']):5.2f}", font=ft, fill=(170, 170, 180), anchor="lm")
        if mark and key_of(tok) == mark and said:
            d.rounded_rectangle((x + 92, y - 36, x + 104 + fw.getlength(tok), y + 36), 12, fill=(255, 236, 200))
        d.text((x + 100, y), tok, font=fw, fill=BLUE if now else (INK if said else (205, 205, 212)), anchor="lm")
    if chip_k is not None and chip_k >= 0:
        c = _rrect(330, 64, 32, (255, 98, 20, 255))
        _say(ImageDraw.Draw(c), (165, 33), chip_text, display(30, 700), WHITE)
        place(card, c, 725, 672, 0.8 + 0.2 * back(chip_k / 0.2))
    place(pan, _soft(card, 24, 70, 12), W / 2, 480 - 700 * (1 - cubic(k / 0.3)))
    cv.alpha_composite(pan, (0, 0))
    iw, ih = frame.size
    cw, ch = iw * 0.8, iw * 0.8 * 960 / W
    cy = clamp(fy * ih + ch * 0.3, ch / 2, ih - ch / 2)
    face = frame.convert("RGB").resize((W, 960), Image.BICUBIC, box=(iw * 0.1, cy - ch / 2, iw * 0.9, cy + ch / 2))
    cv.alpha_composite(face.convert("RGBA"), (0, 960))
    return cv


def file_card(canvas, k, title, rows, tag=None, cy=360):
    """a white file card (title, optional tag) whose key/value rows fade in one by one; the card blurs in."""
    card = _rrect(820, 120 + 86 * len(rows), 34, (255, 255, 255, 240))
    d = ImageDraw.Draw(card)
    d.text((44, 62), title, font=display(44, 700), fill=INK, anchor="lm")
    if tag:
        d.text((776, 62), tag, font=display(26, 500), fill=(150, 150, 160), anchor="rm")
    for i, (key, val) in enumerate(rows):
        a = clamp((k - 0.15 - 0.28 * i) / 0.15)
        if a > 0:
            y = 150 + 86 * i
            d.text((44, y), key, font=display(34, 500), fill=(130, 130, 140, int(255 * a)), anchor="lm")
            d.text((776, y), val, font=display(36, 700), fill=(18, 18, 18, int(255 * a)), anchor="rm")
    p = clamp((k + 0.1) / 0.25)
    im = _soft(card, 24, 90, 12)
    if p < 1:
        im = im.filter(ImageFilter.GaussianBlur(22 * (1 - p)))
    place(canvas, im, W / 2, cy, 1.0, 0.0, min(1, p * 1.6))


def badge(canvas, k, text, color=GREEN, cy=1270):
    """a rounded pill that pops in with a little overshoot."""
    if k < 0:
        return
    f = display(44, 700)
    w_ = int(f.getlength(text)) + 90
    im = _rrect(w_, 96, 48, color + (255,))
    _say(ImageDraw.Draw(im), (w_ / 2, 50), text, f, WHITE)
    place(canvas, im, W / 2, cy, 0.7 + 0.3 * back(k / 0.18), 0.0, min(1, k / 0.09))


def note(canvas, k, text, saved_k=None, saved="✓ saved to memory", cy=330):
    """a note bubble sliding in from the right with the text typing out; from saved_k a chip pops under it."""
    if k < 0:
        return
    n = int(clamp((k - 0.15) / 0.8) * len(text))
    f = display(50, 500)
    caret = "|" if int(k * 4) % 2 == 0 and n < len(text) else ""
    bw = max(260, int(f.getlength(text)) + 80)
    b = _rrect(bw, 170, 36, (255, 255, 255, 245))
    d = ImageDraw.Draw(b)
    d.text((40, 42), "your note", font=display(26, 500), fill=(150, 150, 160), anchor="lm")
    d.text((40, 110), text[:n] + caret, font=f, fill=INK, anchor="lm")
    p = clamp(k / 0.25)
    place(canvas, _soft(fit(b, 1000), 20, 90, 10), W / 2 + 300 * (1 - cubic(p)), cy, 1.0, 0.0, min(1, p * 2))
    if saved_k is not None and saved_k >= 0:
        sf = display(36, 700)
        cw = int(sf.getlength(saved)) + 80
        c = _rrect(cw, 84, 42, CLAUDE + (255,))
        _say(ImageDraw.Draw(c), (cw / 2, 44), saved, sf, WHITE)
        place(canvas, c, W / 2, cy + 170, 0.7 + 0.3 * back(saved_k / 0.2), 0.0, min(1, saved_k * 10))


def comment_bar(canvas, k, word, typed_k=None, cy=1760):
    """an Instagram-style comment field rising from the bottom; from typed_k the word types in and Post lights up."""
    if k < 0:
        return
    bar = _rrect(960, 120, 60, (20, 20, 24, 235))
    d = ImageDraw.Draw(bar)
    d.ellipse((24, 24, 96, 96), fill=CLAUDE)
    n = int(clamp(typed_k / 0.35) * len(word)) if typed_k is not None and typed_k >= 0 else 0
    d.text((124, 60), word[:n] or "Add a comment…", font=display(44, BOLD if n else 500),
           fill=WHITE if n else (150, 150, 160), anchor="lm")
    d.rounded_rectangle((820, 26, 936, 94), 34, fill=BLUE if n == len(word) else (60, 60, 70))
    d.text((878, 60), "Post", font=display(32, 700), fill=WHITE, anchor="mm")
    p = clamp(k / 0.25)
    place(canvas, bar, W / 2, cy + 200 * (1 - cubic(p)), 1.0, 0.0, min(1, p * 2))


def logo(canvas, k, cx=820, cy=420, out=None):
    """the Claude asterisk on a white tile, popping and untwisting into place."""
    if k < 0 or (out is not None and k > out):
        return
    p = clamp(k / 0.2)
    c = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, 199, 199), 48, fill=WHITE)
    for i in range(12):
        a = i * math.pi / 6
        d.line([(100, 100), (100 + 70 * math.cos(a), 100 + 70 * math.sin(a))], fill=CLAUDE, width=16)
    place(canvas, c, cx, cy, 0.5 + 0.5 * back(p), -12 * (1 - p), 1.0, (0, 10, 18, 90))


class ClipReader:
    """frames of a reference clip by time since it appeared (k); reopens only when k jumps, holds the last frame."""

    def __init__(self, path, w=720, h=1280, start=0.0):
        self.path, self.w, self.h, self.start = path, w, h, start
        self.r, self.i = None, None

    def at(self, k):
        n = int(round(max(0.0, k) * FPS))
        if self.r is None or n < self.i or n > self.i + FPS:
            self.close()
            self.r = Reader(self.path, self.w, self.h, start=self.start + n / FPS)
            self.i = n - 1
        while self.i < n:
            self.r.next()
            self.i += 1
        return self.r.last

    def close(self):
        if self.r:
            self.r.close()
        self.r = None


@lru_cache(8)
def _clip_mask(w, h, r):
    return ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), r * s, fill=(255, 255, 255, 255)), w, h).split()[3]


def floating_clip(canvas, k, frame, cx=540, cy=430, w=560, rot=-3.0, via=None, out=None):
    """a playing reference clip in a rounded white-edged card that pops in, floats gently, and shrinks away after
    `out`; an optional "via @handle" tag hangs off its bottom-left corner. Returns the card's box for pointers."""
    if frame is None or k < 0 or (out is not None and k > out + 0.12):
        return None
    h = int(w * frame.height / frame.width)
    pic = frame.convert("RGB").resize((w, h), Image.BICUBIC).convert("RGBA")
    pic.putalpha(_clip_mask(w, h, 34))
    b = 8
    card = Image.new("RGBA", (w + 2 * b, h + 2 * b), (0, 0, 0, 0))
    card.alpha_composite(_rrect(w + 2 * b, h + 2 * b, 40, WHITE + (255,)))
    card.alpha_composite(pic, (b, b))
    if via:
        f = display(34, HEAVY)
        tw = int(f.getlength(via)) + 48
        tag = _rrect(tw, 62, 31, INK + (255,))
        ImageDraw.Draw(tag).text((tw / 2, 32), via, font=f, fill=WHITE, anchor="mm")
        full = Image.new("RGBA", (card.width + 40, card.height + 40), (0, 0, 0, 0))
        full.alpha_composite(card, (20, 0))
        full.alpha_composite(tag, (0, card.height - 22))
        card = full
    s = 0.4 + 0.6 * back(k / 0.2, 1.7)
    if out is not None and k > out:
        s *= 1 - (k - out) / 0.12
    dy = 10 * math.sin(k * 2.2)
    rr = rot + 1.2 * math.sin(k * 1.4)
    place(canvas, card, cx, cy + dy, s, rr, clamp(k / 0.06), (0, 18, 30, 150))
    return (cx - card.width * s / 2, cy + dy - card.height * s / 2, cx + card.width * s / 2, cy + dy + card.height * s / 2)


def pointer(canvas, k, text, target, cx=540, cy=1000, color=GOLD, out=None):
    """a caption chip whose curved arrow draws itself to `target` (x, y), landing on the thing it's about."""
    if k < 0 or (out is not None and k > out + 0.1):
        return
    a = 1 - clamp((k - out) / 0.1) if out is not None and k > out else 1.0
    f = display(54, HEAVY)
    tw = int(f.getlength(text)) + 70
    chip = _rrect(tw, 96, 48, WHITE + (255,))
    ImageDraw.Draw(chip).text((tw / 2, 50), text, font=f, fill=INK, anchor="mm")
    tx, ty = target
    sx, sy = cx, cy - 48 if ty < cy else cy + 48
    mx, my = (sx + tx) / 2 + (1 if tx <= sx else -1) * 120, (sy + ty) / 2
    p = cubic(clamp((k - 0.08) / 0.3))
    pts = []
    for i in range(int(40 * p) + 1):
        u = i / 40
        pts.append(((1 - u) ** 2 * sx + 2 * (1 - u) * u * mx + u * u * tx, (1 - u) ** 2 * sy + 2 * (1 - u) * u * my + u * u * ty))
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if len(pts) > 1:
        d.line(pts, fill=BLACK + (120,), width=14, joint="curve")
        d.line(pts, fill=color + (255,), width=8, joint="curve")
    if p >= 1:
        (x0, y0), (x1, y1) = pts[-4], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        head = [(x1 + 10 * math.cos(ang), y1 + 10 * math.sin(ang)),
                (x1 - 34 * math.cos(ang - 0.5), y1 - 34 * math.sin(ang - 0.5)),
                (x1 - 34 * math.cos(ang + 0.5), y1 - 34 * math.sin(ang + 0.5))]
        d.polygon(head, fill=color + (255,), outline=BLACK + (120,))
    if a < 1:
        lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
    canvas.alpha_composite(lay)
    place(canvas, chip, cx, cy, 0.7 + 0.3 * back(k / 0.16), -2.0, clamp(k / 0.05) * a, (0, 10, 18, 120))


def cover(frame, w=W, h=H):
    """the frame scaled to fill w×h, centre-cropped."""
    s = max(w / frame.width, h / frame.height)
    cw, ch = w / s, h / s
    x, y = max(0, (frame.width - cw) / 2), max(0, (frame.height - ch) / 2)
    return frame.convert("RGB").resize((w, h), Image.BICUBIC, box=(x, y, min(frame.width, x + cw), min(frame.height, y + ch)))


def screen(frame, k, box=None, box_k=None, zoom_k=None):
    """a hard cut to a screen recording: a slow push-in toward `box` (x0, y0, x1, y1 on the 1080×1920 frame), a thin
    red box that snaps on at box_k, then from zoom_k a hard cut to a zoomed crop of that box over a dimmed copy."""
    fr = cover(frame)
    if zoom_k is not None and zoom_k >= 0 and box:
        x0, y0, x1, y1 = box
        pad = 0.3 * (x1 - x0)
        crop = fr.crop((int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad)))
        bg = darken(fr.filter(ImageFilter.GaussianBlur(30)).convert("RGBA"), 1.0)
        w = 980
        im = crop.resize((w, int(crop.height * w / crop.width)), Image.BICUBIC).convert("RGBA")
        im.putalpha(_clip_mask(im.width, im.height, 36))
        place(bg, im, W / 2, H * 0.42, 1.0 + 0.04 * cubic(zoom_k / 1.2), 0.0, 1.0, (0, 20, 36, 160))
        return bg
    cx, cy = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else (W / 2, H / 2)
    s = 1 + 0.1 * cubic(k / 0.6)
    cw, ch = W / s, H / s
    left = clamp(cx - cw / 2, 0, W - cw)
    top = clamp(cy - ch / 2, 0, H - ch)
    cv = fr.resize((W, H), Image.BICUBIC, box=(left, top, left + cw, top + ch)).convert("RGBA")
    if box and box_k is not None and box_k >= 0:
        x0, y0, x1, y1 = [(v - o) * s for v, o in zip(box, (left, top, left, top))]
        ImageDraw.Draw(cv).rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), 16, outline=RED, width=7)
    return cv


def outline(mask, r=10, size=(W, H)):
    """the person's matte grown by r px (at 540 wide) for a white sticker edge."""
    return dilate(mask, r).filter(ImageFilter.GaussianBlur(1.2)).resize(size, Image.BICUBIC)


def swap(canvas, mask, k, bg=(255, 98, 20), tiles=None, edge=WHITE):
    """the room swapped in one frame for a flat colour (or a wall of playing videos, `tiles`), the person cut out on top
    with a white sticker edge. mask is the person's matte for this shot. The wall's first frame is blurred."""
    if tiles:
        back_ = wall(tiles, k)
    else:
        back_ = Image.new("RGBA", (W, H), bg + (255,))
    small = mask.convert("L").resize((540, 960))
    rim = Image.new("RGBA", (W, H), edge + (255,))
    rim.putalpha(outline(small, 9))
    back_.alpha_composite(rim)
    back_.alpha_composite(person(canvas, mask))
    return back_


def wall(tiles, k, cols=3, gap=14):
    """a grid of playing clips (frames, any size) filling the frame; one frame of blur on the cut, then sharp."""
    tw = (W - gap * (cols + 1)) // cols
    th = int(tw * 16 / 9)
    rows = math.ceil(H / (th + gap)) + 1
    cv = Image.new("RGBA", (W, H), (12, 12, 12, 255))
    y0 = -(th // 3)
    for r in range(rows):
        for c in range(cols):
            f = tiles[(r * cols + c) % len(tiles)]
            if f is None:
                continue
            im = cover(f, tw, th).convert("RGBA")
            im.putalpha(_clip_mask(tw, th, 22))
            cv.alpha_composite(im, (gap + c * (tw + gap), y0 + r * (th + gap)))
    cv = darken(cv, 0.55)
    if k < 1 / FPS:
        cv = cv.filter(ImageFilter.GaussianBlur(16))
    return cv


def _card(frame, w, r=30, b=7, ratio=16 / 9):
    h = int(w * ratio)
    pic = cover(frame, w, h).convert("RGBA")
    pic.putalpha(_clip_mask(w, h, r))
    c = _rrect(w + 2 * b, h + 2 * b, r + b, WHITE + (255,))
    c.alpha_composite(pic, (b, b))
    return c


def inset(frame, k, w=760, cy=880, via=None, ratio=16 / 9):
    """a full-frame cut to a reference clip: the clip in a rounded card over a dimmed, blurred copy of itself.
    ratio is the card's height / width: 16/9 for a vertical clip, 9/16 for a landscape one."""
    bg = darken(cover(frame).filter(ImageFilter.GaussianBlur(36)).convert("RGBA"), 0.9)
    place(bg, _card(frame, w, 40, 0, ratio), W / 2, cy, 1.0, 0.0, 1.0, (0, 24, 40, 170))
    if via:
        f = display(36, HEAVY)
        tw = int(f.getlength(via)) + 52
        tag = _rrect(tw, 66, 33, INK + (255,))
        ImageDraw.Draw(tag).text((tw / 2, 34), via, font=f, fill=WHITE, anchor="mm")
        place(bg, tag, W / 2 - w / 2 + tw / 2 + 10, cy + w * ratio / 2 + 10)
    return bg


FAN = [(-260, 40, -11.0), (0, 0, 0.0), (260, 40, 11.0)]


def fan(canvas, k, frames, cy=520, w=330):
    """three tilted clip cards fanned out at once, one frame apart."""
    for i, (f, (dx, dy, rot)) in enumerate(zip(frames, FAN)):
        u = k - i / FPS
        if f is None or u < 0:
            continue
        place(canvas, _card(f, w), W / 2 + dx, cy + dy + 6 * math.sin(k * 2 + i), 1.08 - 0.08 * clamp(u / 0.07), rot,
              1.0, (0, 18, 30, 150))


DEPTHS = [(200, 470, 230, -8.0, 0), (880, 380, 210, 7.0, 0), (150, 1180, 300, 6.0, 1), (930, 1120, 320, -6.0, 1)]


def depth(canvas, k, frames, cutout=None, out=None):
    """demo clips floating at different depths around the person: small, soft and dimmer ones behind (drawn under
    `cutout`, the person), bigger sharp ones in front at the edges. Each drifts on its own."""
    for layer in (0, 1):
        if layer == 1 and cutout is not None:
            canvas.alpha_composite(cutout)
        for i, (f, (x, y, w, rot, near)) in enumerate(zip(frames, DEPTHS)):
            if near != layer or f is None:
                continue
            u = k - 0.08 * i
            if u < 0:
                continue
            c = _card(f, w)
            if not near:
                c = darken(c, 0.35).filter(ImageFilter.GaussianBlur(2.5))
            s = 0.5 + 0.5 * back(u / 0.22)
            if out is not None and k > out:
                s *= 1 - clamp((k - out) / 0.12)
            place(canvas, c, x + 14 * math.sin(k * (1.1 + 0.3 * i) + i), y + 18 * math.sin(k * (0.9 + 0.2 * i) + 2 * i), s,
                  rot + 2 * math.sin(k * 0.8 + i), 1.0 if s > 0.05 else 0.0, (0, 16, 28, 140))


FLY = [(230, 360, -12.0), (850, 330, 10.0), (130, 760, -6.0), (950, 720, 7.0)]


def fly(canvas, k, frames, cutout, head=(540, 700), w=260):
    """clip cards flying out from behind the head to the sides, staggered, then hanging there. Draw the person over
    them with `cutout` so they come from behind."""
    for i, (f, (x, y, rot)) in enumerate(zip(frames, FLY)):
        u = clamp((k - 0.12 * i) / 0.4)
        if f is None or u <= 0:
            continue
        e = back(u, 1.2)
        px, py = head[0] + (x - head[0]) * e, head[1] + (y - head[1]) * e - 120 * math.sin(math.pi * u)
        place(canvas, _card(f, w), px, py + 8 * math.sin(k * 2 + i), 0.3 + 0.7 * cubic(u), rot * cubic(u), 1.0,
              (0, 16, 28, 140))
    if cutout is not None:
        canvas.alpha_composite(cutout)


NEON = (255, 46, 132)


def spotlight(canvas, k, cutout=None, word=None, cy=620, glow=NEON, dim=0.86, blur=12, out=None):
    """the room goes dark and soft while the person stays lit (`cutout`), with an optional neon serif word glowing
    behind the head. Pair it with a slow push-in. Eases in over 0.4s and back out over 0.3s after `out`."""
    a = inout(clamp(k / 0.4))
    if out is not None and k > out:
        a *= 1 - inout(clamp((k - out) / 0.3))
    if a <= 0.003:
        return canvas
    bg = canvas.convert("RGB").filter(ImageFilter.GaussianBlur(blur * a))
    shade = np.asarray(_vignette(), np.float32)[..., None] / 255
    px = np.asarray(bg, np.float32) * (1 - dim * a * shade)
    cv = Image.fromarray(px.astype(np.uint8)).convert("RGBA")
    if word:
        _fade_in(cv, _neon(word, glow), a, int(cy) - 200)
    if cutout is not None:
        cv.alpha_composite(cutout)
    return cv


def _fade_in(canvas, lay, a, y):
    lay = lay.copy()
    lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
    canvas.alpha_composite(lay, (0, y))


@lru_cache(1)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.clip(np.hypot((xx - W / 2) / (W * 0.75), (yy - H * 0.42) / (H * 0.6)), 0, 1)
    return Image.fromarray(((0.8 + 0.2 * d * d) * 255).astype(np.uint8), "L")


@lru_cache(8)
def _neon(word, glow):
    size = 250
    f = sit(size, 900)
    while f.getlength(word) > 980 and size > 80:
        size -= 10
        f = sit(size, 900)
    lay = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W / 2, 200), word, font=f, fill=glow + (255,), anchor="mm")
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    for r, g in ((60, 1.6), (24, 2.2), (8, 2.4), (3, 1.4)):
        halo = lay.filter(ImageFilter.GaussianBlur(r))
        halo.putalpha(halo.split()[3].point(lambda v, g=g: min(255, int(v * g))))
        out.alpha_composite(halo)
    core = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(core).text((W / 2, 200), word, font=f, fill=(255, 205, 225, 255), anchor="mm")
    out.alpha_composite(core)
    return out


def orbit(canvas, k, frames, cutout=None, head=(540, 700), rx=430, ry=300, w=180, speed=1.1, tilt=-8.0, out=None):
    """clip cards circling the head on a tilted ring: they spiral out from behind the head, pass behind the person
    (smaller, dimmer, soft) and in front (bigger, sharp), and pull back in after `out`."""
    n = len([f for f in frames if f is not None])
    if not n:
        return
    e = back(clamp(k / 0.5), 1.1)
    if out is not None and k > out:
        e *= 1 - cubic(clamp((k - out) / 0.22))
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    cards = []
    for i, f in enumerate(f for f in frames if f is not None):
        th = 2 * math.pi * i / n + speed * k - 1.8 * (1 - clamp(k / 0.6))
        ox, oy = rx * e * math.cos(th), ry * e * math.sin(th)
        z = math.sin(th)
        cards.append((z, f, head[0] + ox * ct - oy * st, head[1] + ox * st + oy * ct, -9 * math.cos(th)))
    cards.sort(key=lambda c: c[0])
    drawn_person = cutout is None
    for z, f, x, y, rot in cards:
        if not drawn_person and z >= 0:
            canvas.alpha_composite(cutout)
            drawn_person = True
        c = _card(f, w)
        if z < 0:
            alpha = c.split()[3]
            c = darken(c, -z * 0.9)
            c.putalpha(alpha)
            c = c.filter(ImageFilter.GaussianBlur(2.5 * -z))
        s = (0.82 + 0.22 * z) * (0.35 + 0.65 * clamp(e))
        place(canvas, c, x, y, s, rot, clamp(e * 2.5), (0, 16, 28, 140))
    if not drawn_person:
        canvas.alpha_composite(cutout)


def result(frame, k, under=None):
    """a result card that grows from an inset to full frame in two frames, then holds."""
    full = cover(frame).convert("RGBA")
    p = clamp(k / (2 / FPS))
    if p >= 1:
        return full
    cv = under.copy() if under is not None else Image.new("RGBA", (W, H), (0, 0, 0, 255))
    s = 0.55 + 0.45 * p
    im = full.resize((int(W * s), int(H * s)), Image.BICUBIC)
    im.putalpha(_clip_mask(im.width, im.height, int(60 * (1 - p)) + 1))
    cv.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))
    return cv


def label(canvas, text, cy=120):
    """an effect name tag at the top (for showreels)."""
    f = font(MONO, 40)
    tw = int(f.getlength(text)) + 96
    tag = _rrect(tw, 76, 38, (18, 18, 18, 225))
    d = ImageDraw.Draw(tag)
    d.ellipse((30, 30, 46, 46), fill=CLAUDE)
    d.text((62, 39), text, font=f, fill=WHITE, anchor="lm")
    place(canvas, tag, W / 2, cy)


# ------------------------------------------------------------------ slide
SLIDE_RISE, SLIDE_FALL = 0.5, 0.4
SLIDE_OVERSCAN = 1.12


@lru_cache(16)
def slide_still(path, w, h, focus=(0.5, 0.5)):
    im = Image.open(path).convert("RGB")
    ow, oh = int(w * SLIDE_OVERSCAN), int(h * SLIDE_OVERSCAN)
    s = max(ow / im.width, oh / im.height)
    cw, ch = ow / s, oh / s
    x0 = (im.width - cw) * focus[0]
    y0 = (im.height - ch) * focus[1]
    return im.resize((ow, oh), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def slide_push(still, k, w, h):
    z = min(SLIDE_OVERSCAN, 1.0 + 0.018 * max(0.0, k))
    cw, ch = still.width / z, still.height / z
    x0, y0 = (still.width - cw) / 2, (still.height - ch) / 2
    return still.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def slide_ease(k, out_k=None):
    e = cubic(k / SLIDE_RISE)
    if out_k is not None and out_k >= 0:
        e *= 1 - inout(out_k / SLIDE_FALL)
    return e


def slide(frame, media, k, z=1.0, panel_z=1.0, fy=0.34, join=H // 2, face=0.42, out_k=None):
    e = slide_ease(k, out_k)
    lift = max(0.0, fy * H - face * join) * e
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    cv.paste(shot(frame, z + (panel_z - z) * e, fy), (0, -round(lift)))
    cv.paste(media, (0, round(H - (H - join) * e)))
    return cv
