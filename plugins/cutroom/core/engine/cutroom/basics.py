"""Basics: the core pack look every new account starts with (2026-11-03, from this week's top "edit video with
Claude" reels: jesseeisenbart, kallaway, v.i.s.h.ai, favoritetechgal, fabianocarvalhojr).

Near-black page, graphic on top, the face filling the bottom, a black mono caption chip on the seam. Type is
narrow heavy Archivo in caps, one Instrument Serif italic word for emphasis, JetBrains Mono for labels. One accent
colour (the brand kit's "accent", sand by default); no blue, no gradients, no glow.

    from cutroom import basics as Bx
    cv = Bx.canvas()
    Bx.step(cv, k, 1, "Cut the pauses")
    Bx.prompt(cv, k, "Cut every pause longer than half a second", file="raw.mp4", t_check=1.8)
    Bx.face_panel(cv, face_frame)
    Bx.caption(cv, k, [("saved", 0.1), ("me", 0.35), ("hours", 0.6)])

Every block is `block(canvas, k, ...)` with k in local seconds, chunk-safe like blocks.py.
"""
import math, os
from PIL import Image, ImageDraw, ImageOps
from . import brand
from .core import W, H, ASSETS, font, clamp, expo, inout, wrap
from .blocks import ss, place, rounded_rect, _partial

ACCENT = brand.color("accent", (214, 190, 150))
PAGE = (18, 18, 17)
CARD = (29, 28, 26)
EDGE = (52, 50, 46)
INK = (242, 239, 232)
MUTED = (141, 137, 127)
FAINT = (78, 75, 70)
SHADE = (38, 37, 35)
BLACK = (11, 11, 11)
SEAM = 1040
ZONE_CY = 500
FACE_BOX = (0, SEAM, W, H)

_DIR = os.path.join(ASSETS, "fonts")
HEAD = brand.font("basics_display", os.path.join(_DIR, "Archivo[wdth,wght].ttf"))
SERIF = brand.font("serif_italic", os.path.join(_DIR, "InstrumentSerif-Italic.ttf"))
CODE = os.path.join(_DIR, "JetBrainsMono[wght].ttf")


def head(size, weight=800, width=72):
    """narrow heavy display face; set words in caps."""
    return font(HEAD, size, [weight, width])


def serif(size):
    return font(SERIF, size)


def mono(size, weight=500):
    return font(CODE, size, [weight])


def mix(a, b, p):
    return tuple(int(a[i] + (b[i] - a[i]) * p) for i in range(3))


def on_accent():
    return BLACK if sum(ACCENT) > 380 else INK


def canvas(frame=0):
    return Image.new("RGBA", (W, H), PAGE + (255,))


def face_panel(canvas, frame, box=FACE_BOX, focus=0.3, radius=0):
    """the talking head filling the bottom of the frame, with a hairline seam on top."""
    x0, y0, x1, y1 = box
    im = ImageOps.fit(frame.convert("RGB"), (x1 - x0, y1 - y0), Image.BICUBIC, centering=(0.5, focus)).convert("RGBA")
    if radius:
        im = rounded_rect(im, radius)
    canvas.alpha_composite(im, (x0, y0))
    if not radius:
        ImageDraw.Draw(canvas).line([(x0, y0), (x1, y0)], fill=EDGE + (255,), width=2)


def _chunks(words, per=3, gap=0.35):
    out, cur = [], []
    for i, (w_, t) in enumerate(words):
        if cur and (len(cur) >= per or t - words[i - 1][1] > gap):
            out.append(cur)
            cur = []
        cur.append((w_, t))
    if cur:
        out.append(cur)
    return out


