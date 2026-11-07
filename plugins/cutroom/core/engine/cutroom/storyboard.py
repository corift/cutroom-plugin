"""Storyboard: ONE timeline file that drives picture AND sound.

A video editor locks picture first and lays sound last, on the picture's cue points. We do the same:
`storyboard.json` lists every beat (what's on screen) and its cues (when things happen). The
render script reads layouts + cue times from it; the mix script builds SFX from the same cues. A
click can't drift away from the press it belongs to, because both read one number.

File shape (see templates/storyboard_template.json):
{
  "video": "...", "transcript": "base_vN_transcript.json",
  "beats": [
    {"id": "hook", "t0": 0.86, "t1": 3.30, "layout": "stack",          # face | stack | full | split
     "says": "(auto from transcript)", "header": "Just dropped",
     "visual": "Hero card: Claude Opus 5.5 over launch image", "asset": "assets/hero_bg.jpg",
     "notes": "rise-in 0.5 s",
     "cues": [{"name": "hook_in", "t": "start", "event": "card rises", "sfx": "impact", "gain": 0.42}]}
  ]
}

Cue "t" forms: 12.3 (absolute) | "start" / "end" (beat bounds) | "+0.45" (after beat start)
| "word:copywriting" or "word:copywriting#2" (nth time that word is said) — add "offset": 0.1.
"sfx" is a key in assets/sfx/sfx.json (onset + default gain live there), or omit it for a
visual-only cue that the render reads with sb.cue(name).
"""
import json, os, re, subprocess
from PIL import Image, ImageDraw
from .core import W, H, font, text_img, paste, WHITE, HELV, SFD, MONO
from . import sound as S

LAYOUTS = ("face", "stack", "full", "split", "inset")   # inset = Kallaway: graphic top ~60% on canvas(), face_inset flush bottom

def _n(s): return re.sub(r"[^a-z0-9.\-]", "", s.lower()).strip(".")

