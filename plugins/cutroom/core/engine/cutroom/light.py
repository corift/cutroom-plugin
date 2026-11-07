"""Light product UI look (2026-10-21, from @charliehills' "Claude edited this entire video").

A white to pale-blue page on top, the face in a rounded panel below, a small caption between them, one blue
accent and Claude orange only in the mark. White cards with soft shadows. Things move by changing state
(typing, ticking, highlighting, counting), not by flying in: cards rise in once, then only their contents move.

    from cutroom import light as L
    cv = L.canvas()
    L.prompt_card(cv, k, "Edit this video. Cut the silences.", file="raw.mp4", t_check=2.2)
    L.face_panel(cv, face_frame)
    L.caption(cv, k, [("Claude", 0.1), ("edited", 0.35), ("this", 0.6)])

Every block is `block(canvas, k, ...)` with k in local seconds, chunk-safe like blocks.py.
Showcase: templates/shorts/light_showcase.py
"""
import math, random
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from . import brand
from .core import W, H, font, SFD, SFT, MONO, clamp, expo, inout, wrap
from .blocks import ss, place, rounded_rect, _partial, CLAUDE

BLUE = brand.color("light_accent", (30, 111, 240))
INK = (22, 22, 26)
MUTED = (128, 131, 140)
FAINT = (196, 199, 207)
EDGE = (226, 229, 236)
TINT = (232, 240, 254)
WHITE = (255, 255, 255)
ZONE_CY = 520
FACE_BOX = (40, 1150, 1040, 1880)
CAPTION_Y = 1092

@lru_cache(1)
def _page():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.clip(np.hypot((xx - W / 2) / (W * 0.62), (yy - ZONE_CY) / (H * 0.42)), 0, 1) ** 1.8
    top, edge = np.array((253, 253, 254), np.float32), np.array((212, 226, 250), np.float32)
    img = top[None, None] * (1 - d[..., None]) + edge[None, None] * d[..., None]
    return Image.fromarray(np.dstack([img, np.full((H, W), 255, np.float32)]).astype(np.uint8), "RGBA")

def canvas(frame=0):
    """the light page: white in the middle of the graphic zone, pale blue at the edges. No grain."""
    return _page().copy()

def face_panel(canvas, frame, box=FACE_BOX, radius=44, focus=0.32):
    """the talking head in a rounded panel at the bottom; `frame` = this frame of the face video."""
    x0, y0, x1, y1 = box
    im = rounded_rect(ImageOps.fit(frame.convert("RGB"), (x1 - x0, y1 - y0), Image.BICUBIC, centering=(0.5, focus)), radius)
    place(canvas, im, (x0 + x1) / 2, (y0 + y1) / 2, shadow=(0, 14, 30, 60))

def _chunks(words, per=2, gap=0.35):
    out, cur = [], []
    for i, (w_, t) in enumerate(words):
        if cur and (len(cur) >= per or t - words[i - 1][1] > gap): out.append(cur); cur = []
        cur.append((w_, t))
    if cur: out.append(cur)
    return out

def caption(canvas, k, words, cy=CAPTION_Y, size=46, per=2, hold=0.6):
    """small dark caption between the page and the face, `per` words at a time; a word shows grey until
    it is spoken, then turns ink in 0.1s. words = [(word, t)] in local s."""
    chunks = _chunks(words, per)
    for i, ch in enumerate(chunks):
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else ch[-1][1] + hold
        if ch[0][1] - 0.15 <= k < end: break
    else: return
    f = font(SFT("Semibold"), size); gap = f.getlength(" ")
    tot = sum(f.getlength(w_) for w_, _ in ch) + gap * (len(ch) - 1)
    d = ImageDraw.Draw(canvas); x = W / 2 - tot / 2
    for w_, t in ch:
        p = clamp((k - t) / 0.1)
        col = tuple(int(FAINT[c] + (INK[c] - FAINT[c]) * p) for c in range(3))
        d.text((x, cy), w_, font=f, fill=col, anchor="lm"); x += f.getlength(w_) + gap

@lru_cache(4)
def claude_mark(size, color=CLAUDE):
    """Claude's orange starburst, drawn (no logo file needed)."""
    def dr(d, s):
        c = size * s / 2
        for i in range(12):
            a = math.radians(i * 30 + 8); r = c * (0.96 if i % 2 == 0 else 0.78)
            x, y = c + math.cos(a) * r, c + math.sin(a) * r
            d.line([(c, c), (x, y)], fill=color + (255,), width=int(size * s * 0.11))
            e = size * s * 0.055; d.ellipse((x - e, y - e, x + e, y + e), fill=color + (255,))
        e = size * s * 0.12; d.ellipse((c - e, c - e, c + e, c + e), fill=color + (255,))
    return ss(dr, size, size, 3)