def caption(canvas, k, words, cy=SEAM, size=34, per=3, hold=0.6):
    """black chip on the seam, mono caps, `per` words at a time; the word being said turns the accent colour.
    words = [(word, t)] in local s."""
    chunks = _chunks(words, per)
    for i, ch in enumerate(chunks):
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else ch[-1][1] + hold
        if ch[0][1] - 0.15 <= k < end:
            break
    else:
        return
    f = mono(size, 600)
    gap = f.getlength(" ")
    parts = [(w_.upper(), t) for w_, t in ch]
    tot = sum(f.getlength(w_) for w_, _ in parts) + gap * (len(parts) - 1)
    pw, ph = int(tot + 56), int(size * 1.9)
    chip = ss(lambda d, s: d.rounded_rectangle((0, 0, pw * s - 1, ph * s - 1), 14 * s, fill=BLACK + (255,)), pw, ph)
    d = ImageDraw.Draw(chip)
    x = 28
    for i, (w_, t) in enumerate(parts):
        nxt = parts[i + 1][1] if i + 1 < len(parts) else end
        col = ACCENT if t <= k < nxt else INK if k >= t else MUTED
        d.text((x, ph / 2), w_, font=f, fill=col, anchor="lm")
        x += f.getlength(w_) + gap
    place(canvas, chip, W / 2, cy)


def label(txt, size=26, col=MUTED, weight=500):
    f = mono(size, weight)
    txt = txt.upper()
    im = Image.new("RGBA", (int(f.getlength(txt) + len(txt) * size * 0.08) + 8, int(size * 1.5)), (0, 0, 0, 0))
    d, x = ImageDraw.Draw(im), 4
    for ch in txt:
        d.text((x, im.height / 2), ch, font=f, fill=col, anchor="lm")
        x += f.getlength(ch) + size * 0.08
    return im


def _card(w, h, radius=26):
    return ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=CARD + (255,),
                                               outline=EDGE + (255,), width=2 * s), w, h)


def enter(canvas, k, img, cx, cy, out=None):
    """the one entrance: on in 3 frames with a 10px rise, off in 2. What changes inside is the motion."""
    if k <= 0:
        return
    a = clamp(k / 0.1)
    e = expo(k / 0.14)
    if out is not None and k > out:
        a *= 1 - clamp((k - out) / 0.07)
    place(canvas, img, cx, cy + (1 - e) * 10, 1, 0, a)


def _words_line(d, x, y, parts, size, anchor="l"):
    """parts = [(text, accent)]; plain words in narrow caps, accent words in serif italic, baseline aligned."""
    fH, fS = head(size), serif(int(size * 1.12))
    items = [(t.upper() if not acc else t, fS if acc else fH, acc) for t, acc in parts]
    gap = size * 0.22
    tot = sum(f.getlength(t) for t, f, _ in items) + gap * (len(items) - 1)
    if anchor == "m":
        x -= tot / 2
    for t, f, acc in items:
        d.text((x, y), t, font=f, fill=ACCENT if acc else INK, anchor="ls")
        x += f.getlength(t) + gap
    return tot


def hook(canvas, k, lines, sub=None, cy=ZONE_CY, size=128, stagger=0.09):
    """the opening title, no card: big narrow caps, one serif italic accent word, each line rising in on its
    own. lines = [[("Claude edited", False)], [("this", False), ("entire", True)], [("video", False)]]."""
    lh = size * 0.98
    top = cy - lh * len(lines) / 2 + size * 0.8
    for i, parts in enumerate(lines):
        p = expo((k - i * stagger) / 0.35)
        if p <= 0:
            continue
        lay = Image.new("RGBA", (W, int(size * 1.6)), (0, 0, 0, 0))
        _words_line(ImageDraw.Draw(lay), W / 2, size * 1.15, parts, size, "m")
        lay.putalpha(lay.split()[3].point(lambda v: int(v * clamp(p * 1.4))))
        canvas.alpha_composite(lay, (0, int(top + i * lh - size * 1.15 + (1 - p) * 24)))
    if sub:
        a = clamp((k - len(lines) * stagger - 0.2) / 0.2)
        if a > 0:
            place(canvas, label(sub, 30), W / 2, top + (len(lines) - 1) * lh + size * 0.55, 1, 0, a)


