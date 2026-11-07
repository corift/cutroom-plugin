"""App screens: the graphic is a screen people already know (a chat app, a terminal, notes, a text thread, a
social post, analytics, an inbox, a browser), filled with what the video is about. Generic, not any one brand;
the accent is the brand kit's, as in basics.

    from cutroom import screens as Sc
    Sc.terminal(cv, k, [("cmd", "cut the pauses in raw.mp4", 0.2), ("out", "found 14 pauses", 1.0),
                        ("ok", "saved cut.mp4", 1.6)])

Every block is `block(canvas, k, ...)` with k in local seconds and draws in the top zone, above the face.
"""
from PIL import Image, ImageDraw
from . import basics as Bx
from .core import W, clamp, expo, inout, wrap, font
from .blocks import ss

PAPER = (244, 241, 234)
PAPER_INK = (28, 27, 25)
PAPER_MUTED = (128, 123, 113)
TERM = (14, 14, 13)


def ui(size, weight=500):
    return font(Bx.HEAD, size, [weight, 100])


def _window(w, h, title=None, fill=Bx.CARD, bar=Bx.SHADE, ink=Bx.MUTED, radius=28):
    card = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=fill + (255,),
                                               outline=Bx.EDGE + (255,), width=2 * s), w, h).copy()
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((2, 2, w - 3, 86), radius, fill=bar)
    d.rectangle((2, 50, w - 3, 86), fill=bar)
    for i in range(3):
        d.ellipse((34 + i * 30, 36, 50 + i * 30, 52), fill=Bx.FAINT)
    if title:
        d.text((w / 2, 44), title, font=ui(32), fill=ink, anchor="mm")
    return card, d


def _dots(d, x, y, k, col=Bx.MUTED):
    for i in range(3):
        a = 0.35 + 0.65 * max(0, 1 - abs(((k * 2.4 - i * 0.22) % 1.2) - 0.3) * 3)
        d.ellipse((x + i * 26 - 8, y - 8, x + i * 26 + 8, y + 8), fill=Bx.mix(Bx.CARD, col, a))


def _streamed(text, k, t, cps):
    words = text.split(" ")
    n = int(clamp((k - t) * cps / 5, 0, len(words)))
    return " ".join(words[:n])


def assistant(canvas, k, prompt, reply, cx=W / 2, cy=Bx.ZONE_CY, w=960, h=900, t_type=0.1, cps=40, t_send=None,
              t_reply=None, title="New chat"):
    """a chat assistant: the prompt types into the composer, sends as a bubble, typing dots, then the reply
    streams in word by word."""
    t_send = t_type + len(prompt) / cps + 0.15 if t_send is None else t_send
    t_reply = t_send + 0.6 if t_reply is None else t_reply
    card, d = _window(w, h, title)
    fB = ui(54)
    pad = 44
    if k < t_send:
        n = int(clamp((k - t_type) * cps, 0, len(prompt)))
        lines = wrap(prompt[:n], fB, w - 220) or [""]
        d.rounded_rectangle((pad, h - 160, w - pad, h - 40), 32, fill=Bx.SHADE, outline=Bx.EDGE, width=2)
        last = lines[-1] if len(lines) > 1 else lines[0]
        d.text((pad + 36, h - 100), last if n else "Ask anything", font=fB, fill=Bx.INK if n else Bx.FAINT,
               anchor="lm")
        if (k * 2.2) % 1 < 0.62:
            x = pad + 34 + (fB.getlength(last) if n else 0)
            d.rectangle((x, h - 128, x + 5, h - 72), fill=Bx.ACCENT)
    else:
        d.rounded_rectangle((pad, h - 160, w - pad, h - 40), 32, fill=Bx.SHADE, outline=Bx.EDGE, width=2)
        d.text((pad + 36, h - 100), "Reply…", font=fB, fill=Bx.FAINT, anchor="lm")
        lines = wrap(prompt, fB, w * 0.66)
        bw = max(fB.getlength(l) for l in lines) + 72
        bh = len(lines) * 68 + 44
        p = expo((k - t_send) / 0.25)
        y0 = 130 + (1 - p) * 30
        d.rounded_rectangle((w - pad - bw, y0, w - pad, y0 + bh), 30, fill=Bx.SHADE)
        for i, l in enumerate(lines):
            d.text((w - pad - bw + 36, y0 + 22 + i * 68), l, font=fB, fill=Bx.INK)
        ry = y0 + bh + 50
        d.ellipse((pad, ry + 6, pad + 48, ry + 54), fill=Bx.ACCENT)
        if k < t_reply:
            _dots(d, pad + 96, ry + 30, k)
        else:
            shown = _streamed(reply, k, t_reply, cps * 2.4)
            for i, l in enumerate(wrap(shown, fB, w - 2 * pad - 80)):
                d.text((pad + 80, ry + i * 68), l, font=fB, fill=Bx.INK)
    Bx.enter(canvas, k, card, cx, cy)


