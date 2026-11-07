"""Cinematic room look (2026-10-21, from @raycfu, @tenfoldmarc, @iamajene and @simonbeard).

The footage carries it: a graded talking head in a real room (teal shadows, warm skin, crushed blacks, a
vignette), with the person low in frame so the top half is free. Graphics are few and clean: a magazine serif
title in white and one warm yellow, screen cards floating above the head, a yellow keyword caption, giant text
behind the person, native-looking Instagram UI for the CTA. Timed at 10 fps on the source reels: most overlays
hard-cut on and off; keywords blur in over 1-2 frames; nothing bounces.

    from cutroom import cinematic as C
    cv = C.grade(face_frame)
    C.serif_title(cv, k, "How I edit / *every video* with / *Claude Opus 5.5*")
    C.key_caption(cv, k, [("this is how you *stand out*", 0.2, 1.4)])

Every block is `block(canvas, k, ...)` with k in local seconds, chunk-safe like blocks.py.
Showcase: templates/shorts/cinematic_showcase.py
"""
import os, math, re
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from . import brand
from .core import W, H, font, SFD, SFT, SERIF, clamp, expo, inout, text_img, wrap
from .blocks import ss, place, rounded_rect, drop_shadow

YELLOW = brand.color("cinematic_accent", (246, 214, 92))
WHITE = (255, 255, 255)
IG_BLUE = (0, 149, 246)
SERIF_FALLBACK = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"

def serif(size, weight=520):
    """display serif: New York at a large optical size (high contrast); FreeSerif where it isn't installed."""
    if os.path.exists(SERIF): return font(SERIF, size, [min(120, size), weight, 0])
    return font(SERIF_FALLBACK, size)

def _parts(text):
    """'plain *accent* plain' -> [(word, accent)]"""
    out, acc = [], False
    for tok in re.split(r"(\*)", text):
        if tok == "*": acc = not acc; continue
        out += [(w_, acc) for w_ in tok.split()]
    return out

# ------------------------------------------------------------------ grade
@lru_cache(1)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - W / 2) / (W * 0.75), (yy - H * 0.45) / (H * 0.62))
    return np.clip(1 - 0.55 * np.clip(d - 0.35, 0, 1) ** 1.5, 0, 1)[..., None]

