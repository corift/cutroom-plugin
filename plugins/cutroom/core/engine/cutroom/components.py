"""Reusable graphic components. Each returns/draws onto RGBA and takes a local time `k`
(seconds since the component started) so it can be dropped anywhere on the timeline.

Motion rule: per-element cascade (each word / row / bar starts on its own offset), never a
whole block fading in at once. Ease-outs only (expo/cubic), 0.3-0.5 s.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from . import brand
from .core import (W, H, font, serif, text_img, paste, reveal, expo, cubic, clamp, wrap,
                   SFD, SFT, CODE, MONO, WHITE, GREY, DIM, INK, PAPER, DARK, with_alpha)

ACCENT = brand.color("highlight", (224, 122, 88))   # default: Claude orange (muted)
HILITE = brand.color("marker", (255, 214, 92))      # default: rpn-style marker yellow

# ------------------------------------------------------------------ editorial serif titles
def _words(text, f, fill):
    return [text_img(w, f, fill=fill, shadow=150) for w in text.split(" ")]

_tc = {}
def serif_title(canvas, k, text, cy, size=78, width=900, fill=WHITE, a=1.0, weight=470):
    """Centered New York title, wrapped, words cascading in (fade + 14px rise, 55 ms apart)."""
    key = (text, size, width, fill, weight)
    if key not in _tc:
        f = serif(size, weight)
        lines = wrap(text, f, width)
        _tc[key] = (f, [(_words(ln, f, fill), f.getlength(ln)) for ln in lines])
    f, lines = _tc[key]
    lh = int(size * 1.08)
    y = cy - lh * len(lines) / 2
    i = 0
    sp = f.getlength(" ")
    for ims, lw in lines:
        x = W / 2 - lw / 2
        for im in ims:
            p = (k - i * 0.055) / 0.45
            if p > 0:
                paste(canvas, im, x - im.pad, y - im.pad + (1 - expo(p)) * 14, cubic(p) * a)
            x += im.width - 2 * im.pad + sp - 4
            i += 1
        y += lh

def chapter(canvas, k, num, text, cy=430, a=1.0):
    """'1. It makes videos' — the numbered section title rpn uses."""
    serif_title(canvas, k, f"{num}. {text}", cy, size=74, a=a)

# ------------------------------------------------------------------ floating images / logos
def float_img(canvas, k, img, cx, cy, a=1.0, drift=10):
    """Small floating element: rises in, then drifts slowly. Soft drop shadow."""
    p = expo(k / 0.5)
    y = cy + (1 - p) * 40 - drift * clamp(k / 4)
    sh = Image.new("RGBA", (img.width + 80, img.height + 80), (0, 0, 0, 0))
    m = img.split()[3].point(lambda v: v * 120 // 255)
    sh.paste(Image.new("RGBA", img.size, (0, 0, 0, 255)), (40, 52), m)
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    paste(canvas, sh, cx - sh.width / 2, y - sh.height / 2, cubic(p) * a * 0.8)
    paste(canvas, img, cx - img.width / 2, y - img.height / 2, cubic(p) * a)

def tile(img, size, r=36, bg=(250, 250, 250)):
    """App-icon style tile holding a logo."""
    t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(t).rounded_rectangle((0, 0, size - 1, size - 1), r, fill=bg + (255,))
    lg = img.resize((int(size * 0.62),) * 2, Image.LANCZOS)
    t.alpha_composite(lg, ((size - lg.width) // 2, (size - lg.height) // 2))
    return t

# ------------------------------------------------------------------ panel backgrounds
def dark_panel(w, h, grid=True, glow=True):
    im = Image.new("RGBA", (w, h), DARK + (255,))
    d = ImageDraw.Draw(im)
    if grid:
        for gx in range(60, w, 96): d.line([(gx, 0), (gx, h)], fill=(255, 255, 255, 9))
        for gy in range(48, h, 96): d.line([(0, gy), (w, gy)], fill=(255, 255, 255, 6))
    # soft top glow (kallaway-style lit document feel)
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((w * 0.1, -h * 0.5, w * 0.9, h * 0.45), fill=ACCENT + (38,))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(120)))
    return im

def kicker(txt, col=GREY, size=26):
    return text_img(txt.upper(), font(MONO, size), fill=col, tracking=0.12)

# ------------------------------------------------------------------ bar comparison
def bars_panel(k, w, h, title, groups, source=None, grid=True, gap=280):
    """groups: [(name, subtitle, [(label, value, display, max, highlight), ...]), ...]"""
    im = dark_panel(w, h, grid=grid)
    d = ImageDraw.Draw(im)
    x = 72
    y = 60
    if title:
        t = text_img(title, font(SFD("Bold"), 64))
        reveal(im, t, x - t.pad, 80, k / 0.4)
        y = 210
    for gi, (name, sub, rows) in enumerate(groups):
        gk = k - 0.25 - gi * 0.45
        n = text_img(name, font(SFD("Semibold"), 44))
        reveal(im, n, x - n.pad, y, gk / 0.35)
        s = kicker(sub, size=24)
        reveal(im, s, x - s.pad, y + 60, (gk - 0.05) / 0.35)
        ry = y + 118
        for ri, (lab, val, disp, mx, hi) in enumerate(rows):
            rk = gk - 0.12 - ri * 0.16
            col = ACCENT if hi else (86, 86, 92)
            lt = text_img(lab, font(SFT("Semibold" if hi else "Medium"), 30), fill=WHITE if hi else GREY)
            paste(im, lt, x - lt.pad, ry + 4 - lt.pad, cubic(rk / 0.3))
            full = (w - 2 * x - 400) * val / mx
            p = expo(rk / 0.9)
            if p > 0:
                d.rounded_rectangle((x + 220, ry, x + 220 + max(8, full * p), ry + 44), 7, fill=col + (255,))
                shown = val * p
                num = f"{shown:.1f}%" if "%" in disp else f"{int(round(shown))}"
                nt = text_img(num, font(SFD("Semibold"), 38), fill=WHITE if hi else GREY)
                paste(im, nt, x + 220 + full * p + 16 - nt.pad, ry - 2 - nt.pad, cubic(rk / 0.3))
            ry += 64
        y += gap
    if source:
        s = text_img(source, font(SFT("Regular"), 22), fill=(110, 110, 116))
        paste(im, s, x - s.pad, h - 60 - s.pad, cubic((k - 1.2) / 0.4))
    return im

# ------------------------------------------------------------------ terminal mock
def terminal_panel(k, w, h, logo_img, title, prompt, lines, type_cps=38, bare=False, path="~/videos/opus-launch"):
    """A Claude-Code-like terminal window: prompt types out, then progress lines cascade."""
    im = Image.new("RGBA", (w, h), (20, 18, 17, 255))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-w * 0.2, h * 0.4, w * 0.7, h * 1.4), fill=ACCENT + (40,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(im)
    mx, my, mw, mh = 60, 90, w - 120, h - 170
    p = expo(k / 0.5)
    oy = (1 - p) * 30
    if bare:
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); mx, my, mw, mh, oy = 0, 0, w, h, 0
    win = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    wd = ImageDraw.Draw(win)
    wd.rounded_rectangle((0, 0, mw - 1, mh - 1), 22, fill=(30, 28, 27, 245), outline=(70, 64, 60, 255), width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        wd.ellipse((26 + i * 30, 24, 44 + i * 30, 42), fill=c + (255,))
    fc, fcb = font(CODE, 36), font(CODE, 36)
    win.alpha_composite(logo_img.resize((54, 54), Image.LANCZOS), (34, 72))
    wd.text((104, 82), title, font=font(SFT("Semibold"), 30), fill=(240, 235, 230))
    wd.text((104, 118), path, font=font(CODE, 22), fill=(140, 130, 124))
    wd.line([(30, 164), (mw - 30, 164)], fill=(60, 56, 53), width=2)
    # prompt box
    typed = prompt[:int(max(0, k - 0.35) * type_cps)]
    wd.rounded_rectangle((30, 188, mw - 30, 320), 14, outline=(90, 84, 80), width=2)
    wd.text((52, 206), ">", font=fcb, fill=ACCENT)
    for li, ln in enumerate(wrap(typed, fc, mw - 140)[:2]):
        wd.text((86, 206 + li * 48), ln, font=fc, fill=(235, 230, 225))
    if int(k * 2.5) % 2 == 0 and len(typed) < len(prompt):
        tw = fc.getlength(wrap(typed, fc, mw - 140)[-1] if typed else "")
        nl = max(0, len(wrap(typed, fc, mw - 140)) - 1)
        wd.rectangle((88 + tw, 210 + nl * 48, 106 + tw, 246 + nl * 48), fill=(235, 230, 225))
    t_done = 0.35 + len(prompt) / type_cps + 0.25
    y = 360
    for i, (sym, txt) in enumerate(lines):
        lk = k - t_done - i * 0.32
        if lk <= 0: break
        a = int(255 * cubic(lk / 0.25))
        col = ACCENT if sym == "●" else (120, 200, 130) if sym == "✓" else (150, 142, 136)
        wd.text((52, y), sym, font=font(SFT("Semibold"), 34), fill=col + (a,))
        wd.text((96, y), txt, font=fc, fill=(220, 214, 208, a))
        y += 62
    paste(im, win, mx, my + oy, 1.0 if bare else cubic(k / 0.35))
    return im

# ------------------------------------------------------------------ checklist
def check_mark(d, x, y, p, col=ACCENT, s=1.0, width=7, a=255):
    pts = [(x, y + 18 * s), (x + 16 * s, y + 34 * s), (x + 44 * s, y)]
    if p <= 0: return
    if p < 0.4:
        q = p / 0.4; seg = [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * q, pts[0][1] + (pts[1][1] - pts[0][1]) * q)]
    else:
        q = min(1, (p - 0.4) / 0.6); seg = [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * q, pts[1][1] + (pts[2][1] - pts[1][1]) * q)]
    d.line(seg, fill=col + (a,), width=width, joint="curve")

def checklist_panel(t, w, h, heading, items, y0=300, grid=True):
    """items: [(t_on, text)] absolute times; heading reveals at first item - 1.4s."""
    im = dark_panel(w, h, grid=grid, glow=grid)
    d = ImageDraw.Draw(im)
    x = 60 if not heading else 90
    k0 = t - (items[0][0] - 1.4)
    if heading:
        hd = kicker(heading, col=(200, 190, 182), size=28)
        reveal(im, hd, x - hd.pad, y0 - 100, k0 / 0.4)
    for i, (ts, txt) in enumerate(items):
        y = y0 + i * 150
        k = t - ts
        row = Image.new("RGBA", (w - 2 * x, 118), (0, 0, 0, 0))
        rd = ImageDraw.Draw(row)
        on = k > 0
        rd.rounded_rectangle((0, 0, row.width - 1, 117), 20, fill=(255, 255, 255, 14 if on else 7),
                             outline=(255, 255, 255, 40 if on else 18), width=2)
        rd.rounded_rectangle((28, 34, 78, 84), 12, outline=(ACCENT if on else (90, 90, 96)) + (255,), width=3)
        check_mark(rd, 40, 44, expo(k / 0.35), s=0.62, width=6)
        txt_im = text_img(txt, font(SFD("Semibold"), 56), fill=WHITE if on else (110, 110, 116))
        row.alpha_composite(txt_im, (110 - txt_im.pad, 59 - txt_im.height // 2))
        pk = k0 - 0.15 - i * 0.12
        paste(im, row, x, y + (1 - expo(pk / 0.5)) * 30, cubic(pk / 0.35))
    return im

# ------------------------------------------------------------------ documents (paper)
def render_doc(blocks, fg, width=920, sizes=(44, 44, 68, 29)):
    """blocks: [(kind, text)] kind in p/h/H/c. Returns (image, headline marks [(y, w)])."""
    fp, fh, fH, fc = (serif(sizes[0], 430), serif(sizes[1], 720), serif(sizes[2], 680), font(CODE, sizes[3]))
    im = Image.new("RGBA", (width, 3000), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y, marks = 0, []
    for kind, txt in blocks:
        if kind == "c":
            d.text((0, y), txt, font=fc, fill=(110, 105, 100)); y += int(sizes[3] * 1.5)
            continue
        f, lh, gap = {"p": (fp, int(sizes[0] * 1.42), 24), "h": (fh, int(sizes[1] * 1.42), 8),
                      "H": (fH, int(sizes[2] * 1.2), 28)}[kind]
        for ln in wrap(txt, f, width):
            d.text((0, y), ln, font=f, fill=fg)
            if kind == "H": marks.append((y, f.getlength(ln)))
            y += lh
        y += gap
    return im.crop((0, 0, width, y)), marks

def model_tag(name, active, size=40):
    f = font(SFD("Semibold"), size)
    im = Image.new("RGBA", (int(f.getlength(name)) + 60, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 22, 22, 42), fill=(ACCENT if active else (170, 165, 160)) + (255,))
    d.text((40, 32), name, font=f, fill=INK if active else (130, 125, 120), anchor="lm")
    return im

def chip(txt):
    f = font(SFT("Semibold"), 30)
    im = Image.new("RGBA", (int(f.getlength(txt)) + 92, 62), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 61), 31, fill=(255, 255, 255, 255), outline=(225, 220, 212, 255), width=2)
    check_mark(d, 24, 21, 1.0, s=0.6, width=5)
    d.text((66, 31), txt, font=f, fill=INK, anchor="lm")
    return im

def paper_fade(w, h, col=PAPER):
    g = Image.new("RGBA", (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for yy in range(h): gd.line([(0, yy), (w, yy)], fill=col + (int(255 * yy / h),))
    return g

# ================================================================== @kallaway look
# near-black dotted canvas, white-outlined glowing cards, red highlight-box headers that type on.
RED = brand.color("accent", (214, 34, 34))
SERIF_IT = brand.font("serif_italic", "/System/Library/Fonts/NewYorkItalic.ttf")

def serif_it(size, weight=500):
    return font(SERIF_IT, size, [min(40, max(18, size // 3)), weight, 0])

_dots = {}
def dotted_bg(w, h, step=22, col=(255, 255, 255, 16), base=(8, 8, 9)):
    k = (w, h)
    if k not in _dots:
        im = Image.new("RGBA", (w, h), base + (255,))
        d = ImageDraw.Draw(im)
        for y in range(step // 2, h, step):
            for x in range(step // 2, w, step):
                d.point((x, y), fill=col); d.point((x + 1, y), fill=col)
        _dots[k] = im
    return _dots[k].copy()

def glow_card(img, r=26, border=(255, 255, 255, 200), glow=90, blur=26):
    """Wrap content in a rounded, white-outlined card with a soft white outer glow."""
    pad = blur * 2
    w, h = img.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    g = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((pad, pad, pad + w - 1, pad + h - 1), r, outline=(255, 255, 255, glow), width=10)
    out.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    body = img.convert("RGBA"); body.putalpha(ImageChops.multiply(body.split()[3], m))
    out.alpha_composite(body, (pad, pad))
    ImageDraw.Draw(out).rounded_rectangle((pad, pad, pad + w - 1, pad + h - 1), r, outline=border, width=3)
    out.pad = pad
    return out

def red_header(canvas, k, text, cx, y, size=52, cps=32, sub=None, sub_size=44, italic=True):
    """Kallaway header: white italic serif inside a red box, typed on; optional bold sub-line."""
    f = serif_it(size) if italic else font(SFD("Bold"), size)
    n = int(max(0, k) * cps)
    shown = text[:n]
    if not shown: return
    full_w = f.getlength(text)
    x0 = cx - full_w / 2
    d = ImageDraw.Draw(canvas)
    bw = f.getlength(shown)
    asc, desc = f.getmetrics()
    d.rectangle((x0 - 14, y - 4, x0 + bw + 14, y + asc + desc - 2), fill=RED + (255,))
    d.text((x0, y), shown, font=f, fill=WHITE)
    if sub and n >= len(text):
        sk = k - len(text) / cps
        fs = font(SFD("Bold"), sub_size)
        sn = int(max(0, sk) * cps)
        d.text((cx - fs.getlength(sub) / 2, y + asc + desc + 6), sub[:sn], font=fs, fill=WHITE)

def press(canvas, k, x, y, size=1.0, col=(255, 255, 255)):
    """Visible click for a `click` SFX cue: a cursor arrives (k<0), presses at k=0 (dips + ring
    bursts), releases. Call with k = t - cue_time so the SOUND and the PRESS share one number.
    Draws nothing outside -0.35 < k < 0.45. Clicks with no visible press read as broken (user v5)."""
    if not -0.35 < k < 0.45: return
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * min(1, (k + 0.35) / 0.12) * min(1, (0.45 - k) / 0.15))
    if k >= 0:                                            # ring burst
        p = expo(k / 0.35)
        r = (14 + 46 * p) * size
        d.ellipse((x - r, y - r, x + r, y + r), outline=col + (int(a * (1 - p)),), width=max(2, int(5 * size)))
    s = size * (0.86 if 0 <= k < 0.09 else 1.0)           # press dip
    ox = (1 - expo((k + 0.35) / 0.3)) * 60 * size         # arrive from lower-right
    cx, cy = x + ox, y + ox
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    poly = [(cx + px * s * 1.3, cy + py * s * 1.3) for px, py in pts]
    d.polygon(poly, fill=(255, 255, 255, a), outline=(0, 0, 0, a))
    canvas.alpha_composite(layer)
