"""Core primitives: canvas constants, fonts, easing, text rendering, compositing, video I/O.

Everything renders with Pillow onto a 1080x1920 RGBA canvas; frames are read from and
written to ffmpeg over raw pipes. No libass/drawtext needed.
"""
import io, os, subprocess, sys
import numpy as np
from . import brand as _brand
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30

# ------------------------------------------------------------------ fonts
LF = "/Library/Fonts/"
SFD = lambda w: LF + f"SF-Pro-Display-{w}.otf"      # Bold / Semibold / Medium / Regular
SFT = lambda w: LF + f"SF-Pro-Text-{w}.otf"
SERIF = "/System/Library/Fonts/NewYork.ttf"          # variable: [opsz 12-256, wght 400-1000, GRAD]
MONO = _brand.font("mono", LF + "DMMono-Regular.ttf")                     # caption face (closest match to @rpn)
MONO_MED = LF + "DMMono-Medium.ttf"
CODE = "/System/Library/Fonts/SFNSMono.ttf"
HELV = _brand.font("caption", "/System/Library/Fonts/HelveticaNeue.ttc")             # index 1 = Bold (caption face)
ASSETS = os.environ.get("CUTROOM_ASSETS") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")
TIKTOK = os.path.join(ASSETS, "fonts", "TikTokSans[opsz,slnt,wdth,wght].ttf")
DISPLAY = _brand.font("display", TIKTOK)
WEIGHTS = [("black", 900), ("heavy", 800), ("semibold", 600), ("bold", 700), ("medium", 500), ("light", 300)]


def display(size, weight=900):
    """The display face (TikTok Sans unless the brand kit sets "display") at a weight from 300 to 900."""
    return font(DISPLAY, size, [36, 100, weight, 0])


def _fallback(path, index):
    b = os.path.basename(path).lower()
    weight = next((v for k, v in WEIGHTS if k in b), 700 if "helvetica" in b and index == 1 else 400)
    name = {900: "Bold", 800: "Bold", 700: "Bold", 600: "SemiBold", 500: "Medium"}.get(weight, "Regular")
    linux = ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf" if "mono" in b
             else "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if "newyork" in b
             else f"/usr/share/fonts/opentype/inter/Inter-{name}.otf")
    if os.path.exists(linux):
        return linux, None
    return TIKTOK, [36, 100, weight, 0]

_fc, _fbytes = {}, {}
def font(path, size, var=None, index=0):
    """Cached font. `var` = variation axes list, e.g. serif(…) uses [opsz, wght, 0].
    `index` picks a face inside a .ttc collection (HelveticaNeue.ttc: 1 = Bold).
    A font that isn't installed falls back to Inter / DejaVu where they exist, else the bundled TikTok Sans."""
    k = (path, size, tuple(var) if var else None, index)
    if k not in _fc:
        src = path
        if not os.path.exists(src):
            alt = os.path.expanduser("~/Library/Fonts/" + os.path.basename(path))
            if os.path.exists(alt):
                src = alt
            else:
                src, var = _fallback(path, index)
                index = 0
        if src not in _fbytes:
            _fbytes[src] = open(src, "rb").read()
        f = ImageFont.truetype(io.BytesIO(_fbytes[src]), size, index=index)
        if var is not None:
            try: f.set_variation_by_axes(list(var))
            except Exception: pass
        _fc[k] = f
    return _fc[k]