def grade(frame, strength=1.0):
    """teal-and-warm film grade: crushed blacks, teal shadows, warm highlights, 15% less saturation, vignette.
    Returns an RGBA canvas from any frame (resized to 1080x1920 if needed)."""
    im = frame.convert("RGB")
    if im.size != (W, H): im = ImageOps.fit(im, (W, H), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) / 255
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    a = lum + (a - lum) * (1 - 0.15 * strength)
    a = np.clip((a - 0.045 * strength) / (1 - 0.045 * strength), 0, 1) ** (1 + 0.12 * strength)
    sh, hi = (1 - lum) ** 2, lum ** 2
    a += strength * (sh * np.array([-0.02, 0.015, 0.035], np.float32) + hi * np.array([0.03, 0.01, -0.025], np.float32))
    a = np.clip(a * (1 - (1 - _vignette()) * strength), 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")

def _soft(im, k, d=0.4, blur=10):
    p = expo(clamp(k / d))
    return (im.filter(ImageFilter.GaussianBlur(blur * (1 - p))) if p < 0.97 else im), p

def _fade_out(k, out, d=0.25):
    return 1.0 if out is None or k <= out else 1 - clamp((k - out) / d)

# ------------------------------------------------------------------ titles and captions
def serif_title(canvas, k, text, cy=300, size=92, lh=1.08, accent=YELLOW, stagger=0.1, out=None):
    """magazine headline in white with *accent* words in yellow; ' / ' breaks lines. Each line fades up out of a
    light blur, 0.1s apart. Soft shadow so it holds over bright rooms."""
    lines = [l.strip() for l in text.split("/")]
    a_out = _fade_out(k, out)
    for i, ln in enumerate(lines):
        kk = k - i * stagger
        if kk <= 0 or a_out <= 0: continue
        words = _parts(ln); f = serif(size)
        imgs = [text_img(w_, f, fill=accent if acc else WHITE, shadow=120) for w_, acc in words]
        gap = size * 0.24; tot = sum(im.width - 2 * im.pad for im in imgs) + gap * (len(imgs) - 1)
        lay = Image.new("RGBA", (int(tot) + 120, int(size * 1.6) + 60), (0, 0, 0, 0)); x = 60
        for im in imgs:
            lay.alpha_composite(im, (int(x - im.pad), int(lay.height / 2 - im.height / 2))); x += im.width - 2 * im.pad + gap
        lay, p = _soft(lay, kk, 0.25, 8)
        place(canvas, lay, W / 2, cy + i * size * lh + (1 - p) * 10, 1, 0, clamp(kk / 0.15) * a_out)

def _phrase_at(phrases, k):
    for txt, t0, t1 in phrases:
        if t0 <= k < t1: return txt, t0, t1
    return None

def serif_caption(canvas, k, phrases, cy=1330, size=54, width=900, accent=YELLOW):
    """quiet sentence captions in white serif with a soft shadow (@raycfu). phrases = [(text, t0, t1)];
    *word* marks the accent. Fades 0.12s in and out."""
    cur = _phrase_at(phrases, k)
    if not cur: return
    txt, t0, t1 = cur; a = clamp((k - t0) / 0.12) * clamp((t1 - k) / 0.12)
    f = serif(size, 480); words = _parts(txt)
    lines, line, lw = [], [], 0
    for w_, acc in words:
        ww = f.getlength(w_ + " ")
        if line and lw + ww > width: lines.append(line); line, lw = [], 0
        line.append((w_, acc)); lw += ww
    if line: lines.append(line)
    for i, ln in enumerate(lines):
        imgs = [text_img(w_, f, fill=accent if acc else WHITE, shadow=150) for w_, acc in ln]
        gap = f.getlength(" "); tot = sum(im.width - 2 * im.pad for im in imgs) + gap * (len(imgs) - 1)
        x = W / 2 - tot / 2; y = cy + (i - (len(lines) - 1) / 2) * size * 1.25
        for im in imgs:
            place(canvas, im, x + (im.width - 2 * im.pad) / 2, y, 1, 0, a); x += im.width - 2 * im.pad + gap

def key_caption(canvas, k, phrases, cy=1020, size=50, scale=2.1, accent=YELLOW):
    """@tenfoldmarc's caption: a short lowercase phrase in tight white bold; the *key* word sits on its own line,
    twice as big, in yellow. The phrase hard-cuts on; the key word blur-fades in over 2 frames. A soft dark
    gradient sits behind the bottom half so it reads over any room."""
    cur = _phrase_at(phrases, k)
    if not cur: return
    canvas.alpha_composite(_floor())
    txt, t0, t1 = cur; a = 1.0
    m = re.match(r"(.*?)\*(.+?)\*(.*)", txt)
    before, key, after = (m.group(1).strip(), m.group(2).strip(), m.group(3).strip()) if m else (txt, "", "")
    fs, fk = font(SFD("Bold"), size), font(SFD("Heavy"), int(size * scale))
    rows = [(r, fs, WHITE) for r in [before] if r] + ([(key, fk, accent)] if key else []) + [(r, fs, WHITE) for r in [after] if r]
    hs = [f.size * 1.08 for _, f, _ in rows]; y = cy - sum(hs) / 2
    for (r, f, col), h_ in zip(rows, hs):
        im = text_img(r, f, fill=col, tracking=-0.03, shadow=160)
        if f is fk:
            p = clamp((k - t0) / 0.07)
            if p < 1: im = im.filter(ImageFilter.GaussianBlur(10 * (1 - p)))
            place(canvas, im, W / 2, y + h_ / 2, 1, 0, p)
        else: place(canvas, im, W / 2, y + h_ / 2, 1, 0, a)
        y += h_

@lru_cache(1)
def _floor():
    g = np.clip((np.arange(H, dtype=np.float32) - H * 0.42) / (H * 0.5), 0, 1) ** 1.4 * 150
    a = np.repeat(g[:, None], W, axis=1).astype(np.uint8)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray(a, "L")); return im

