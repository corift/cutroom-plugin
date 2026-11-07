"""Layouts (the @rpn system).

  face  : talking head full frame. Framing alternates WIDE/TIGHT on every visible cut so a
          jump cut reads as a camera change (never zoom mid-shot, only a slow 1.5% drift).
  split : B-roll/UI in the top half (0-960), face in the bottom half, hard edge at the seam.
          Caption sits on the seam in a pill.
  full  : graphic or B-roll owns the whole frame; the voice continues underneath.

Timeline entries are plain tuples so a render script reads like an edit decision list:
    LAYOUT = [(t0, t1, "split", top_fn), (t0, t1, "full", fn), ...]   # everything else = face
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
from .core import W, H, cover, clamp, cubic

SEAM = H // 2

class Framing:
    """Per-cut framing for the face cam. `cuts` = output times of visible cuts."""
    def __init__(self, cuts, wide=1.0, tight=1.14, face_cy=0.36, start_tight=False):
        self.cuts = sorted(cuts); self.wide, self.tight, self.cy = wide, tight, face_cy
        self.start_tight = start_tight
    def shot(self, t):
        i = sum(1 for c in self.cuts if c <= t)
        s = self.cuts[i - 1] if i else 0.0
        return i, s
    def zoom(self, t):
        i, s = self.shot(t)
        base = self.tight if (i % 2 == 1) != self.start_tight else self.wide
        return base * (1 + 0.015 * clamp((t - s) / 6))      # barely-there drift

    def face(self, frame, t, punch=None, punch_z=1.2, punch_cy=0.38):
        """Full-frame face shot. punch = time of a Kallaway punch-in: from then on a hard 1.0 -> punch_z zoom that
        keeps the face (storyboard face beat `punch`)."""
        if punch is not None and t >= punch: return cover(frame, W, H, z=punch_z, cx=0.5, cy=punch_cy)
        z = self.zoom(t)
        if z <= 1.001: return frame.copy()
        return cover(frame, W, H, z=z, cx=0.5, cy=self.cy)

    def bottom(self, frame, t, face_cy=0.30):
        """Face for the bottom split panel (1080x960). Crops the source around the head."""
        i, _ = self.shot(t)
        z = 1.0 + (0.07 if i % 2 else 0.0)
        src_h = H / 2 / z                         # 960 px window of the 1080x1920 source
        cw = W / z
        y0 = clamp(H * face_cy - src_h * 0.42, 0, H - src_h)
        x0 = (W - cw) / 2
        return frame.resize((W, SEAM), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + src_h))

def split(canvas, top_img, face_img):
    canvas.paste(top_img.convert("RGB") if top_img.mode != "RGB" else top_img, (0, 0))
    canvas.paste(face_img, (0, SEAM))
    ImageDraw.Draw(canvas).line([(0, SEAM), (W, SEAM)], fill=(0, 0, 0, 255), width=2)

def resolve(t, timeline):
    """Returns (mode, fn, t0, t1) for time t; default face."""
    for t0, t1, mode, fn in timeline:
        if t0 <= t < t1: return mode, fn, t0, t1
    return "face", None, None, None

# ================================================================== @kallaway "stack"

def _drop_head(m, pad=24):
    """Pop-out = hands only. The head/hair crosses the seam as one wide run in the bottom rows of
    the strip; blank those columns so hair never spills over the graphic (user v5: 'my hair is
    spilling over … we can crop it'). Hands raised beside the head still pop out."""
    a = np.asarray(m).copy()
    if not a.any(): return m
    row = a[-3:].max(axis=0) > 128
    xs = np.flatnonzero(row)
    if xs.size:
        runs = np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)
        c = a.shape[1] / 2
        head = max(runs, key=lambda r: (r.size > a.shape[1] * 0.15) * r.size - abs((r[0] + r[-1]) / 2 - c) * 0.1)
        if head.size > a.shape[1] * 0.15:
            a[:, max(0, head[0] - pad):head[-1] + pad] = 0
    return Image.fromarray(a)

class Stack:
    """Graphic zone on top, face panel at the bottom.
    Default (v5, user-approved): face fills the WHOLE bottom half, full width, hard seam at
    y=960 like @rpn (radius=0 -> no card corners/glow, just a thin seam line). The v4
    kallaway small rounded card is card=(210,1360,660,530), radius=30 — user found it too small.
    Person pixels (Vision mask) that leave the card's top edge are drawn OVER the graphic
    zone -> raised hands / hair break out of the frame (the kallaway 'pop-out').

    card:     (x, y, w, h) on canvas
    src_top:  source y (0..1) on the card top edge. Keep it ABOVE the hair (0.13 for a close
              phone selfie) so the whole head is inside; only hands pop out. Cropping through
              the forehead makes the head look sliced (user feedback v4).
    pop:      max px above the card that pop-out may reach
    """
    def __init__(self, framing, card=(0, 960, 1080, 960), src_top=0.07, pop=240, radius=0, hands_only=True):
        self.f, self.card, self.src_top, self.pop, self.r = framing, card, src_top, pop, radius
        self.hands_only = hands_only
        cx, cy, cw, ch = card
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), radius, fill=255) if radius else m.paste(255, (0, 0, cw, ch))
        self.cmask = m
        g = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((40, 40, cw + 39, ch + 39), radius, outline=(255, 255, 255, 70), width=8)
        self.glow = g.filter(ImageFilter.GaussianBlur(18))

    def geometry(self, t):
        cx, cy, cw, ch = self.card
        i, _ = self.f.shot(t)
        z = 1.0 + (0.05 if i % 2 else 0.0)
        s = cw * z / W                              # source -> canvas scale
        x0 = (W - W / z) / 2                        # source crop left
        y0 = H * self.src_top + (0.015 * H if i % 2 else 0)
        return s, x0, y0

    def draw(self, canvas, frame, mask, t):
        cx, cy, cw, ch = self.card
        s, x0, y0 = self.geometry(t)
        # card body
        body = frame.resize((cw, ch), Image.BICUBIC, box=(x0, y0, x0 + cw / s, y0 + ch / s)).convert("RGBA")
        body.putalpha(self.cmask)
        if self.r:
            canvas.alpha_composite(self.glow, (cx - 40, cy - 40))
            canvas.alpha_composite(body, (cx, cy))
            ImageDraw.Draw(canvas).rounded_rectangle((cx, cy, cx + cw - 1, cy + ch - 1), self.r,
                                                     outline=(255, 255, 255, 150), width=3)
        else:                                       # full-width panel: hard seam
            canvas.alpha_composite(body, (cx, cy))
            ImageDraw.Draw(canvas).line([(cx, cy), (cx + cw, cy)], fill=(255, 255, 255, 110), width=2)
        # pop-out: the strip of source directly above the card, keyed by the person mask
        if mask is None: return
        ph = int(min(self.pop, y0 * s))
        if ph < 4: return
        sy0 = y0 - ph / s
        box = (x0, sy0, x0 + cw / s, y0)
        strip = frame.resize((cw, ph), Image.BICUBIC, box=box).convert("RGBA")
        mw, mh = mask.size; k = mw / W
        m = mask.resize((cw, ph), Image.BILINEAR, box=(box[0] * k, box[1] * k, box[2] * k, box[3] * k))
        m = m.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 0 if v < 60 else min(255, int((v - 60) * 1.4)))
        if self.hands_only: m = _drop_head(m)
        strip.putalpha(m)
        canvas.alpha_composite(strip, (cx, cy - ph))