def terminal(canvas, k, lines, cx=W / 2, cy=Bx.ZONE_CY, w=960, h=860, cps=30, title="claude — my-video"):
    """a coding agent in a terminal. lines = [(kind, text, t)]: "cmd" types after a prompt sign, "out" prints
    dim, "edit" prints a + in the accent colour, "ok" prints a tick and bold accent text."""
    card, d = _window(w, h, title, fill=TERM, bar=(26, 26, 24))
    f, fb = Bx.mono(44), Bx.mono(44, 700)
    y, lh = 134, 68
    cursor = None
    for kind, text, t in lines:
        if k < t:
            break
        if kind == "cmd":
            n = int(clamp((k - t) * cps, 0, len(text)))
            d.text((44, y), ">", font=fb, fill=Bx.ACCENT)
            rows = wrap(text[:n], f, w - 150) or [""]
            for i, r in enumerate(rows):
                d.text((100, y + i * lh), r, font=f, fill=Bx.INK)
            cursor = (100 + f.getlength(rows[-1]), y + (len(rows) - 1) * lh) if n < len(text) else None
            y += len(rows) * lh + 14
        else:
            col = {"out": Bx.MUTED, "edit": Bx.INK, "ok": Bx.ACCENT}[kind]
            if kind == "ok":
                d.line([(46, y + 36), (60, y + 50), (82, y + 22)], fill=Bx.ACCENT, width=6, joint="curve")
            elif kind == "edit":
                d.text((44, y), "+", font=fb, fill=Bx.ACCENT)
            for i, r in enumerate(wrap(text, fb if kind == "ok" else f, w - 150)):
                d.text((100, y + i * lh), r, font=fb if kind == "ok" else f, fill=col)
                y += lh
            y += 6
    if cursor is None:
        cursor = (100, y)
        if (k * 2.2) % 1 < 0.62:
            d.text((44, y), ">", font=fb, fill=Bx.ACCENT)
    if (k * 2.2) % 1 < 0.62:
        d.rectangle((cursor[0] + 4, cursor[1] + 6, cursor[0] + 30, cursor[1] + 56), fill=Bx.ACCENT)
    Bx.enter(canvas, k, card, cx, cy)


def notes(canvas, k, title, lines, date="Today", cx=W / 2, cy=Bx.ZONE_CY, w=960, h=880, cps=38):
    """a notes page on paper: bold title, a dim date, then each line writing itself with a caret.
    lines = [(text, t)]; start a line with "- " for a bullet."""
    card = ss(lambda d, s: d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), 28 * s, fill=PAPER + (255,)), w, h).copy()
    d = ImageDraw.Draw(card)
    d.text((64, 76), date.upper(), font=Bx.mono(30, 600), fill=PAPER_MUTED, anchor="lm")
    d.text((60, 176), title, font=ui(86, 800), fill=PAPER_INK, anchor="ls")
    f = ui(56)
    y = 270
    caret = None
    for text, t in lines:
        if k < t:
            break
        bullet = text.startswith("- ")
        body = text[2:] if bullet else text
        n = int(clamp((k - t) * cps, 0, len(body)))
        x = 60
        if bullet:
            d.ellipse((64, y + 28, 80, y + 44), fill=PAPER_INK)
            x = 112
        rows = wrap(body[:n], f, w - x - 60) or [""]
        for i, r in enumerate(rows):
            d.text((x, y + i * 72), r, font=f, fill=PAPER_INK)
        if n < len(body):
            caret = (x + f.getlength(rows[-1]) + 4, y + (len(rows) - 1) * 72)
        y += len(rows) * 72 + 22
    if caret and (k * 2.2) % 1 < 0.62:
        d.rectangle((caret[0], caret[1] + 6, caret[0] + 5, caret[1] + 66), fill=PAPER_INK)
    Bx.enter(canvas, k, card, cx, cy)