@lru_cache(32)
def status_pill(txt, done=False, size=26):
    f = font(SFT("Semibold"), size); w_ = int(f.getlength(txt)) + 44; h_ = int(size * 1.9)
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), h_ * s / 2, fill=(BLUE if done else TINT) + (255,)), w_, h_)
    ImageDraw.Draw(im).text((w_ / 2, h_ / 2), txt, font=f, fill=WHITE if done else BLUE, anchor="mm")
    return im

@lru_cache(16)
def _card(w, h, title, mark, radius=30):
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=WHITE + (255,), outline=EDGE + (255,), width=2 * s), w, h)
    if title:
        d = ImageDraw.Draw(im); x = 44
        if mark: im.alpha_composite(claude_mark(40), (40, 32)); x = 96
        d.text((x, 52), title, font=font(SFT("Semibold"), 34), fill=INK, anchor="lm")
    return im

def _status_at(statuses, k):
    cur = None
    for t, txt, done in statuses:
        if k >= t: cur = (txt, done)
    return cur

def card_in(canvas, k, img, cx, cy, out=None):
    """the one entrance in this look, measured at 10 fps on the source: on within 3 frames (fade with an 8px
    rise), off in 2. The cards are not the motion; what changes inside them is."""
    if k <= 0: return
    a = clamp(k / 0.1); e = expo(k / 0.12)
    if out is not None and k > out:
        u = clamp((k - out) / 0.07); a *= 1 - u
    place(canvas, img, cx, cy + (1 - e) * 8, 1, 0, a, shadow=(0, 20, 40, 46))

def _with_status(card, statuses, k, w):
    s = _status_at(statuses, k)
    if s:
        p = status_pill(*s); card.alpha_composite(p, (w - 36 - p.width, 52 - p.height // 2))

def _check(d, cx, cy, r, p, col=WHITE, width=5):
    pts = [(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.34), (cx + r * 0.45, cy - r * 0.3)]
    seg = _partial(pts, p)
    if len(seg) > 1: d.line(seg, fill=col, width=width, joint="curve")

def _send(card, x, y, press=0.0, active=True):
    bs = 64
    btn = ss(lambda d, s: d.ellipse((0, 0, bs * s - 1, bs * s - 1), fill=(BLUE if active else FAINT) + (255,)), bs, bs)
    d = ImageDraw.Draw(btn)
    d.line([(32, 46), (32, 19)], fill=WHITE, width=5); d.line([(21, 30), (32, 18), (43, 30)], fill=WHITE, width=5, joint="curve")
    place(card, btn, x, y, 1 - 0.12 * press)

def _file_chip(name, checked):
    f = font(SFT("Medium"), 28); w_ = int(f.getlength(name)) + 118; h_ = 62
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), 16 * s, fill=(244, 246, 250, 255), outline=EDGE + (255,), width=2 * s), w_, h_)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 16, 44, 46), 5, outline=MUTED, width=3)
    d.text((58, h_ / 2), name, font=f, fill=INK, anchor="lm")
    cx = w_ - 34
    if checked > 0:
        d.ellipse((cx - 16, h_ / 2 - 16, cx + 16, h_ / 2 + 16), fill=BLUE)
        _check(d, cx, h_ / 2, 16, checked, width=4)
    return im

def prompt_card(canvas, k, text, cx=540, cy=ZONE_CY, w=960, t_type=0.3, cps=26, file=None, t_file=0.0, t_check=None,
                t_send=None, statuses=(), title="Claude Code", out=None):
    """the Claude Code prompt typing in (blue caret), an attached file chip that gets a blue tick at t_check,
    and the blue send button pressing at t_send. statuses = [(t, "Step 1 of 4", done)] for the top-right pill."""
    fT = font(SFT("Regular"), 40); lh = 56
    lines_full = wrap(text, fT, w - 88)
    h_ = 126 + len(lines_full) * lh + 120
    card = _card(w, h_, title, True).copy(); d = ImageDraw.Draw(card)
    _with_status(card, statuses, k, w)
    n = int(clamp((k - t_type) * cps, 0, len(text)))
    lines = wrap(text[:n], fT, w - 88) if n else []
    y0 = 120
    for i, ln in enumerate(lines): d.text((44, y0 + i * lh), ln, font=fT, fill=INK)
    typing = n < len(text) or (t_send is None or k < t_send)
    if typing and (k * 2.2) % 1 < 0.62:
        last = lines[-1] if lines else ""
        x = 46 + fT.getlength(last); y = y0 + (max(1, len(lines)) - 1) * lh
        d.rounded_rectangle((x, y + 6, x + 4, y + 50), 2, fill=BLUE)
    by = h_ - 60
    if file and k >= t_file:
        chip = _file_chip(file, clamp((k - t_check) / 0.3) if t_check is not None and k >= t_check else 0)
        place(card, chip, 40 + chip.width / 2, by, 1, 0, clamp((k - t_file) / 0.2))
    press = math.exp(-(k - t_send) * 9) if t_send is not None and t_send <= k < t_send + 0.6 else 0
    _send(card, w - 40 - 32, by, press, n > 0)
    card_in(canvas, k, card, cx, cy, out)

