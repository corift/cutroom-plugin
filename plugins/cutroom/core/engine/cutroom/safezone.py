"""Platform safe zones (1080x1920). YouTube Shorts / Instagram Reels draw UI over the video, and tall
phones (taller than 9:16) scale the video up and trim the sides. Measured 2026-09-25 from the user's
Shorts screenshot (the "Made with Claude" header at y=64 sat under the status bar + Shorts header).

  SAFE box for anything that must be read: x 70..1010, y 250..1500
    top    0-250   status bar + app header (always)      250-340: Shorts feed chips (sometimes)
    bottom 1500-1920 channel / title / share / audio
    right  x>=900, y 1080-1780  like / comment / share rail
    sides  ~55 px trimmed on tall phones

`overlay(img)` tints the unsafe zones for review (storyboard board, preview stills). Never burn it into
the final render.
"""
from PIL import Image, ImageDraw
from .core import W, H, font, SFD

SAFE = (70, 250, 1010, 1500)
ZONES = [   # (box, label, strength)
    ((0, 0, W, 250), "STATUS BAR + APP HEADER", 1.0),
    ((0, 250, W, 340), "shorts chips (sometimes)", 0.45),
    ((0, 1500, W, H), "CHANNEL · TITLE · SHARE", 1.0),
    ((900, 1080, W, 1500), "BUTTONS", 1.0),
    ((0, 0, 55, H), "", 0.8),
    ((W - 55, 0, W, H), "", 0.8),
]

def overlay(img, col=(255, 40, 60)):
    """Return a copy with unsafe zones tinted + labelled and the safe box outlined."""
    base = img.convert("RGBA")
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    sx, sy = base.width / W, base.height / H
    f = font(SFD("Semibold"), max(12, int(30 * sx)))
    for (x0, y0, x1, y1), label, s in ZONES:
        d.rectangle((x0 * sx, y0 * sy, x1 * sx, y1 * sy), fill=col + (int(70 * s),))
        if label:
            d.text((x0 * sx + 70 * sx, y0 * sy + 12 * sy), label, font=f, fill=(255, 255, 255, int(220 * s)))
    x0, y0, x1, y1 = SAFE
    for i in range(int(x0 * sx), int(x1 * sx), int(24 * sx) or 1):          # dashed safe box
        d.line([(i, y0 * sy), (i + 12 * sx, y0 * sy)], fill=(255, 255, 255, 200), width=2)
        d.line([(i, y1 * sy), (i + 12 * sx, y1 * sy)], fill=(255, 255, 255, 200), width=2)
    base.alpha_composite(lay)
    return base

def check(boxes):
    """boxes: {name: (x0, y0, x1, y1)} of must-read elements -> list of names that leave SAFE."""
    sx0, sy0, sx1, sy1 = SAFE
    return [n for n, (x0, y0, x1, y1) in boxes.items() if x0 < sx0 or y0 < sy0 or x1 > sx1 or y1 > sy1]