def step(canvas, k, n, title, cx=W / 2, cy=210, size=84):
    """an accent 'STEP 01' tag and the step's title typing on beside it, in narrow caps."""
    if k <= 0:
        return
    tag = label(f"Step {n:02d}", 30, on_accent(), 600)
    pw, ph = tag.width + 28, int(size * 0.62)
    chip = ss(lambda d, s: d.rounded_rectangle((0, 0, pw * s - 1, ph * s - 1), 10 * s, fill=ACCENT + (255,)), pw, ph)
    chip.alpha_composite(tag, (14, (ph - tag.height) // 2))
    fT = head(size)
    full = title.upper()
    shown = full[:int(clamp((k - 0.15) * 34, 0, len(full)))]
    x = cx - (pw + 26 + fT.getlength(full)) / 2
    place(canvas, chip, x + pw / 2, cy, 0.9 + 0.1 * expo(k / 0.2), 0, clamp(k / 0.1))
    ImageDraw.Draw(canvas).text((x + pw + 26, cy + size * 0.36), shown, font=fT, fill=INK, anchor="ls")


def _send(card, x, y, press=0.0, active=True):
    bs = 66
    btn = ss(lambda d, s: d.ellipse((0, 0, bs * s - 1, bs * s - 1), fill=(ACCENT if active else FAINT) + (255,)), bs, bs)
    d = ImageDraw.Draw(btn)
    col = on_accent() if active else PAGE
    d.line([(33, 48), (33, 19)], fill=col, width=5)
    d.line([(21, 31), (33, 18), (45, 31)], fill=col, width=5, joint="curve")
    place(card, btn, x, y, 1 - 0.12 * press)


def _chip(name, checked):
    f = mono(28)
    w_, h_ = int(f.getlength(name)) + 110, 60
    im = ss(lambda d, s: d.rounded_rectangle((0, 0, w_ * s - 1, h_ * s - 1), 12 * s, fill=SHADE + (255,),
                                             outline=EDGE + (255,), width=2 * s), w_, h_)
    d = ImageDraw.Draw(im)
    d.text((24, h_ / 2), name, font=f, fill=INK, anchor="lm")
    if checked > 0:
        cx = w_ - 34
        d.rounded_rectangle((cx - 15, h_ / 2 - 15, cx + 15, h_ / 2 + 15), 6, fill=ACCENT)
        _tick(d, cx, h_ / 2, 15, checked, on_accent(), 4)
    return im


def _tick(d, cx, cy, r, p, col, width=5):
    seg = _partial([(cx - r * 0.45, cy), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.48, cy - r * 0.32)], p)
    if len(seg) > 1:
        d.line(seg, fill=col, width=width, joint="curve")


def prompt(canvas, k, text, cx=W / 2, cy=ZONE_CY, w=960, t_type=0.3, cps=26, file=None, t_file=0.0, t_check=None,
           t_send=None, title="Claude Code", out=None):
    """a prompt typing into a dark composer card with an accent caret, a file chip that ticks at t_check, and the
    send button pressing at t_send."""
    fT = font(HEAD, 44, [500, 100])
    lh = 60
    lines_full = wrap(text, fT, w - 96)
    h_ = 120 + len(lines_full) * lh + 120
    card = _card(w, h_).copy()
    card.alpha_composite(label(title, 24), (40, 34))
    d = ImageDraw.Draw(card)
    n = int(clamp((k - t_type) * cps, 0, len(text)))
    lines = wrap(text[:n], fT, w - 96) if n else []
    y0 = 104
    for i, ln in enumerate(lines):
        d.text((44, y0 + i * lh), ln, font=fT, fill=INK)
    if (n < len(text) or t_send is None or k < t_send) and (k * 2.2) % 1 < 0.62:
        last = lines[-1] if lines else ""
        x = 48 + fT.getlength(last)
        y = y0 + (max(1, len(lines)) - 1) * lh
        d.rectangle((x, y + 6, x + 5, y + 52), fill=ACCENT)
    by = h_ - 62
    if file and k >= t_file:
        c = _chip(file, clamp((k - t_check) / 0.3) if t_check is not None and k >= t_check else 0)
        place(card, c, 40 + c.width / 2, by, 1, 0, clamp((k - t_file) / 0.2))
    press = math.exp(-(k - t_send) * 9) if t_send is not None and t_send <= k < t_send + 0.6 else 0
    _send(card, w - 40 - 33, by, press, n > 0)
    enter(canvas, k, card, cx, cy, out)


def checklist(canvas, k, rows, title=None, cx=W / 2, cy=ZONE_CY, w=960, out=None):
    """rows tick one after another: the square fills with the accent, a tick draws, the text goes from dim to ink.
    rows = [(text, t)]."""
    rh = 118
    top = 110 if title else 40
    h_ = top + len(rows) * rh + 30
    card = _card(w, h_).copy()
    if title:
        card.alpha_composite(label(title, 24), (40, 36))
    d = ImageDraw.Draw(card)
    fT = head(56, 700)
    for i, (txt, t) in enumerate(rows):
        y = top + i * rh + rh / 2
        p = clamp((k - t) / 0.16)
        if i:
            d.line([(44, y - rh / 2), (w - 44, y - rh / 2)], fill=EDGE, width=2)
        box = (52, y - 26, 104, y + 26)
        if p > 0:
            d.rounded_rectangle(box, 8, fill=ACCENT)
            _tick(d, 78, y, 24, clamp((k - t - 0.06) / 0.2), on_accent(), 6)
        else:
            d.rounded_rectangle(box, 8, outline=FAINT, width=3)
        d.text((140, y + 20), txt.upper(), font=fT, fill=mix(FAINT, INK, max(p, 0.35)), anchor="ls")
    enter(canvas, k, card, cx, cy, out)


def counter(canvas, k, a, b, word="views", cx=W / 2, cy=ZONE_CY, t0=0.2, dur=1.2, suffix="+", sub=None):
    """a huge number counting up, the unit in serif italic under it, and an accent bar filling."""
    if k <= 0:
        return
    p = inout(clamp((k - t0) / dur))
    val = int(a + (b - a) * p)
    txt = f"{val:,}" + (suffix if p >= 1 else "")
    d = ImageDraw.Draw(canvas)
    al = int(255 * clamp(k / 0.12))
    if sub:
        d.text((cx, cy - 210), sub.upper(), font=mono(28), fill=MUTED + (al,), anchor="mm")
    d.text((cx, cy + 60), txt, font=head(250, 800, 64), fill=INK + (al,), anchor="ms")
    d.text((cx, cy + 150), word, font=serif(96), fill=ACCENT + (al,), anchor="ms")
    bx0, bx1, by = cx - 330, cx + 330, cy + 220
    d.rounded_rectangle((bx0, by - 5, bx1, by + 5), 5, fill=EDGE)
    d.rounded_rectangle((bx0, by - 5, bx0 + max(12, (bx1 - bx0) * p), by + 5), 5, fill=ACCENT)


def folder(canvas, k, root, children, cx=W / 2, cy=ZONE_CY, w=960, out=None):
    """a project folder as a mono tree: the root in the accent colour, children appearing one by one.
    children = [(name, t)]."""
    rh = 86
    h_ = 140 + len(children) * rh + 30
    card = _card(w, h_).copy()
    d = ImageDraw.Draw(card)
    f = mono(42)
    d.text((52, 84), "▸ " + root, font=f, fill=ACCENT, anchor="lm")
    for i, (name, t) in enumerate(children):
        p = clamp((k - t) / 0.18)
        if p <= 0:
            continue
        y = 140 + i * rh + rh / 2
        dx = (1 - expo((k - t) / 0.3)) * 18
        branch = "└" if i == len(children) - 1 else "├"
        d.text((76, y), branch + "─", font=f, fill=FAINT, anchor="lm")
        d.text((180 + dx, y), name, font=f, fill=mix(CARD, INK, p), anchor="lm")
    enter(canvas, k, card, cx, cy, out)


def numbered(canvas, k, items, x=110, cy=ZONE_CY, gap=150, size=104):
    """a numbered list with no card: mono accent numbers, narrow caps rows that light up as they're said.
    items = [(text, t)]."""
    y0 = cy - gap * (len(items) - 1) / 2
    d = ImageDraw.Draw(canvas)
    fN, fT = mono(40, 600), head(size)
    for i, (txt, t) in enumerate(items):
        p = clamp((k - t) / 0.18)
        if k < t - 0.6:
            continue
        y = y0 + i * gap + size * 0.36
        d.text((x, y - size * 0.32), f"{i + 1:02d}", font=fN, fill=mix(FAINT, ACCENT, p), anchor="ls")
        d.text((x + 100, y), txt.upper(), font=fT, fill=mix(FAINT, INK, p), anchor="ls")


def bars(canvas, k, data, title, accent_word=None, cx=W / 2, cy=ZONE_CY, w=920, h=620, t0=0.3, stagger=0.1):
    """a bar chart with no card: narrow caps title with a serif italic word, bars growing in with their numbers,
    the tallest in the accent colour. data = [(label, value)]."""
    if k <= 0:
        return
    d = ImageDraw.Draw(canvas)
    x0, top = cx - w / 2, cy - h / 2
    _words_line(d, x0, top + 70, [(title, False)] + ([(accent_word, True)] if accent_word else []), 76)
    vmax = max(v for _, v in data)
    n = len(data)
    base, ceil = top + h, top + 190
    step_w = w / n
    bw = step_w * 0.7
    fV, fL = mono(30, 600), mono(26)
    for i, (lab, v) in enumerate(data):
        p = expo(clamp((k - t0 - i * stagger) / 0.5))
        x = x0 + i * step_w + (step_w - bw) / 2
        hh = (base - ceil) * v / vmax * p
        d.rectangle((x, base - max(hh, 4), x + bw, base), fill=ACCENT if v == vmax else (74, 72, 66))
        if p > 0.6:
            d.text((x + bw / 2, base - hh - 24), f"{v / 1000:.0f}K" if v >= 1000 else str(v), font=fV, fill=INK, anchor="mm")
        d.text((x + bw / 2, base + 40), lab, font=fL, fill=MUTED, anchor="mm")


def compare(canvas, k, thumbs, labels=("Bad", "Good", "Best"), views=("2K", "40K", "1.2M"), cx=W / 2, cy=ZONE_CY,
            tw=296, th=526, times=(0.2, 0.6, 1.0), best=None):
    """three thumbnails side by side with a mono label above and a view count below; the best one gets an accent
    outline and accent text."""
    best = len(thumbs) - 1 if best is None else best
    gap = 24
    x0 = cx - (len(thumbs) * tw + (len(thumbs) - 1) * gap) / 2
    for i, (im, lab, vw, t) in enumerate(zip(thumbs, labels, views, times)):
        if k < t:
            continue
        hi = i == best
        x = x0 + i * (tw + gap) + tw / 2
        fr = Image.new("RGBA", (tw + 12, th + 12), (0, 0, 0, 0))
        if hi:
            ImageDraw.Draw(fr).rounded_rectangle((0, 0, tw + 11, th + 11), 24, fill=ACCENT + (255,))
        fr.alpha_composite(rounded_rect(ImageOps.fit(im.convert("RGB"), (tw, th), Image.BICUBIC, centering=(0.5, 0.3)), 18), (6, 6))
        enter(canvas, k - t, fr, x, cy)
        a = clamp((k - t) / 0.15)
        col = ACCENT if hi else MUTED
        place(canvas, label(lab, 30, col, 600), x, cy - th / 2 - 46, 1, 0, a)
        place(canvas, label(vw + " views", 28, ACCENT if hi else INK, 600), x, cy + th / 2 + 46, 1, 0,
              clamp((k - t - 0.15) / 0.12))


def cta(canvas, k, word="EDIT", line=("I'll send you ", "the skill", " + the setup"), cx=W / 2, cy=ZONE_CY, t_line=0.5):
    """end card with no card: mono COMMENT, the keyword huge in the accent colour, one line with a serif word."""
    if k <= 0:
        return
    a = clamp(k / 0.1)
    place(canvas, label("Comment", 34), cx, cy - 200, 1, 0, a)
    f = head(330, 900, 62)
    im = Image.new("RGBA", (int(f.getlength(word)) + 40, 380), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 330), word, font=f, fill=ACCENT, anchor="ls")
    place(canvas, im, cx, cy + 10, 1.06 - 0.06 * expo(k / 0.2), 0, a)
    p = clamp((k - t_line) / 0.25)
    if p > 0:
        d = ImageDraw.Draw(canvas)
        fL, fS = font(HEAD, 44, [500, 100]), serif(54)
        a_, b_, c_ = line
        tot = fL.getlength(a_) + fS.getlength(b_) + fL.getlength(c_)
        x, y = cx - tot / 2, cy + 230
        al = int(255 * p)
        d.text((x, y), a_, font=fL, fill=MUTED + (al,), anchor="ls")
        x += fL.getlength(a_)
        d.text((x, y), b_, font=fS, fill=INK + (al,), anchor="ls")
        d.text((x + fS.getlength(b_), y), c_, font=fL, fill=MUTED + (al,), anchor="ls")


