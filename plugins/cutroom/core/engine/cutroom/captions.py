"""Captions. Two house styles, both hard-swap (no bounce, no per-word pop):

  "kallaway" (default since v4): Helvetica Neue Bold 68, tracking -0.045em, soft drop shadow,
             pure white, sentence case as spoken (matched against a kallaway frame),
             1-2 words per chunk; KEY PHRASES swap to white italic serif (New York Italic).
  "rpn":     small uppercase DM Mono, 1-3 words; pill on seams.

Three word-by-word styles, where the spoken word is marked as it is said:
  "pop":      heavy uppercase display face with a black outline, 1-2 words; the spoken word turns marker yellow.
  "box":      bold sentence case, 1-3 words; the spoken word sits on an accent-coloured rounded box.
  "subtitle": clean sentence-case line, up to ~7 words, soft shadow, low in the frame. No word marking.

Placement: ONE fixed spot (y=960, dead center — on the stack seam) in every layout — moving captions
between layouts felt jarring (user feedback v4), and v5 asked for it centered. Layouts leave that band free.
"""
import json, re
from PIL import Image, ImageDraw, ImageFilter
from . import brand
from .core import W, font, text_img, paste, display, MONO, WHITE, PILL, HELV

SERIF_IT = brand.font("serif_italic", "/System/Library/Fonts/NewYorkItalic.ttf")
STYLES = {
    "kallaway": dict(max_words=2, max_chars=14,
                     y={"face": 960, "stack": 960, "split": 960, "full": 960}),
    "rpn": dict(max_words=3, max_chars=16,
                y={"face": 1400, "stack": 1040, "split": 960, "full": 1650}),
    "pop": dict(max_words=2, max_chars=14,
                y={"face": 1240, "stack": 960, "split": 960, "full": 1400}),
    "box": dict(max_words=3, max_chars=20,
                y={"face": 1240, "stack": 960, "split": 960, "full": 1400}),
    "subtitle": dict(max_words=7, max_chars=34,
                     y={"face": 1480, "stack": 1040, "split": 1480, "full": 1560}),
}
WORD_STYLES = ("pop", "box")
MARKER = brand.color("marker", (255, 214, 92))
ACCENT = brand.color("accent", (214, 34, 34))
BLACK = (0, 0, 0)
GAP_BREAK = 0.30     # a pause this long always starts a new chunk
HOLD = 0.35          # linger after the last word when followed by silence

def load_words(transcript_json, fixes=None, drop=()):
    """Words from a Groq/Whisper verbose_json. `fixes` maps wrong->right (punctuation kept)."""
    fixes = fixes or {}
    out = []
    for w in json.load(open(transcript_json))["words"]:
        txt = w["word"].strip()
        if not txt or txt in drop: continue
        core = re.sub(r"[,.?!]+$", "", txt)
        if core in fixes: txt = fixes[core] + txt[len(core):]
        out.append({"w": txt, "s": float(w["start"]), "e": float(w["end"])})
    for i, w in enumerate(out):                       # monotonic, non-overlapping
        if i: w["s"] = max(w["s"], out[i - 1]["s"] + 0.04)
    for i, w in enumerate(out):
        nxt = out[i + 1]["s"] if i + 1 < len(out) else w["e"] + 0.5
        w["e"] = max(min(w["e"], nxt), w["s"] + 0.06)
    return out

def _n(s): return re.sub(r"[^a-z0-9.\-]", "", s.lower()).strip(".")

def join_phrases(words, phrases):
    """Merge consecutive words that spell an emphasis phrase into one token flagged `em`."""
    out, i = [], 0
    targets = [[_n(p) for p in ph.split()] for ph in phrases]
    while i < len(words):
        hit = None
        for tg in targets:
            if [_n(w["w"]) for w in words[i:i + len(tg)]] == tg: hit = tg; break
        if hit:
            grp = words[i:i + len(hit)]
            out.append({"w": " ".join(g["w"] for g in grp), "s": grp[0]["s"], "e": grp[-1]["e"], "em": True})
            i += len(hit)
        else:
            out.append(dict(words[i])); i += 1
    return out

def chunk(words, style="kallaway"):
    """Phrase chunks: break on punctuation, pauses, word/char limits. Emphasis tokens stand alone."""
    st = STYLES[style]
    groups, cur = [], []
    for i, w in enumerate(words):
        if w.get("em") and cur: groups.append(cur); cur = []
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(x["w"] for x in cur)
        brk = (nxt is None or w.get("em") or nxt.get("em") or w["w"][-1] in ",.?!"
               or len(cur) >= st["max_words"] or nxt["s"] - w["e"] > GAP_BREAK
               or len(txt + " " + nxt["w"]) > st["max_chars"])
        if brk: groups.append(cur); cur = []
    spans = []
    for gi, g in enumerate(groups):
        nxt = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else g[-1]["e"] + HOLD
        spans.append({"s": g[0]["s"], "e": min(g[-1]["e"] + HOLD, nxt),
                      "text": " ".join(x["w"] for x in g), "em": any(x.get("em") for x in g), "words": g})
    return spans