class Storyboard:
    def __init__(self, data, base_dir="."):
        self.d, self.dir = data, base_dir
        self.beats = sorted(data["beats"], key=lambda b: b["t0"])
        self.words = []
        tr = data.get("transcript")
        if tr and os.path.exists(os.path.join(base_dir, tr)):
            self.words = [{"w": w["word"].strip(), "s": float(w["start"]), "e": float(w["end"])}
                          for w in json.load(open(os.path.join(base_dir, tr)))["words"]]
        reg = os.path.join(S.SFX_DIR, "sfx.json")
        self.sfx = {k: v for k, v in json.load(open(reg)).items() if not k.startswith("_")} if os.path.exists(reg) else {}
        for b in self.beats:
            assert b.get("layout", "face") in LAYOUTS, f"beat {b.get('id')}: bad layout {b.get('layout')}"
            for c in b.get("cues", []): c["_t"] = self._resolve(c, b)

    @classmethod
    def load(cls, path):
        return cls(json.load(open(path)), os.path.dirname(os.path.abspath(path)))

    # ------------------------------------------------------------ time resolution
    def word_time(self, spec, after=0.0):
        m = re.match(r"(.+?)(?:#(\d+))?$", spec)
        target, nth = [_n(x) for x in m.group(1).split()], int(m.group(2) or 1)
        hits = [i for i in range(len(self.words))
                if [_n(w["w"]) for w in self.words[i:i + len(target)]] == target and self.words[i]["s"] >= after]
        if len(hits) < nth: raise KeyError(f"word '{spec}' not found in transcript")
        return self.words[hits[nth - 1]]["s"]

    def _resolve(self, c, b):
        t, off = c.get("t", "start"), float(c.get("offset", 0))
        if isinstance(t, (int, float)): v = float(t)
        elif t == "start": v = b["t0"]
        elif t == "end": v = b["t1"]
        elif t.startswith("+"): v = b["t0"] + float(t[1:])
        elif t.startswith("word:"): v = self.word_time(t[5:])
        else: raise ValueError(f"cue time {t!r}")
        return round(v + off, 3)

    # ------------------------------------------------------------ picture
    def cue(self, name):
        for b in self.beats:
            for c in b.get("cues", []):
                if c.get("name") == name: return c["_t"]
        raise KeyError(name)

    def beat(self, bid):
        return next(b for b in self.beats if b["id"] == bid)

    def timeline(self, fns):
        """[(t0, t1, layout, fn)] for non-face beats; fns maps beat id -> draw function."""
        return [(b["t0"], b["t1"], b["layout"], fns[b["id"]]) for b in self.beats
                if b.get("layout", "face") != "face" and b["id"] in fns]

    def overlays(self, fns):
        """[(t0, t1, fn)] for face beats that have an overlay function."""
        return [(b["t0"], b["t1"], fns[b["id"]]) for b in self.beats
                if b.get("layout", "face") == "face" and b["id"] in fns]

    def cuts(self):
        return [b["t0"] for b in self.beats] + [b["t1"] for b in self.beats]

    # ------------------------------------------------------------ sound (laid last, on the cues)
    CLICKS_PER_MIN = 9
    CLICKS_MIN = 6

    def sfx_events(self):
        """Events for sound.mix. A cue may set "until": "<cue name>" (e.g. a `typing` bed until its Enter press):
        its length becomes that cue's time - 0.12 s, so the press lands on its own."""
        ev, clicks = [], []
        for b in self.beats:
            for c in b.get("cues", []):
                k = c.get("sfx")
                if not k: continue
                s = self.sfx[k]
                if s.get("status") == "avoid": raise ValueError(f"cue {c.get('name')}: sfx '{k}' is on the avoid list")
                dur = c.get("dur", s.get("dur"))
                if c.get("until"): dur = round(self.cue(c["until"]) - c["_t"] - 0.12, 2)
                clip = S.load(s["file"], c.get("gain", s["gain"]), start=s.get("start", 0.0), dur=dur)
                ev.append(S.at(c["_t"], clip, s["onset"]))
                if k == "click": clicks.append(c.get("name") or c.get("event", ""))
        dur_min = max(b["t1"] for b in self.beats) / 60 if self.beats else 1
        if len(clicks) > max(self.CLICKS_MIN, self.CLICKS_PER_MIN * dur_min):
            print(f"WARNING: {len(clicks)} clicks in {dur_min * 60:.0f}s (budget ~{self.CLICKS_PER_MIN}/min). Click only on "
                  f"real on-screen presses (Enter, buttons); drop the sfx on other cues: {clicks}")
        return ev

    def sfx_cues(self):
        return [(c["_t"], c["sfx"], c.get("event", c.get("name", "")), b["id"])
                for b in self.beats for c in b.get("cues", []) if c.get("sfx")]

    # ------------------------------------------------------------ review artifacts
    def says(self, b):
        if b.get("says"): return b["says"]
        return " ".join(w["w"] for w in self.words if b["t0"] - 0.05 <= w["s"] < b["t1"])

    def markdown(self, out):
        L = [f"# Storyboard: {self.d.get('video', '')}", "",
             "Loose plan for approval before the build. Picture first, sound last on the cues.", "",
             "| # | Time | Layout | On screen | Says | Cues → SFX |", "|---|---|---|---|---|---|"]
        for i, b in enumerate(self.beats, 1):
            vis = " · ".join(x for x in [f"**{b['header']}**" if b.get("header") else "", b.get("visual", ""),
                                         f"_{b['notes']}_" if b.get("notes") else ""] if x)
            cues = "<br>".join(f"{c['_t']:.2f} {c.get('event', c.get('name', ''))}" + (f" → `{c['sfx']}`" if c.get("sfx") else "")
                               for c in b.get("cues", []))
            L.append(f"| {i} | {b['t0']:.2f}–{b['t1']:.2f} | {b.get('layout', 'face')} | {vis} | {self.says(b)} | {cues} |")
        open(out, "w").write("\n".join(L) + "\n")
        return out

    def rough_board(self, base_video, out, cols=4, framing=None, safe=True, mask_video=None):
        """Low-fi board (safe=True tints the Shorts/Reels UI zones, see safezone.py): one rough frame per beat (real face from the cut, labelled placeholder
        for the graphic, header, caption spot), plus time/cues under each. Takes ~1 min."""
        from . import layout as Lay, components as C
        fr = Lay.Framing(self.cuts(), wide=1.28, tight=1.38, face_cy=1.0) if framing is None else framing
        stack = Lay.Stack(fr)
        tw, th = 360, 640
        cells = []
        for i, b in enumerate(self.beats, 1):
            t = (b["t0"] + min(b["t1"], b["t0"] + 3)) / 2
            src = _grab(base_video, t)
            lay = b.get("layout", "face")
            if lay == "face":
                cv = fr.face(src, t).convert("RGBA")
            elif lay == "inset":
                from . import blocks as B
                cv = B.canvas(b.get("theme", "dark"), int(t * 30))
                _placeholder(cv, (90, 300, W - 90, 1090), b.get("visual", ""))
                mk = _grab(mask_video, t).convert("L") if mask_video else None   # with the mask the head pops out like the render
                B.face_inset(cv, src, mk, box=tuple(b.get("box", (60, 1300, 1020, 1920))), src_y=b.get("src_y", 690), theme=b.get("theme", "dark"))
            else:
                cv = C.dotted_bg(W, H).copy() if lay != "full" else Image.new("RGBA", (W, H), (8, 8, 9, 255))
                y1 = 900 if lay in ("stack", "split") else 1480
                _placeholder(cv, (90, 360 if lay != "full" else 300, W - 90, y1), b.get("visual", ""))
                if lay in ("stack", "split"): stack.draw(cv, src, None, t)
            if b.get("header"):
                C.red_header(cv, 99, b["header"], W / 2, 260, size=54)   # safe zone: never above y 250
            cap = self.says(b).split()
            if cap:
                im = text_img(" ".join(cap[:2]), font(HELV, 68, index=1), fill=WHITE, shadow=200)
                paste(cv, im, W / 2 - im.width / 2, (self.d.get("caption_y_inset", 1040) if lay == "inset" else 960) - im.height / 2)   # inset: proposed spot just above the popped-out head
            if safe:
                from . import safezone
                cv = safezone.overlay(cv)
            cell = Image.new("RGB", (tw, th + 150), (18, 18, 20))
            cell.paste(cv.convert("RGB").resize((tw, th)), (0, 0))
            d = ImageDraw.Draw(cell)
            fs, fm = font(SFD("Semibold"), 20), font(MONO, 15)
            d.text((10, th + 8), f"{i}. {b['id']}  {b['t0']:.1f}–{b['t1']:.1f}s  [{lay}]", font=fs, fill=WHITE)
            y = th + 36
            for c in b.get("cues", [])[:5]:
                d.text((10, y), f"{c['_t']:.2f} {c.get('event', c.get('name', ''))[:26]}" + (f" -> {c['sfx']}" if c.get('sfx') else ""),
                       font=fm, fill=(224, 122, 88) if c.get("sfx") else (170, 170, 176)); y += 21
            cells.append(cell)
        rows = (len(cells) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 158) + 8), (60, 60, 64))
        for i, c in enumerate(cells):
            sheet.paste(c, (8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 158)))
        sheet.save(out, quality=85)
        return out

    def cue_sheet(self, video, out):
        """QA after render: for every SFX cue, frames at -0.2 s / on the cue / +0.25 s. The visual
        event (press, tick, wipe, cut) must be visible in the middle frame — otherwise move the cue."""
        rows = []
        for t, k, ev, bid in self.sfx_cues():
            fs = [_grab(video, max(0, t + dt)).resize((240, 427)) for dt in (-0.2, 0.0, 0.25)]
            r = Image.new("RGB", (3 * 244 + 260, 431), (18, 18, 20))
            for j, f in enumerate(fs): r.paste(f, (4 + j * 244, 2))
            d = ImageDraw.Draw(r)
            d.text((3 * 244 + 12, 20), f"{t:.2f}s", font=font(SFD("Semibold"), 34), fill=WHITE)
            d.text((3 * 244 + 12, 70), k, font=font(MONO, 26), fill=(224, 122, 88))
            d.text((3 * 244 + 12, 110), f"{ev}\n[{bid}]", font=font(SFD("Semibold"), 20), fill=(190, 190, 196))
            d.text((3 * 244 + 12, 380), "-0.2  |  ON  |  +0.25", font=font(MONO, 16), fill=(120, 120, 126))
            rows.append(r)
        sheet = Image.new("RGB", (rows[0].width * 2 + 12, ((len(rows) + 1) // 2) * 435 + 4), (60, 60, 64))
        for i, r in enumerate(rows):
            sheet.paste(r, (4 + (i % 2) * (r.width + 4), 4 + (i // 2) * 435))
        sheet.save(out, quality=82)
        return out

_dur = {}
def _grab(video, t):
    if video not in _dur:
        _dur[video] = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                     "-of", "csv=p=0", video]).decode())
    t = min(max(0.0, t), _dur[video] - 0.1)            # beats may run past the cut (end-card hold)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                                   "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1)

def _placeholder(cv, box, text):
    d = ImageDraw.Draw(cv)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 26, outline=(255, 255, 255, 170), width=4)
    for x in range(x0 + 30, x1 - 30, 36):                     # dashed inner hint
        d.line([(x, y0 + 18), (x + 16, y0 + 18)], fill=(255, 255, 255, 60), width=2)
    f = font(SFD("Semibold"), 46)
    words, lines, cur = text.split(), [], ""
    for w in words:
        if f.getlength(cur + " " + w) > (x1 - x0 - 100) and cur: lines.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    if cur: lines.append(cur)
    y = (y0 + y1) / 2 - len(lines) * 30
    for ln in lines:
        d.text(((x0 + x1) / 2 - f.getlength(ln) / 2, y), ln, font=f, fill=(235, 235, 240)); y += 60