def headline(canvas, k, text, cy=330, size=170, color=YELLOW, d=0.07, dim=0.4, out=None):
    """@tenfoldmarc's 'stand out': on the word, the whole shot drops darker and greyer while one big yellow word
    blurs in over 2 frames; it hard-cuts off at `out`."""
    if k <= 0 or (out is not None and k >= out): return
    if dim:
        g = canvas.convert("L").convert("RGBA")
        canvas.alpha_composite(Image.blend(canvas, g, 0.6).point(lambda v: int(v * (1 - dim))))
    im = text_img(text, font(SFD("Heavy"), size), fill=color, tracking=-0.035, shadow=140)
    p = clamp(k / d)
    if p < 1: im = im.filter(ImageFilter.GaussianBlur(18 * (1 - p)))
    place(canvas, im, W / 2, cy, 1, 0, p)

def odometer(canvas, k, a, b, cy=330, size=260, color=YELLOW, dur=0.5, digits=2, label=None):
    """a number rolling from a to b like a car odometer: each digit is a strip of 0-9 that scrolls (@tenfoldmarc
    rolls 00 -> 26 in 5 frames), then holds."""
    if k <= 0: return
    f = font(SFD("Heavy"), size); cw = int(f.getlength("0")) + 6; ch = int(size * 1.1)
    v = a + (b - a) * inout(clamp(k / dur))
    lay = Image.new("RGBA", (cw * digits, ch), (0, 0, 0, 0))
    for i in range(digits):
        pv = 10 ** (digits - 1 - i)
        d0 = int(v // pv) % 10
        frac = v / pv - v // pv if pv == 1 else clamp(v % pv - (pv - 1))
        col = Image.new("RGBA", (cw, ch * 2), (0, 0, 0, 0)); dc = ImageDraw.Draw(col)
        dc.text((cw / 2, ch / 2), str(d0), font=f, fill=color, anchor="mm"); dc.text((cw / 2, ch * 1.5), str((d0 + 1) % 10), font=f, fill=color, anchor="mm")
        lay.alpha_composite(col.crop((0, int(frac * ch), cw, int(frac * ch) + ch)), (i * cw, 0))
    sh = drop_shadow(lay, 14, 140)
    canvas.alpha_composite(sh, (int(W / 2 - sh.width / 2), int(cy - sh.height / 2 + 4)))
    canvas.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(cy - ch / 2)))
    if label: place(canvas, text_img(label, font(SFD("Bold"), 56), fill=WHITE, shadow=150), W / 2, cy + ch / 2 + 40)

def hook_box(canvas, k, text, cy=250, size=58, width=900, color=YELLOW, out=None):
    """@simonbeard's hook: a near-black rounded box with the line in bold yellow, there from the first frame."""
    f = font(SFD("Bold"), size); lines = [l.strip() for l in text.split("/")] if "/" in text else wrap(text, f, width - 100)
    lh = int(size * 1.22); bw = int(max(f.getlength(l) for l in lines)) + 96; bh = len(lines) * lh + 64
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, bw * s - 1, bh * s - 1), 26 * s, fill=(10, 10, 10, 228)), bw, bh)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines): d.text((bw / 2, 32 + i * lh + lh / 2), l, font=f, fill=color, anchor="mm")
    if k >= 0: place(canvas, im, W / 2, cy, 1, 0, clamp(k / 0.06) * _fade_out(k, out, 0.15))