def serif(size, weight=460, opsz=None):
    """New York at a sane optical size (large opsz renders hairline-thin)."""
    return font(SERIF, size, [opsz or min(40, max(18, size // 3)), weight, 0])

# ------------------------------------------------------------------ palette (dark / techy-pro)
WHITE = (255, 255, 255)
GREY = (150, 150, 155)
DIM = (92, 92, 98)
INK = (22, 22, 24)
PAPER = (245, 243, 238)
DARK = (11, 11, 12)
PILL = (28, 28, 30)

# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def expo(x): x = clamp(x); return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def cubic(x): x = clamp(x); return 1 - (1 - x) ** 3
def inout(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def env(t, t0, t1, fin=0.25, fout=0.18):
    """0..1 envelope: ease in over `fin` after t0, ease out over `fout` before t1."""
    if t < t0 or t > t1: return 0.0
    return min(cubic((t - t0) / fin), cubic((t1 - t) / fout))

# ------------------------------------------------------------------ text
def text_img(txt, f, fill=WHITE, tracking=0.0, shadow=0):
    """Tight RGBA text image. `tracking` in em. Result has `.pad` (transparent margin)."""
    asc, desc = f.getmetrics()
    widths = [f.getlength(c) for c in txt] if tracking else None
    tw = int(sum(widths) + tracking * f.size * (len(txt) - 1)) + 4 if tracking else int(f.getlength(txt)) + 4
    pad = 30 if shadow else 2
    im = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    def draw_on(d, col, off=(0, 0)):
        if tracking:
            x = pad
            for c, w_ in zip(txt, widths):
                d.text((x + off[0], pad + off[1]), c, font=f, fill=col); x += w_ + tracking * f.size
        else:
            d.text((pad + off[0], pad + off[1]), txt, font=f, fill=col)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw_on(ImageDraw.Draw(sh), (0, 0, 0, shadow), (0, 3))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
    draw_on(ImageDraw.Draw(im), fill)
    im.pad = pad
    return im

def wrap(txt, f, width):
    out, line = [], ""
    for wd in txt.split(" "):
        tst = (line + " " + wd).strip()
        if f.getlength(tst) <= width: line = tst
        else: out.append(line); line = wd
    if line: out.append(line)
    return out

def label(txt, col=(224, 122, 88), size=28):
    """Small tracked uppercase kicker label."""
    return text_img(txt.upper(), font(SFT("Semibold"), size), fill=col, tracking=0.16)

# ------------------------------------------------------------------ compositing
def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a))); return im

def paste(canvas, im, x, y, a=1.0):
    if a <= 0.003: return
    canvas.alpha_composite(with_alpha(im, a), (int(x), int(y)))

def paste_center(canvas, im, cx, cy, a=1.0):
    paste(canvas, im, cx - im.width / 2, cy - im.height / 2, a)

def reveal(canvas, im, x, y, p, a=1.0):
    """Mask reveal: content slides up from beneath a clip line at its own baseline."""
    if p <= 0.001: return
    off = int((1 - expo(p)) * im.height * 0.9)
    paste(canvas, im.crop((0, 0, im.width, im.height - off)), x, y + off, a)

def hline(canvas, x, y, length, p, col=(224, 122, 88), width=4, a=1.0):
    if p <= 0: return
    ImageDraw.Draw(canvas).rectangle((x, y, x + length * expo(p), y + width - 1), fill=col + (int(255 * a),))

def cover(img, w, h, z=1.0, cx=0.5, cy=0.5):
    """Scale-to-fill crop with extra zoom `z` and focus point (cx, cy) in 0..1."""
    iw, ih = img.size
    s = max(w / iw, h / ih) * z
    cw, ch = w / s, h / s
    x0 = clamp((iw - cw) * cx, 0, iw - cw); y0 = clamp((ih - ch) * cy, 0, ih - ch)
    return img.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width - 1, img.height - 1), r, fill=255)
    out = img.convert("RGBA"); out.putalpha(m); return out

def dilate(mask, r):
    """L mask grown by r px, the same result as ImageFilter.MaxFilter(2 * r + 1) at a fraction of the time."""
    a = np.asarray(mask.convert("L"))
    for axis in (0, 1):
        p = np.pad(a, [(r, r) if i == axis else (0, 0) for i in (0, 1)])
        n = a.shape[axis]
        grown = np.zeros_like(a)
        for k in range(2 * r + 1):
            np.maximum(grown, p[k:k + n] if axis == 0 else p[:, k:k + n], out=grown)
        a = grown
    return Image.fromarray(a)

def vgrad(w, h, a0, a1, col=(0, 0, 0), power=1.4):
    """Vertical alpha gradient strip from alpha a0 (top) to a1 (bottom)."""
    g = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for y in range(h):
        k = (y / max(1, h - 1)) ** power
        d.line([(0, y), (w, y)], fill=col + (int(a0 + (a1 - a0) * k),))
    return g

def logo(path, size):
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)