def words_card(canvas, k, words, cx=540, cy=ZONE_CY, w=960, title="audio.json", statuses=(), cols=2, out=None):
    """the transcript Claude writes: rows of `time  word` that turn blue one after another as they are read.
    words = [("7.76s", "Not", t_on)]."""
    rows = math.ceil(len(words) / cols); rh = 64
    h_ = 130 + rows * rh + 30
    card = _card(w, h_, title, False).copy(); d = ImageDraw.Draw(card)
    _with_status(card, statuses, k, w)
    fM, fW = font(MONO, 28), font(SFT("Semibold"), 36); cw = (w - 88) / cols
    for i, (ts, word, t_on) in enumerate(words):
        c, r = i // rows, i % rows
        x, y = 44 + c * cw, 130 + r * rh + rh / 2
        p = clamp((k - t_on) / 0.12)
        col = tuple(int(FAINT[j] + (BLUE[j] - FAINT[j]) * p) for j in range(3))
        d.text((x, y), ts, font=fM, fill=MUTED if p > 0 else FAINT, anchor="lm")
        d.text((x + 150, y), word, font=fW, fill=col, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

@lru_cache(4)
def _bars(n, seed, silence):
    rng = random.Random(seed); out = []
    for i in range(n):
        u = i / (n - 1)
        quiet = abs(u - silence) < 0.07
        out.append(0.06 + rng.random() * 0.08 if quiet else 0.3 + 0.7 * abs(math.sin(i * 0.7 + rng.random())) * rng.uniform(0.6, 1))
    return out

def wave_card(canvas, k, cx=540, cy=ZONE_CY, w=960, title="raw.mp4", t_play=(0.2, 1.6), t_cut=1.9, silence=0.58,
              n=56, statuses=(), duration="2:05", out=None):
    """the raw clip's waveform: a playhead sweeps it (played bars turn blue), then at t_cut the quiet stretch is
    selected and pulled out, the two sides close the gap and a blue tick pops on the seam."""
    h_ = 420
    card = _card(w, h_, title, False).copy(); d = ImageDraw.Draw(card)
    _with_status(card, statuses, k, w)
    bars = _bars(n, 7, silence)
    x0, x1, mid, amp = 60, w - 60, 250, 105
    step = (x1 - x0) / n; bw = step * 0.56
    ph = clamp((k - t_play[0]) / (t_play[1] - t_play[0]))
    lo, hi = int((silence - 0.07) * (n - 1)) + 1, int((silence + 0.07) * (n - 1))
    sel = clamp((k - t_cut) / 0.25); close = inout(clamp((k - t_cut - 0.45) / 0.4))
    gap_w = (hi - lo + 1) * step
    for i, b in enumerate(bars):
        x = x0 + i * step
        quiet = lo <= i <= hi
        if quiet and close > 0: continue
        if i > hi: x -= gap_w * close
        x += gap_w * close / 2 if close else 0
        played = i / n <= ph
        col = BLUE if played else (204, 216, 240)
        hh = b * amp
        d.rounded_rectangle((x, mid - hh, x + bw, mid + hh), bw / 2, fill=col)
    if 0 < ph < 1:
        px = x0 + ph * (x1 - x0); d.line([(px, mid - 130), (px, mid + 130)], fill=INK, width=3)
    if sel > 0 and close < 1:
        sx0, sx1 = x0 + lo * step - 8, x0 + (hi + 1) * step - step * 0.44 + 8
        a = int(255 * sel * (1 - close))
        lay = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle((sx0, mid - 130, sx1, mid + 130), 14, fill=TINT + (int(a * 0.7),), outline=BLUE + (a,), width=3)
        card.alpha_composite(lay)
    if close >= 1:
        cxs = x0 + lo * step + gap_w / 2 - step * 0.22
        p = expo(clamp((k - t_cut - 0.85) / 0.3))
        if p > 0:
            r = 26 * (0.6 + 0.4 * p)
            d.ellipse((cxs - r, mid - 160 - r, cxs + r, mid - 160 + r), fill=BLUE)
            _check(d, cxs, mid - 160, r, clamp((k - t_cut - 0.9) / 0.25), width=5)
    fM = font(MONO, 26)
    d.text((x0, h_ - 40), "0:00", font=fM, fill=MUTED, anchor="lm")
    d.text((x1, h_ - 40), duration, font=fM, fill=MUTED, anchor="rm")
    card_in(canvas, k, card, cx, cy, out)

def style_card(canvas, k, rows, cx=540, cy=ZONE_CY, w=960, title="design.md", statuses=(), out=None):
    """the design file filling in one row at a time. rows = [(label, value, t)] where value is text or a list of
    colours (swatches pop in one by one)."""
    rh = 104; h_ = 130 + len(rows) * rh + 20
    card = _card(w, h_, title, False).copy(); d = ImageDraw.Draw(card)
    _with_status(card, statuses, k, w)
    fL, fV = font(SFT("Medium"), 30), font(SFT("Semibold"), 38)
    for i, (label, value, t) in enumerate(rows):
        p = clamp((k - t) / 0.2)
        if p <= 0: continue
        y = 130 + i * rh + rh / 2; dx = (1 - expo((k - t) / 0.35)) * 16
        if i: d.line([(44, y - rh / 2), (w - 44, y - rh / 2)], fill=EDGE, width=2)
        lay = Image.new("RGBA", card.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        dl.text((44 + dx, y), label, font=fL, fill=MUTED, anchor="lm")
        if isinstance(value, str): dl.text((w - 44 + dx, y), value, font=fV, fill=INK, anchor="rm")
        else:
            for j, col in enumerate(reversed(value)):
                q = expo(clamp((k - t - 0.12 * (len(value) - 1 - j)) / 0.25))
                if q <= 0: continue
                r = 22 * q; x = w - 66 - j * 64
                dl.ellipse((x - r, y - r, x + r, y + r), fill=tuple(col), outline=EDGE if tuple(col) == WHITE else None, width=2)
        lay.putalpha(lay.split()[3].point(lambda v: int(v * p))); card.alpha_composite(lay)
    card_in(canvas, k, card, cx, cy, out)

def check_card(canvas, k, rows, cx=540, cy=ZONE_CY, w=960, title="Self-check", statuses=(), out=None):
    """rows tick one after another: the ring fills blue, a white tick draws, the title turns blue.
    rows = [(title, sub, t)]."""
    rh = 120; h_ = 130 + len(rows) * rh + 20
    card = _card(w, h_, title, True).copy(); d = ImageDraw.Draw(card)
    _with_status(card, statuses, k, w)
    fT, fS = font(SFT("Semibold"), 38), font(SFT("Regular"), 28)
    for i, (txt, sub, t) in enumerate(rows):
        y = 130 + i * rh + rh / 2; cx_ = 80
        p = clamp((k - t) / 0.18)
        if p > 0: d.ellipse((cx_ - 26, y - 26, cx_ + 26, y + 26), fill=BLUE)
        else: d.ellipse((cx_ - 26, y - 26, cx_ + 26, y + 26), outline=FAINT, width=3)
        if p > 0: _check(d, cx_, y, 26, clamp((k - t - 0.08) / 0.22), width=5)
        col = tuple(int(INK[j] + (BLUE[j] - INK[j]) * p) for j in range(3))
        d.text((130, y - 18), txt, font=fT, fill=col, anchor="lm")
        d.text((130, y + 24), sub, font=fS, fill=MUTED, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

def memory_card(canvas, k, note, rules, new_rule, cx=540, cy=ZONE_CY, w=960, t_type=0.2, cps=28, t_save=1.6,
                struck=None, t_strike=None, title="memory.md", out=None):
    """a review note typing into a grey bubble, then memory.md with the new rule swept in blue and a Saved pill.
    struck = an old rule that gets a line drawn through it at t_strike."""
    fN, fR = font(SFT("Regular"), 34), font(SFT("Medium"), 34)
    rules = list(rules) + [new_rule]
    h_ = 150 + 110 + len(rules) * 70 + 40
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    n = int(clamp((k - t_type) * cps, 0, len(note)))
    d.rounded_rectangle((40, 36, w - 40, 136), 22, fill=(242, 243, 246))
    d.text((70, 86), "Your note: " + note[:n], font=fN, fill=INK, anchor="lm")
    if n < len(note) and (k * 2.2) % 1 < 0.62:
        x = 72 + fN.getlength("Your note: " + note[:n]); d.rounded_rectangle((x, 66, x + 4, 108), 2, fill=BLUE)
    d.text((44, 200), title, font=font(SFT("Semibold"), 34), fill=INK, anchor="lm")
    if k >= t_save:
        p = status_pill("Saved", True); q = expo(clamp((k - t_save - 0.4) / 0.25))
        if q > 0: place(card, p, w - 44 - p.width / 2, 200, 0.8 + 0.2 * q, 0, q)
    for i, r in enumerate(rules):
        y = 270 + i * 70
        new = r == new_rule
        if new:
            if k < t_save: continue
            sw = expo(clamp((k - t_save) / 0.4)) * (fR.getlength(r) + 36)
            d.rounded_rectangle((26, y - 30, 26 + sw, y + 30), 12, fill=TINT)
        d.text((44, y), r, font=fR, fill=BLUE if new else INK, anchor="lm")
        if struck and r == struck and t_strike is not None and k >= t_strike:
            sx = 44 + fR.getlength(r) * expo(clamp((k - t_strike) / 0.3)); d.line([(40, y + 2), (sx, y + 2)], fill=MUTED, width=4)
    card_in(canvas, k, card, cx, cy, out)

def count_card(canvas, k, thumb, a=2500, b=10000, cx=540, cy=ZONE_CY, w=960, t0=0.3, dur=1.2, label="views", suffix="+",
               title=None, out=None):
    """a posted video's thumbnail and its view count climbing from a to b, with a blue bar filling under it."""
    h_ = 360
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    tw, th = 180, 300
    card.alpha_composite(rounded_rect(ImageOps.fit(thumb.convert("RGB"), (tw, th), Image.BICUBIC), 20), (30, 30))
    p = inout(clamp((k - t0) / dur))
    val = int(a + (b - a) * p); txt = f"{val:,}" + (suffix if p >= 1 else "")
    if title: d.text((250, 76), title, font=font(SFT("Semibold"), 32), fill=MUTED, anchor="lm")
    d.text((250, 170), txt, font=font(SFD("Bold"), 104), fill=INK, anchor="lm")
    d.text((250 + font(SFD("Bold"), 104).getlength(txt) + 18, 190), label, font=font(SFT("Medium"), 36), fill=MUTED, anchor="lm")
    bx0, bx1, by = 250, w - 50, 280
    d.rounded_rectangle((bx0, by - 9, bx1, by + 9), 9, fill=TINT)
    d.rounded_rectangle((bx0, by - 9, bx0 + max(20, (bx1 - bx0) * p), by + 9), 9, fill=BLUE)
    card_in(canvas, k, card, cx, cy, out)

def slam_word(canvas, k, word, cx=540, cy=ZONE_CY, size=250, out=None):
    """one huge black word alone on the page, its last character (the full stop) in blue; lands in 0.18s."""
    if k <= 0: return
    f = font(SFD("Heavy"), size); body, tail = word[:-1], word[-1]
    wb, wt = f.getlength(body), f.getlength(tail)
    asc, desc = f.getmetrics(); im = Image.new("RGBA", (int(wb + wt) + 20, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); d.text((10, 10), body, font=f, fill=INK); d.text((10 + wb, 10), tail, font=f, fill=BLUE)
    a = clamp(k / 0.08)
    if out is not None and k > out: a *= 1 - clamp((k - out) / 0.15)
    place(canvas, im, cx, cy, 1.08 - 0.08 * expo(k / 0.18), 0, a)

def cta_card(canvas, k, word="EDIT", line=("I'll send you the ", "prompts", " + the full setup"), cx=540, cy=ZONE_CY,
             t_line=0.5, out=None):
    """end card: blue chat icon, small 'Comment', the keyword huge, and one line with a blue underlined word."""
    w, h_ = 960, 640
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    ic = ss(lambda dd, s: dd.rounded_rectangle((0, 0, 150 * s - 1, 150 * s - 1), 38 * s, fill=BLUE + (255,)), 150, 150)
    di = ImageDraw.Draw(ic); di.rounded_rectangle((34, 40, 116, 98), 18, fill=WHITE); di.polygon([(50, 96), (50, 118), (72, 96)], fill=WHITE)
    card.alpha_composite(ic, (w // 2 - 75, 50))
    d.text((w / 2, 250), "Comment", font=font(SFT("Medium"), 44), fill=MUTED, anchor="mm")
    d.text((w / 2, 380), word, font=font(SFD("Heavy"), 190), fill=INK, anchor="mm")
    p = clamp((k - t_line) / 0.25)
    if p > 0:
        fL = font(SFT("Medium"), 38); a_, b_, c_ = line
        tot = fL.getlength(a_ + b_ + c_); x = w / 2 - tot / 2; y = 545
        g = tuple(int(255 - (255 - MUTED[j]) * p) for j in range(3))
        d.text((x, y), a_, font=fL, fill=g, anchor="lm"); x2 = x + fL.getlength(a_)
        d.text((x2, y), b_, font=fL, fill=tuple(int(255 - (255 - BLUE[j]) * p) for j in range(3)), anchor="lm")
        u = expo(clamp((k - t_line - 0.2) / 0.35)); d.line([(x2, y + 26), (x2 + fL.getlength(b_) * u, y + 26)], fill=BLUE, width=4)
        d.text((x2 + fL.getlength(b_), y), c_, font=fL, fill=g, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

def hook_card(canvas, k, title, name="Sully", avatar=None, cx=540, cy=ZONE_CY, w=960, t_wave=0.3, out=None):
    """opening card: the Claude mark and a bold title, a waveform strip filling blue, an 'Edited by' pill."""
    fT = font(SFD("Bold"), 64); lines = wrap(title, fT, w - 160)
    h_ = 70 + len(lines) * 78 + 230
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    card.alpha_composite(claude_mark(64), (44, 50))
    for i, ln in enumerate(lines): d.text((132, 84 + i * 78), ln, font=fT, fill=INK, anchor="lm")
    y = 70 + len(lines) * 78 + 60; bars = _bars(44, 3, 2.0)
    p = clamp((k - t_wave) / 1.0); step = (w - 88) / len(bars)
    for i, b in enumerate(bars):
        x = 44 + i * step; hh = 8 + b * 30
        d.rounded_rectangle((x, y - hh, x + step * 0.55, y + hh), step * 0.27, fill=BLUE if i / len(bars) <= p else (214, 222, 238))
    pf = font(SFT("Medium"), 30); label = "Edited by"
    pw = int(pf.getlength(label) + pf.getlength(name)) + 120; py = y + 90
    d.rounded_rectangle((44, py - 32, 44 + pw, py + 32), 32, fill=(244, 246, 250), outline=EDGE, width=2)
    d.text((70, py), label, font=pf, fill=MUTED, anchor="lm")
    ax = 70 + pf.getlength(label) + 30
    if avatar is not None:
        card.alpha_composite(_round(avatar, 40), (int(ax - 20), int(py - 20)))
    else: d.ellipse((ax - 20, py - 20, ax + 20, py + 20), fill=CLAUDE)
    d.text((ax + 30, py), name, font=font(SFT("Semibold"), 30), fill=INK, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

def _round(img, s):
    im = ImageOps.fit(img.convert("RGB"), (s, s), Image.BICUBIC).convert("RGBA")
    m = ss(lambda d, sc: d.ellipse((0, 0, s * sc - 1, s * sc - 1), fill=(255, 255, 255, 255)), s, s).split()[3]
    im.putalpha(m); return im

def step_label(canvas, k, n, text, cx=540, cy=170, size=64):
    """a blue 'Step n' pill and the step's title beside it, typed on; sits above a card."""
    if k <= 0: return
    pf = font(SFT("Bold"), int(size * 0.55)); pill = f"Step {n}"
    pw, ph = int(pf.getlength(pill)) + 48, int(size * 1.05)
    fT = font(SFD("Bold"), size); shown = text[:int(clamp((k - 0.15) * 30, 0, len(text)))]
    tot = pw + 28 + fT.getlength(text); x = cx - tot / 2
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, pw * s - 1, ph * s - 1), ph * s / 2, fill=BLUE + (255,)), pw, ph)
    ImageDraw.Draw(im).text((pw / 2, ph / 2), pill, font=pf, fill=WHITE, anchor="mm")
    place(canvas, im, x + pw / 2, cy, 0.9 + 0.1 * expo(k / 0.2), 0, clamp(k / 0.1))
    ImageDraw.Draw(canvas).text((x + pw + 28, cy), shown, font=fT, fill=INK, anchor="lm")

def list_card(canvas, k, items, cx=540, cy=ZONE_CY, w=960, title=None, out=None):
    """numbered rows that light up one at a time: the number badge fills blue as its row is said.
    items = [(text, t)]."""
    rh = 128; top = 130 if title else 40; h_ = top + len(items) * rh + 30
    card = _card(w, h_, title, True).copy(); d = ImageDraw.Draw(card)
    fT, fN = font(SFD("Bold"), 46), font(SFD("Bold"), 34)
    for i, (txt, t) in enumerate(items):
        y = top + i * rh + rh / 2; p = clamp((k - t) / 0.18)
        if i: d.line([(44, y - rh / 2), (w - 44, y - rh / 2)], fill=EDGE, width=2)
        d.ellipse((50, y - 32, 114, y + 32), fill=BLUE if p > 0 else TINT)
        d.text((82, y), str(i + 1), font=fN, fill=WHITE if p > 0 else BLUE, anchor="mm")
        col = tuple(int(FAINT[j] + (INK[j] - FAINT[j]) * p) for j in range(3))
        d.text((146, y), txt, font=fT, fill=col, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

def folder_card(canvas, k, root, children, cx=540, cy=ZONE_CY, w=960, out=None):
    """a project folder: the root row, then children slide in on a tree line one by one.
    children = [(name, t)]; names ending in / are folders."""
    rh = 104; h_ = 150 + len(children) * rh + 30
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    fR, fC = font(SFT("Semibold"), 44), font(SFT("Medium"), 40)

    def icon(x, y, folder, col):
        if folder:
            d.rounded_rectangle((x, y - 20, x + 26, y - 8), 4, fill=col)
            d.rounded_rectangle((x, y - 14, x + 56, y + 24), 8, fill=col)
        else:
            d.rounded_rectangle((x + 8, y - 24, x + 46, y + 24), 6, outline=col, width=4)

    icon(50, 80, True, BLUE)
    d.text((130, 80), root, font=fR, fill=INK, anchor="lm")
    for i, (name, t) in enumerate(children):
        p = clamp((k - t) / 0.2)
        if p <= 0: continue
        y = 150 + i * rh + rh / 2; dx = (1 - expo((k - t) / 0.3)) * 20
        d.line([(78, 112 + i * rh), (78, y), (130, y)], fill=FAINT, width=3)
        folder = name.endswith("/")
        icon(150 + dx, y, folder, BLUE if folder else MUTED)
        d.text((232 + dx, y), name, font=fC, fill=INK, anchor="lm")
    card_in(canvas, k, card, cx, cy, out)

def bar_card(canvas, k, bars, title, accent_word=None, cx=540, cy=ZONE_CY, w=960, t0=0.3, stagger=0.12, out=None):
    """a bar chart card: bars grow left to right with their value on top, tallest one blue.
    bars = [(label, value)]; title may end in an accent word set in blue."""
    h_ = 760
    card = _card(w, h_, None, False).copy(); d = ImageDraw.Draw(card)
    fT = font(SFD("Bold"), 54); d.text((48, 74), title, font=fT, fill=INK, anchor="lm")
    if accent_word:
        d.text((52 + fT.getlength(title + " "), 74), accent_word, font=fT, fill=BLUE, anchor="lm")
    vmax = max(v for _, v in bars); n = len(bars)
    x0, x1, base, top = 60, w - 60, h_ - 90, 200
    step = (x1 - x0) / n; bw = step * 0.62
    fV, fL = font(SFT("Bold"), 28), font(SFT("Medium"), 26)
    for i, (label, v) in enumerate(bars):
        p = expo(clamp((k - t0 - i * stagger) / 0.5))
        x = x0 + i * step + (step - bw) / 2; hh = (base - top) * v / vmax * p
        d.rounded_rectangle((x, base - max(hh, 6), x + bw, base), 10, fill=BLUE if v == vmax else (198, 212, 238))
        if p > 0.6:
            txt = f"{v / 1000:.0f}K" if v >= 1000 else str(v)
            d.text((x + bw / 2, base - hh - 26), txt, font=fV, fill=INK, anchor="mm")
        d.text((x + bw / 2, base + 40), label, font=fL, fill=MUTED, anchor="mm")
    d.line([(x0, base), (x1, base)], fill=EDGE, width=3)
    card_in(canvas, k, card, cx, cy, out)

def compare_row(canvas, k, thumbs, labels=("Bad", "Good", "Best"), views=("2K", "40K", "1.2M"), cx=540, cy=ZONE_CY,
                tw=290, th=460, times=(0.2, 0.6, 1.0), best=None):
    """three phone-shaped thumbnails side by side, each with a label above and a views pill below;
    the `best` one (default last) gets a blue outline and pill."""
    best = len(thumbs) - 1 if best is None else best
    gap = 26; x0 = cx - (len(thumbs) * tw + (len(thumbs) - 1) * gap) / 2
    fL, fV = font(SFD("Bold"), 40), font(SFT("Bold"), 30)
    for i, (im, lab, vw, t) in enumerate(zip(thumbs, labels, views, times)):
        if k < t: continue
        hi = i == best; x = x0 + i * (tw + gap) + tw / 2
        frame = Image.new("RGBA", (tw + 16, th + 16), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rounded_rectangle((0, 0, tw + 15, th + 15), 34, fill=(BLUE if hi else WHITE) + (255,))
        frame.alpha_composite(rounded_rect(ImageOps.fit(im.convert("RGB"), (tw, th), Image.BICUBIC, centering=(0.5, 0.3)), 28), (8, 8))
        card_in(canvas, k - t, frame, x, cy)
        d = ImageDraw.Draw(canvas); a = clamp((k - t) / 0.15)
        d.text((x, cy - th / 2 - 50), lab, font=fL, fill=tuple(int(255 - (255 - (BLUE if hi else INK)[j]) * a) for j in range(3)), anchor="mm")
        pw = int(fV.getlength(vw + " views")) + 44
        pill = ss(lambda dd, s: dd.rounded_rectangle((0, 0, pw * s - 1, 56 * s - 1), 28 * s, fill=(BLUE if hi else INK) + (255,)), pw, 56)
        ImageDraw.Draw(pill).text((pw / 2, 28), vw + " views", font=fV, fill=WHITE, anchor="mm")
        place(canvas, pill, x, cy + th / 2 + 52, 0.9 + 0.1 * expo((k - t - 0.15) / 0.2), 0, clamp((k - t - 0.15) / 0.12))

def chat_screen(canvas, k, command, result, label, t_type=0.2, cps=14, t_send=1.2, t_result=1.6, hint=None):
    """the Claude app on a phone, dark: a slash command types into the composer with its menu hint above,
    sends, a 'Running' line shows, then the result clip appears as a reply card with a label on it.
    result = the frame of the finished clip at this moment."""
    cv = Image.new("RGBA", (W, H), (32, 31, 30, 255)); d = ImageDraw.Draw(cv)
    fS, fC, fM = font(SFT("Medium"), 32), font(SFT("Regular"), 40), font(SFT("Medium"), 30)
    d.rounded_rectangle((W / 2 - 150, 70, W / 2 + 150, 140), 35, fill=(48, 47, 45))
    d.rounded_rectangle((W / 2, 78, W / 2 + 142, 132), 27, fill=(70, 68, 66))
    d.text((W / 2 - 75, 105), "Chat", font=fS, fill=(150, 146, 140), anchor="mm")
    d.text((W / 2 + 71, 105), "Code", font=fS, fill=(240, 238, 234), anchor="mm")
    sent = k >= t_send
    n = int(clamp((k - t_type) * cps, 0, len(command)))
    comp_y = 1700
    d.rounded_rectangle((40, comp_y - 90, W - 40, comp_y + 90), 36, fill=(48, 47, 45), outline=(66, 64, 62), width=2)
    if not sent:
        d.text((80, comp_y - 30), command[:n], font=fC, fill=CLAUDE, anchor="lm")
        if (k * 2.2) % 1 < 0.62:
            x = 82 + fC.getlength(command[:n]); d.rounded_rectangle((x, comp_y - 54, x + 4, comp_y - 6), 2, fill=CLAUDE)
        if hint and n > 1:
            d.rounded_rectangle((40, comp_y - 230, W - 40, comp_y - 110), 26, fill=(42, 41, 39), outline=(66, 64, 62), width=2)
            d.text((80, comp_y - 190), command, font=font(SFT("Semibold"), 34), fill=(240, 238, 234), anchor="lm")
            d.text((80, comp_y - 148), hint, font=fM, fill=(150, 146, 140), anchor="lm")
    else:
        d.text((80, comp_y - 30), "Reply to Claude...", font=fC, fill=(120, 116, 110), anchor="lm")
        bw = int(fS.getlength(command)) + 48
        d.rounded_rectangle((W - 60 - bw, 200, W - 60, 270), 22, fill=(58, 46, 40))
        d.text((W - 60 - bw / 2, 235), command, font=fS, fill=CLAUDE, anchor="mm")
        if k < t_result:
            d.ellipse((60, 316, 84, 340), fill=CLAUDE)
            d.text((104, 328), "Running " + command + "...", font=fM, fill=(170, 166, 160), anchor="lm")
    d.ellipse((W - 116, comp_y - 4, W - 56, comp_y + 56), fill=CLAUDE)
    d.line([(W - 86, comp_y + 42), (W - 86, comp_y + 12)], fill=WHITE, width=5)
    d.line([(W - 98, comp_y + 24), (W - 86, comp_y + 11), (W - 74, comp_y + 24)], fill=WHITE, width=5, joint="curve")
    if k >= t_result:
        rw, rh = 760, 1150
        clip = rounded_rect(ImageOps.fit(result.convert("RGB"), (rw, rh), Image.BICUBIC, centering=(0.5, 0.35)), 36)
        dd = ImageDraw.Draw(clip); fl = font(SFD("Bold"), 52)
        dd.text((rw / 2, rh - 120), label, font=fl, fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
        card_in(cv, k - t_result, clip, W / 2, 330 + rh / 2)
    canvas.alpha_composite(cv)