def texts(canvas, k, contact, msgs, cx=W / 2, cy=Bx.ZONE_CY, w=960, h=900):
    """a text thread: their messages grey after typing dots, yours in the accent colour.
    msgs = [(mine, text, t)]."""
    card, d = _window(w, h)
    d.ellipse((w / 2 - 44, 110, w / 2 + 44, 198), fill=Bx.FAINT)
    d.text((w / 2, 154), contact[0].upper(), font=ui(46, 700), fill=Bx.INK, anchor="mm")
    d.text((w / 2, 232), contact, font=ui(34, 600), fill=Bx.MUTED, anchor="mm")
    f = ui(54)
    y = 290
    for i, (mine, text, t) in enumerate(msgs):
        typing = not mine and t - 0.5 <= k < t
        if k < t and not typing:
            break
        rows = wrap(text, f, w * 0.66)
        bw = (max(f.getlength(r) for r in rows) + 72) if not typing else 150
        bh = (len(rows) * 66 + 40) if not typing else 90
        x0 = w - 44 - bw if mine else 44
        fill = Bx.ACCENT if mine else Bx.SHADE
        p = expo((k - (t - 0.5 if typing else t)) / 0.2)
        dy = (1 - p) * 20
        d.rounded_rectangle((x0, y + dy, x0 + bw, y + bh + dy), 44, fill=fill)
        if typing:
            _dots(d, x0 + 48, y + 45 + dy, k, Bx.INK)
        else:
            for j, r in enumerate(rows):
                d.text((x0 + 36, y + 18 + j * 66 + dy), r, font=f, fill=Bx.on_accent() if mine else Bx.INK)
        y += bh + 22
    Bx.enter(canvas, k, card, cx, cy)


def post(canvas, k, name, handle, text, stats=(("Replies", 0, 214), ("Reposts", 0, 1240), ("Likes", 0, 12400)),
         cx=W / 2, cy=Bx.ZONE_CY, w=960, t0=0.5, dur=1.6):
    """a social post card: avatar, name and handle, the post, and its numbers counting up; the last number in
    the accent colour."""
    f = ui(62)
    rows = wrap(text, f, w - 120)
    h = 230 + len(rows) * 80 + 170
    card = Bx._card(w, h).copy()
    d = ImageDraw.Draw(card)
    d.ellipse((50, 50, 160, 160), fill=Bx.FAINT)
    d.text((105, 105), name[0].upper(), font=ui(54, 700), fill=Bx.INK, anchor="mm")
    d.text((186, 84), name, font=ui(48, 700), fill=Bx.INK, anchor="lm")
    d.text((186, 132), handle, font=ui(36), fill=Bx.MUTED, anchor="lm")
    for i, r in enumerate(rows):
        d.text((60, 210 + i * 80), r, font=f, fill=Bx.INK)
    by = h - 90
    d.line([(50, by - 50), (w - 50, by - 50)], fill=Bx.EDGE, width=2)
    p = inout(clamp((k - t0) / dur))
    step = (w - 100) / len(stats)
    for i, (lab, a, b) in enumerate(stats):
        v = int(a + (b - a) * p)
        txt = f"{v / 1000:.1f}K" if v >= 1000 else str(v)
        x = 60 + i * step
        last = i == len(stats) - 1
        d.text((x, by), txt, font=Bx.mono(44, 700), fill=Bx.ACCENT if last else Bx.INK, anchor="lm")
        d.text((x + Bx.mono(44, 700).getlength(txt) + 14, by), lab.upper(), font=Bx.mono(26), fill=Bx.MUTED,
               anchor="lm")
    Bx.enter(canvas, k, card, cx, cy)


def analytics(canvas, k, total, series, delta="+312%", label="Views · last 28 days", cx=W / 2, cy=Bx.ZONE_CY,
              w=960, h=860, t0=0.3, dur=1.6):
    """an analytics screen: the total counting up with an accent delta pill, and the line drawing across with a
    soft fill and a dot at its head. series = values over time."""
    card, d = _window(w, h, "Analytics")
    p = inout(clamp((k - t0) / dur))
    d.text((60, 150), label.upper(), font=Bx.mono(30), fill=Bx.MUTED, anchor="lm")
    num = f"{int(total * p):,}"
    fN = Bx.head(150, 800, 66)
    d.text((56, 330), num, font=fN, fill=Bx.INK, anchor="ls")
    if p > 0.6:
        tag = Bx.label(delta, 28, Bx.on_accent(), 700)
        x = 56 + fN.getlength(f"{total:,}") + 30
        d.rounded_rectangle((x, 250, x + tag.width + 24, 304), 12, fill=Bx.ACCENT)
        card.alpha_composite(tag, (int(x + 12), int(277 - tag.height / 2)))
    x0, x1, y0, y1 = 60, w - 60, 400, h - 70
    for i in range(4):
        yy = y0 + (y1 - y0) * i / 3
        d.line([(x0, yy), (x1, yy)], fill=Bx.EDGE, width=2)
    vmax = max(series)
    pts = [(x0 + (x1 - x0) * i / (len(series) - 1), y1 - (y1 - y0) * v / vmax) for i, v in enumerate(series)]
    n = 1 + (len(pts) - 1) * p
    i = int(n)
    shown = pts[:i] + ([(pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * (n - i),
                         pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * (n - i))] if i < len(pts) else [])
    if len(shown) > 1:
        area = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(area).polygon(shown + [(shown[-1][0], y1), (x0, y1)], fill=Bx.ACCENT + (40,))
        card.alpha_composite(area)
        d.line(shown, fill=Bx.ACCENT, width=7, joint="curve")
        hx, hy = shown[-1]
        d.ellipse((hx - 12, hy - 12, hx + 12, hy + 12), fill=Bx.ACCENT)
    Bx.enter(canvas, k, card, cx, cy)