# ------------------------------------------------------------------ video I/O
class Reader:
    """Sequential ffmpeg frame reader. Holds the last frame when the source ends."""
    def __init__(self, path, w=W, h=H, start=0.0, fill=True, precrop="", fps=FPS):
        vf = precrop + (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}" if fill else f"scale={w}:{h}")
        self.w, self.h, self.last = w, h, None
        self.p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-threads", "2", "-ss", str(max(0.0, start - 0.5 / fps)), "-copyts", "-i", path,
                                   "-vf", f"fps={fps}:start_time={start},{vf}",
                                   "-threads", "2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    def next(self):
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) == self.w * self.h * 3:
            self.last = Image.frombuffer("RGB", (self.w, self.h), buf, "raw", "RGB", 0, 1)
        return self.last
    def close(self): self.p.kill(); self.p.wait()

def probe_duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())

BITRATE = "10M"
_hardware = None

def hardware_encoder():
    """True when ffmpeg can encode H.264 on this Mac's media engine. CUTROOM_ENCODER=x264 turns it off."""
    global _hardware
    if _hardware is None:
        _hardware = False
        if sys.platform == "darwin" and os.environ.get("CUTROOM_ENCODER", "") != "x264":
            _hardware = subprocess.run(["ffmpeg", "-v", "quiet", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}",
                                        "-frames:v", "2", "-c:v", "h264_videotoolbox", "-allow_sw", "0", "-f", "null", "-"]).returncode == 0
    return _hardware

def probe_size(path):
    w, h = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", path]).decode().split(",")[:2]
    return int(w), int(h)

def bitrate(size=(W, H), scale=1.0):
    """BITRATE scaled to the frame's pixel count, so a 4K landscape video gets the same quality as a 1080x1920 short."""
    return max(2, round(int(BITRATE[:-1]) * scale * size[0] * size[1] / (W * H)))

def h264(threads=None, size=(W, H)):
    """ffmpeg arguments for an upload-ready H.264 stream: the hardware encoder on a Mac, x264 anywhere else."""
    rate = bitrate(size)
    if hardware_encoder():
        return ["-c:v", "h264_videotoolbox", "-allow_sw", "0", "-profile:v", "high", "-g", str(FPS * 2), "-b:v", f"{rate}M", "-pix_fmt", "yuv420p"]
    return (["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-b:v", f"{rate}M", "-maxrate", f"{rate}M", "-bufsize", f"{rate * 2}M",
             "-pix_fmt", "yuv420p"] + (["-threads", str(threads)] if threads else []))

def mezzanine(size=(W, H)):
    """ffmpeg arguments for a working file a later step renders from (a cut base, a retimed clip): near-lossless,
    a keyframe every second so chunk readers seek cheaply, and fast to write."""
    if hardware_encoder():
        return ["-c:v", "h264_videotoolbox", "-allow_sw", "0", "-profile:v", "high", "-g", str(FPS), "-b:v", f"{bitrate(size, 2.5)}M", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", str(FPS), "-pix_fmt", "yuv420p"]

class Encoder:
    def __init__(self, out, audio=None, crf=16, fps=FPS, size=(W, H)):
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
               "-r", str(fps), "-i", "-"]
        if audio: cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
        cmd += h264(size=size) + ["-movflags", "+faststart", out]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    def write(self, img): self.p.stdin.write(img.convert("RGB").tobytes())
    def close(self): self.p.stdin.close(); self.p.wait()

def social_encode(src, out, mbps=12):
    """Upload-ready copy for Instagram/TikTok: 1080x1920 H.264 High, ~mbps cap, AAC 192k, faststart.
    The platforms re-encode to ~3-6 Mbps, so anything above ~12 Mbps is wasted file size."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
                    "-crf", "18", "-maxrate", f"{mbps}M", "-bufsize", f"{mbps*2}M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out], check=True)

def preview_encode(src, out, mbps=3.5):
    """Small phone-friendly copy (<30 MB for ~60 s)."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-b:v", f"{mbps}M",
                    "-maxrate", f"{mbps*1.3}M", "-bufsize", f"{mbps*2}M", "-vf", "scale=720:-2",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], check=True)