def chat(canvas, k, command, result, hint=None, t_type=0.2, cps=14, t_send=1.2, t_result=1.6):
    """the Claude app on a phone: a slash command types into the composer with its menu row above, sends, a
    'Running' line shows, then the finished clip comes back as the reply. result = this frame of the clip."""
    cv = Image.new("RGBA", (W, H), PAGE + (255,))
    d = ImageDraw.Draw(cv)
    fS, fC = mono(28), font(HEAD, 42, [500, 100])
    d.rounded_rectangle((W / 2 - 150, 70, W / 2 + 150, 140), 35, fill=SHADE)
    d.rounded_rectangle((W / 2, 78, W / 2 + 142, 132), 27, fill=EDGE)
    d.text((W / 2 - 75, 105), "CHAT", font=fS, fill=MUTED, anchor="mm")
    d.text((W / 2 + 71, 105), "CODE", font=fS, fill=INK, anchor="mm")
    n = int(clamp((k - t_type) * cps, 0, len(command)))
    comp_y = 1720
    d.rounded_rectangle((40, comp_y - 90, W - 40, comp_y + 90), 30, fill=SHADE, outline=EDGE, width=2)
    if k < t_send:
        d.text((80, comp_y - 26), command[:n], font=mono(42), fill=ACCENT, anchor="lm")
        if (k * 2.2) % 1 < 0.62:
            x = 82 + mono(42).getlength(command[:n])
            d.rectangle((x, comp_y - 52, x + 5, comp_y), fill=ACCENT)
        if hint and n > 1:
            d.rounded_rectangle((40, comp_y - 240, W - 40, comp_y - 110), 22, fill=CARD, outline=EDGE, width=2)
            d.text((80, comp_y - 196), command, font=mono(34, 600), fill=INK, anchor="lm")
            d.text((80, comp_y - 150), hint, font=fC, fill=MUTED, anchor="lm")
    else:
        d.text((80, comp_y - 26), "Reply to Claude…", font=fC, fill=FAINT, anchor="lm")
        bw = int(mono(30).getlength(command)) + 48
        d.rounded_rectangle((W - 60 - bw, 200, W - 60, 270), 18, fill=SHADE)
        d.text((W - 60 - bw / 2, 235), command, font=mono(30), fill=ACCENT, anchor="mm")
        if k < t_result:
            d.rectangle((60, 318, 80, 338), fill=ACCENT)
            d.text((100, 328), "RUNNING " + command.upper() + "…", font=mono(28), fill=MUTED, anchor="lm")
    _send(cv, W - 86, comp_y + 26, 0, True)
    if k >= t_result:
        rw, rh = 820, 1240
        clip = rounded_rect(ImageOps.fit(result.convert("RGB"), (rw, rh), Image.BICUBIC, centering=(0.5, 0.35)), 30)
        enter(cv, k - t_result, clip, W / 2, 310 + rh / 2)
    canvas.alpha_composite(cv)