# ------------------------------------------------------------------ screens in the room
def float_card(canvas, k, img, cx=540, cy=420, w=860, radius=26, source=None, drift=14, dur=3.0, out=None):
    """a screenshot or clip floating above the head: rounded, thin light edge, deep soft shadow. It fades up out
    of a blur and drifts up `drift` px over `dur`. source = small 'via @x' tag on its top-left corner."""
    if k <= 0: return
    h_ = int(img.height * w / img.width)
    card = rounded_rect(img.convert("RGB").resize((w, h_), Image.LANCZOS), radius)
    edge = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), radius * s, outline=(255, 255, 255, 60), width=2 * s), w, h_)
    card.alpha_composite(edge)
    if source:
        f = font(SFT("Semibold"), 22); tw = int(f.getlength(source)) + 30
        tg = ss(lambda d, s: d.rounded_rectangle((0, 0, tw * s - 1, 40 * s - 1), 12 * s, fill=(0, 0, 0, 170)), tw, 40)
        ImageDraw.Draw(tg).text((15, 20), source, font=f, fill=(235, 235, 235), anchor="lm"); card.alpha_composite(tg, (16, 16))
    card, p = _soft(card, k, 0.12, 10)
    a = clamp(k / 0.07) * _fade_out(k, out, 0.07)
    place(canvas, card, cx, cy - drift * clamp(k / dur), 1, 0, a, shadow=(0, 30, 44, 200))

def behind_word(canvas, k, word, person, cy=700, size=400, color=WHITE, stagger=0.03, out=None):
    """giant letters between the wall and the person: they rise in one by one, then `person` (this frame's
    cut-out: the graded frame with the person mask as alpha) is drawn back on top so the head and arms cross
    in front."""
    fit = font(SFD("Heavy"), 100); size = min(size, int(100 * (W - 60) / (fit.getlength(word) * 0.96)))
    f = font(SFD("Heavy"), size); a_out = _fade_out(k, out)
    widths = [f.getlength(c) for c in word]; tr = -0.04 * size
    tot = sum(widths) + tr * (len(word) - 1); x = W / 2 - tot / 2
    for i, c in enumerate(word):
        kk = k - i * stagger
        if kk > 0 and a_out > 0:
            im = text_img(c, f, fill=color)
            p = expo(clamp(kk / 0.2))
            place(canvas, im, x + widths[i] / 2, cy + (1 - p) * 60, 1, 0, clamp(kk / 0.08) * a_out)
        x += widths[i] + tr
    if person is not None: canvas.alpha_composite(person)

def cutout(frame_rgba, mask):
    """the person from a graded frame, using the engine's person mask video (any size, L or RGB)."""
    m = mask.convert("L")
    if m.size != frame_rgba.size: m = m.resize(frame_rgba.size, Image.BILINEAR)
    out = frame_rgba.copy(); out.putalpha(m.filter(ImageFilter.GaussianBlur(1.2))); return out

def spotlight(canvas, k, cx=540, cy=900, r=430, dim=0.82, d=0.4):
    """the room drops to near black except a soft pool of light on the person (@atheef_abdul_rahman)."""
    if k <= 0: return
    a = inout(clamp(k / d)) * dim
    m = _spot_mask(int(cx), int(cy), int(r))
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 255)); lay.putalpha(m.point(lambda v: int(v * a)))
    canvas.alpha_composite(lay)

@lru_cache(4)
def _spot_mask(cx, cy, r):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - cx) / r, (yy - cy) / (r * 1.25))
    return Image.fromarray((np.clip((d - 0.55) / 0.7, 0, 1) * 255).astype(np.uint8), "L")