_cache = {}
def _pill(im, px, py, r, alpha=225):
    """Wrap a text_img in a tight near-black rounded pill (for captions that sit on a seam)."""
    iw, ih = im.width - 2 * im.pad, im.height - 2 * im.pad
    bg = Image.new("RGBA", (iw + 2 * px, ih + 2 * py), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle((0, 0, bg.width - 1, bg.height - 1), r, fill=PILL + (alpha,))
    bg.alpha_composite(im, (px - im.pad, py - im.pad + 2))
    return bg

def caption_img(text, style, pill=False, em=False):
    k = (text, style, pill, em)
    if k in _cache: return _cache[k]
    txt = text.replace("’", "'")
    if style == "rpn":
        im = text_img(txt.upper(), font(MONO, 44), fill=WHITE, tracking=0.04, shadow=0 if pill else 200)
        if pill: im = _pill(im, 22, 12, 14)
    else:
        txt = txt.rstrip(",")
        sh = 0 if pill else 200
        if em: im = text_img(txt, font(SERIF_IT, 74, [28, 520, 0]), fill=WHITE, shadow=sh)
        else:  im = text_img(txt, font(HELV, 68, index=1 if HELV.endswith("HelveticaNeue.ttc") else 0), fill=WHITE, tracking=-0.045, shadow=sh)
        if pill: im = _pill(im, 26, 10, 18)
    _cache[k] = im
    return im

def _outlined(txt, f, fill, stroke):
    asc, desc = f.getmetrics()
    pad = stroke + 24
    im = Image.new("RGBA", (int(f.getlength(txt)) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad + 6), txt, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text((pad, pad), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=BLACK)
    im.pad = pad
    return im

def _boxed(txt, f, on):
    im = text_img(txt, f, fill=WHITE, tracking=-0.02, shadow=0 if on else 170)
    if not on: return im
    px, py = 18, 6
    iw, ih = im.width - 2 * im.pad, im.height - 2 * im.pad
    bg = Image.new("RGBA", (iw + 2 * px, ih + 2 * py), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle((0, 0, bg.width - 1, bg.height - 1), 16, fill=ACCENT + (255,))
    bg.alpha_composite(im, (px - im.pad, py - im.pad + 3))
    out = Image.new("RGBA", (bg.width + 2 * im.pad, bg.height + 2 * im.pad), (0, 0, 0, 0))
    out.alpha_composite(bg, (im.pad, im.pad))
    out.pad = im.pad + px
    return out

def words_img(words, active, style):
    """One line of words side by side, the word at index `active` marked in the style's way."""
    k = (tuple(w["w"] for w in words), active, style)
    if k in _cache: return _cache[k]
    f = display(84 if style == "pop" else 70, 900 if style == "pop" else 800)
    parts = []
    for i, w in enumerate(words):
        txt = w["w"].replace("’", "'").rstrip(",.")
        if style == "pop": parts.append(_outlined(txt.upper(), f, MARKER if i == active else WHITE, 7))
        else: parts.append(_boxed(txt, f, i == active))
    gap = int(f.size * 0.26)
    inner = [p.width - 2 * p.pad for p in parts]
    pad = max(p.pad for p in parts)
    h = max(p.height - 2 * p.pad for p in parts) + 2 * pad
    im = Image.new("RGBA", (sum(inner) + gap * (len(parts) - 1) + 2 * pad, h), (0, 0, 0, 0))
    x = pad
    for p, iw in zip(parts, inner):
        im.alpha_composite(p, (x - p.pad, (h - p.height) // 2))
        x += iw + gap
    im.pad = pad
    _cache[k] = im
    return im

def subtitle_img(text):
    k = (text, "subtitle")
    if k in _cache: return _cache[k]
    im = text_img(text.replace("’", "'"), display(54, 600), fill=WHITE, tracking=-0.01, shadow=230)
    _cache[k] = im
    return im

def draw(canvas, t, spans, mode, style="kallaway", hidden=False):
    """Hard-swap caption for time t. mode: face | stack | split | full."""
    if hidden: return
    cur = next((c for c in spans if c["s"] <= t < c["e"]), None)
    if not cur: return
    # pill on seams only (stack/split): text straddles graphic + face and loses contrast (user v5).
    # Face shots keep the plain shadowed caption.
    y = STYLES[style]["y"][mode]
    if style in WORD_STYLES:
        words = cur["words"]
        active = max((i for i, w in enumerate(words) if w["s"] <= t), default=0)
        im = words_img(words, active, style)
        paste(canvas, im, W / 2 - im.width / 2, y - im.height / 2)
        return
    if style == "subtitle":
        im = subtitle_img(cur["text"])
        paste(canvas, im, W / 2 - im.width / 2, y - im.height / 2)
        return
    pill = mode in ("stack", "split") if style == "kallaway" else mode != "face"
    im = caption_img(cur["text"], style, pill=pill, em=cur["em"])
    paste(canvas, im, W / 2 - im.width / 2, y - im.height / 2)