def transcript(canvas, k, rows, title="transcript.json", cx=W / 2, cy=ZONE_CY, w=960, t_done=None, out=None):
    """Claude reading the transcript: mono timestamps and words that light up in turn, a status tag that flips
    to DONE in the accent colour at t_done. rows = [(stamp, word, t)]."""
    rh = 92
    h_ = 120 + len(rows) * rh + 30
    card = _card(w, h_).copy()
    card.alpha_composite(label(title, 24), (40, 36))
    done = t_done is not None and k >= t_done
    tag = label("Done" if done else "Reading", 22, on_accent() if done else MUTED, 600)
    tw = tag.width + 24
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((w - 40 - tw, 30, w - 40, 76), 10, fill=ACCENT if done else SHADE)
    card.alpha_composite(tag, (w - 40 - tw + 12, 53 - tag.height // 2))
    fS, fW = mono(34), head(64, 700)
    for i, (stamp, word, t) in enumerate(rows):
        y = 120 + i * rh + rh / 2
        p = clamp((k - t) / 0.12)
        d.text((52, y), stamp, font=fS, fill=mix(FAINT, MUTED, p), anchor="lm")
        d.text((260, y + 24), word.upper(), font=fW, fill=mix(FAINT, ACCENT if 0 <= k - t < 0.25 else INK, p),
               anchor="ls")
    enter(canvas, k, card, cx, cy, out)