# ------------------------------------------------------------------ native Instagram CTA
def _avatar(img, s):
    if img is None:
        return ss(lambda d, sc: d.ellipse((0, 0, s * sc - 1, s * sc - 1), fill=(120, 120, 128, 255)), s, s)
    im = ImageOps.fit(img.convert("RGB"), (s, s), Image.BICUBIC).convert("RGBA")
    im.putalpha(ss(lambda d, sc: d.ellipse((0, 0, s * sc - 1, s * sc - 1), fill=(255, 255, 255, 255)), s, s).split()[3]); return im

def comment_bar(canvas, k, word, avatar=None, cy=1500, w=940, t_type=0.4, cps=10, t_post=None):
    """Instagram's dark 'Add a comment…' bar: the keyword types in about a letter a frame, 'Post' turns blue,
    and dims for a beat at t_post."""
    if k <= 0: return
    h_ = 108; f = font(SFT("Regular"), 36); fw = font(SFT("Bold"), 38)
    bar = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), h_ * s / 2, fill=(28, 28, 30, 238), outline=(64, 64, 68, 255), width=2 * s), w, h_)
    bar.alpha_composite(_avatar(avatar, 64), (24, 22)); d = ImageDraw.Draw(bar)
    n = int(clamp((k - t_type) * cps, 0, len(word)))
    if n: d.text((112, h_ / 2), word[:n], font=fw, fill=WHITE, anchor="lm")
    else: d.text((112, h_ / 2), "Add a comment…", font=f, fill=(142, 142, 148), anchor="lm")
    if n < len(word) and (k * 2.2) % 1 < 0.6:
        x = 114 + fw.getlength(word[:n]); d.rectangle((x, h_ / 2 - 24, x + 3, h_ / 2 + 24), fill=IG_BLUE)
    posted = t_post is not None and k >= t_post
    col = IG_BLUE if n == len(word) else (70, 90, 120)
    if posted: col = tuple(int(c * (0.6 + 0.4 * clamp((k - t_post) / 0.25))) for c in IG_BLUE)
    d.text((w - 40, h_ / 2), "Post", font=font(SFT("Semibold"), 34), fill=col, anchor="rm")
    e = expo(k / 0.4)
    place(canvas, bar, W / 2, cy + (1 - e) * 30, 1, 0, clamp(k / 0.2), shadow=(0, 16, 30, 160))

def follow_row(canvas, k, handle, avatar=None, cy=1500, w=860, t_tap=1.0):
    """profile row with the blue Follow button; at t_tap it presses and becomes a grey 'Following'."""
    if k <= 0: return
    h_ = 140
    row = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h_ * s - 1), 34 * s, fill=(22, 22, 24, 236), outline=(60, 60, 64, 255), width=2 * s), w, h_)
    row.alpha_composite(_avatar(avatar, 88), (26, 26)); d = ImageDraw.Draw(row)
    d.text((136, h_ / 2 - 18), handle, font=font(SFT("Semibold"), 36), fill=WHITE, anchor="lm")
    d.text((136, h_ / 2 + 24), "Claude Code video editing", font=font(SFT("Regular"), 26), fill=(150, 150, 156), anchor="lm")
    done = k >= t_tap + 0.12
    label, fill, fg = ("Following", (54, 54, 58), WHITE) if done else ("Follow", IG_BLUE, WHITE)
    fb = font(SFT("Semibold"), 32); bw = int(fb.getlength("Following")) + 64; bh = 72
    btn = ss(lambda dd, s: dd.rounded_rectangle((0, 0, bw * s - 1, bh * s - 1), 18 * s, fill=fill + (255,)), bw, bh)
    ImageDraw.Draw(btn).text((bw / 2, bh / 2), label, font=fb, fill=fg, anchor="mm")
    press = math.exp(-(k - t_tap) * 10) if t_tap <= k < t_tap + 0.6 else 0
    place(row, btn, w - 30 - bw / 2, h_ / 2, 1 - 0.1 * press)
    e = expo(k / 0.4)
    place(canvas, row, W / 2, cy + (1 - e) * 30, 1, 0, clamp(k / 0.2), shadow=(0, 16, 30, 160))