def inbox(canvas, k, emails, cx=W / 2, cy=Bx.ZONE_CY, w=960, h=880, title="Inbox"):
    """an inbox: each email slides in at the top and pushes the rest down; unread ones get an accent dot and the
    newest an accent edge. emails = [(sender, subject, preview, t)], oldest first."""
    card, d = _window(w, h, title)
    rh = 236
    arrived = [e for e in emails if k >= e[3]]
    y = 100
    for i, (sender, subject, preview, t) in enumerate(reversed(arrived)):
        p = expo((k - t) / 0.3)
        yy = y + i * rh - (1 - p) * rh * (1 if i == 0 else 0)
        if i == 0:
            yy = y - (1 - p) * 40
        if yy > h - 40:
            break
        if i:
            d.line([(40, yy), (w - 40, yy)], fill=Bx.EDGE, width=2)
        if i == 0:
            d.rectangle((2, yy + 12, 8, yy + rh - 12), fill=Bx.ACCENT)
        d.ellipse((42, yy + 54, 62, yy + 74), fill=Bx.ACCENT)
        d.text((88, yy + 64), sender, font=ui(48, 700), fill=Bx.INK, anchor="lm")
        d.text((w - 50, yy + 64), "now" if i == 0 else f"{i * 4}m", font=Bx.mono(30), fill=Bx.MUTED, anchor="rm")
        d.text((88, yy + 128), subject, font=ui(44, 600), fill=Bx.INK, anchor="lm")
        pv = preview
        while ui(38).getlength(pv) > w - 140 and len(pv) > 4:
            pv = pv[:-2]
        d.text((88, yy + 186), pv + ("…" if pv != preview else ""), font=ui(38), fill=Bx.MUTED, anchor="lm")
    Bx.enter(canvas, k, card, cx, cy)


def browser(canvas, k, url, title, paras, mark=(1, 0), t_mark=1.2, cx=W / 2, cy=Bx.ZONE_CY, w=960, h=900,
            scroll=0, t_scroll=(0.3, 1.1)):
    """a web page in a browser window: the url in a pill, an article that scrolls a little, then one line gets an
    accent marker swept behind it. paras = [text]; mark = (paragraph, line)."""
    card, d = _window(w, h, fill=PAPER, bar=(225, 221, 212))
    uw = min(w - 260, ui(26).getlength(url) + 80)
    d.rounded_rectangle((w / 2 - uw / 2, 22, w / 2 + uw / 2, 66), 22, fill=(246, 244, 239))
    d.text((w / 2, 44), url, font=ui(26), fill=PAPER_MUTED, anchor="mm")
    page = Image.new("RGBA", (w, 2000), PAPER + (255,))
    pd = ImageDraw.Draw(page)
    fT, fP = Bx.head(96, 800, 72), ui(50)
    y = 50
    for r in wrap(title.upper(), fT, w - 120):
        pd.text((60, y), r, font=fT, fill=PAPER_INK)
        y += 100
    y += 36
    sweep = expo(clamp((k - t_mark) / 0.4))
    for pi, para in enumerate(paras):
        for li, r in enumerate(wrap(para, fP, w - 120)):
            if (pi, li) == mark and sweep > 0:
                pd.rectangle((52, y + 2, 52 + (fP.getlength(r) + 16) * sweep, y + 64), fill=Bx.ACCENT)
            pd.text((60, y), r, font=fP, fill=PAPER_INK if (pi, li) == mark or sweep == 0 else PAPER_MUTED)
            y += 70
        y += 30
    off = int(scroll * inout(clamp((k - t_scroll[0]) / (t_scroll[1] - t_scroll[0]))))
    view = page.crop((0, off, w, off + h - 90))
    mask = Image.new("L", view.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((2, -40, w - 3, view.height - 3), 28, fill=255)
    card.paste(view, (0, 88), mask)
    Bx.enter(canvas, k, card, cx, cy)
