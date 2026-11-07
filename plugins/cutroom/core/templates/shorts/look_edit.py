"""Edit a talking-head clip in one of the looks (cutroom.light or cutroom.cinematic), timed to its transcript.

Each beat starts on a spoken cue word; the next beat's cue ends it. Captions come from the real words. The
default beats fit a "Claude edited this video" script (claim, one take, every word, silences, design file,
every frame, memory, comment CTA); pass --beats to swap the cue words.

    python3 look_edit.py OUT.mp4 --look light|cinematic --video talk.mp4 --words words.json [--mask mask.mp4]

words.json: [{"w": "Okay", "s": 0.12, "e": 0.40}, ...] or {"words": [{"word", "start", "end"}]} (Whisper style).
--mask: the person mask video (white person on black), needed for text behind the head.
"""
import sys, os, re, json, argparse
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))
from PIL import Image, ImageDraw
from cutroom import light as L, cinematic as C
from cutroom.core import W, H, FPS, font, MONO, Reader, probe_duration
from cutroom import parallel

BEATS = {
    "light": ["recorded", "wrote", "silences", "design", "checked", "note", "comment"],
    "cinematic": ["one", "wrote", "silences", "design", "checked", "note", "comment"],
}
KEYS = {"entire", "one", "every", "silences", "design", "frame", "remembers", "edit", "touch", "single"}

def load_words(path):
    data = json.load(open(path))
    rows = data["words"] if isinstance(data, dict) else data
    out = []
    for r in rows:
        w_ = (r.get("w") or r.get("word") or r.get("text") or "").strip()
        if w_: out.append({"w": w_, "s": float(r.get("s", r.get("start", 0))), "e": float(r.get("e", r.get("end", 0)))})
    return out

def norm(w_): return re.sub(r"[^a-z0-9]", "", w_.lower())

def cue_times(words, cues, total):
    times, t_prev = [], 0.0
    for i, c in enumerate(cues):
        hit = next((w_["s"] for w_ in words if w_["s"] > t_prev + 0.3 and norm(w_["w"]).startswith(c)), None)
        if hit is None: hit = t_prev + (total - t_prev) / (len(cues) - i + 1)
        times.append(hit); t_prev = hit
    return times

def phrases(words, n=3, gap=0.3):
    out, cur = [], []
    for i, w_ in enumerate(words):
        if cur and (len(cur) >= n or w_["s"] - cur[-1]["e"] > gap): out.append(cur); cur = []
        cur.append(w_)
    if cur: out.append(cur)
    spans = []
    for i, ph in enumerate(out):
        t1 = out[i + 1][0]["s"] if i + 1 < len(out) else ph[-1]["e"] + 0.5
        spans.append((ph, ph[0]["s"], t1))
    return spans

def key_spans(words):
    spans = []
    for ph, t0, t1 in phrases(words):
        ws = [w_["w"].strip(",.!?").lower() for w_ in ph]
        ki = next((j for j, w_ in enumerate(ws) if norm(w_) in KEYS), None)
        txt = " ".join(ws) if ki is None else " ".join(ws[:ki]) + f" *{ws[ki]}* " + " ".join(ws[ki + 1:])
        spans.append((txt.strip(), t0, t1))
    return spans

def words_in(words, t0, t1, n=10):
    return [w_ for w_ in words if t0 <= w_["s"] < t1][:n]

def light_screen(fn):
    cv = L.canvas(); fn(cv)
    return cv.crop((40, 160, 1040, 900)).convert("RGB")

def terminal(lines):
    im = Image.new("RGB", (1000, 120 + 74 * len(lines)), (14, 14, 16)); d = ImageDraw.Draw(im); f = font(MONO, 30)
    for i, (c, s) in enumerate(lines): d.text((48, 60 + i * 74), s, font=f, fill=c)
    return im

class Edit:
    def __init__(self, look, words, total, cues):
        self.look, self.words, self.total = look, words, total
        self.t = [0.0] + cue_times(words, cues, total)
        self.fns = self.light_beats() if look == "light" else self.cinematic_beats()
        self.captions = [(w_["w"], w_["s"]) for w_ in words]
        self.keys = key_spans(words)

    def beat_at(self, t):
        for i in range(len(self.t) - 1, -1, -1):
            if t >= self.t[i]: return i, t - self.t[i]
        return 0, t

    def light_beats(self):
        t, ws = self.t, self.words
        wl = words_in(ws, t[2], t[3])
        return [
            lambda cv, k: L.hook_card(cv, k, "Claude just edited this entire video", name="Maya"),
            lambda cv, k: L.prompt_card(cv, k, "Edit this video. One take: cut only in the silences, follow design.md, check every frame.",
                                        file="raw.mp4", t_file=0.05, t_type=0.15, cps=44, t_send=t[2] - t[1] - 0.35,
                                        t_check=t[2] - t[1] - 0.15, statuses=[(0, "Step 1 of 4", False)]),
            lambda cv, k: L.words_card(cv, k, [(f"{w_['s']:.2f}s", w_["w"].strip(",.!?"), w_["s"] - t[2]) for w_ in wl],
                                       statuses=[(0, "Step 2 of 4", False), (t[3] - t[2] - 0.3, f"{len(ws)} words", True)]),
            lambda cv, k: L.wave_card(cv, k, t_play=(0.05, 0.9), t_cut=1.0, statuses=[(0, "Step 2 of 4", False), (1.9, "Cut", True)]),
            lambda cv, k: L.style_card(cv, k, [("Type", "SF Pro, one line", 0.1), ("Colour", [(255, 255, 255), (22, 22, 26), L.BLUE], 0.5),
                                               ("Graphics", "White, one blue", 0.9)], statuses=[(0, "Step 3 of 4", False)]),
            lambda cv, k: L.check_card(cv, k, [("Every cut", "lands in a silence", 0.2), ("Every frame", "nothing off-screen", 0.6),
                                               ("Every second", "captions in sync", 1.0)],
                                       statuses=[(0, "Step 4 of 4", False), (1.3, "All passed", True)]),
            lambda cv, k: L.memory_card(cv, k, "make the captions bigger", ["Captions: one line, SF Pro", "Cut only in silences"],
                                        "Captions a size bigger", cps=34, t_save=1.0),
            lambda cv, k: L.cta_card(cv, k, "EDIT", ("I'll send you the ", "setup", " + the prompts")),
        ]

    def cinematic_beats(self):
        t, ws = self.t, self.words
        wl = words_in(ws, t[2], t[3], 6)
        prompt = light_screen(lambda cv: L.prompt_card(cv, 9, "Edit this video. One take, cut only in the silences.", t_type=0, cps=99,
                                                       file="raw.mp4", t_check=0, cy=520))
        trans = terminal([((217, 119, 87), "✻ Transcribing raw.mp4")] +
                         [((200, 200, 204), f"  {w_['s']:6.2f}s  {w_['w'].strip(',.!?')}") for w_ in wl])
        wave = light_screen(lambda cv: L.wave_card(cv, 3.0, statuses=[(0, "Cut", True)], cy=520))
        style = light_screen(lambda cv: L.style_card(cv, 3.0, [("Type", "New York, one line", 0), ("Colour", [(255, 255, 255), C.YELLOW], 0),
                                                               ("Grade", "Teal and warm", 0)], cy=520))
        return [
            lambda cv, k, p: C.serif_title(cv, k, "Claude just edited / *this entire video*", cy=250),
            lambda cv, k, p: C.behind_word(cv, k, "ONE TAKE", p, cy=760, size=300) if p is not None else C.headline(cv, k, "one take", cy=330),
            lambda cv, k, p: C.float_card(cv, k, trans, cy=360, w=900, source="via terminal"),
            lambda cv, k, p: C.float_card(cv, k, wave, cy=360, w=900, source="via raw.mp4"),
            lambda cv, k, p: C.float_card(cv, k, style, cy=360, w=900, source="via design.md"),
            lambda cv, k, p: C.headline(cv, k, "every frame", cy=330, out=min(1.6, t[6] - t[5] - 0.05)),
            lambda cv, k, p: (C.spotlight(cv, k, cx=540, cy=1050, r=520), C.hook_box(cv, k - 0.2, "It remembers / my notes.", cy=300)),
            lambda cv, k, p: (C.comment_bar(cv, k, "EDIT", cy=1600, t_type=0.2, t_post=0.9),
                              C.follow_row(cv, k - 1.3, "maya.makes", cy=1760, t_tap=0.7) if k > 1.3 else None),
        ]

    def frame(self, i, srcs):
        t = i / FPS
        bi, k = self.beat_at(t)
        fr = srcs[0].next(); m = srcs[1].next() if len(srcs) > 1 else None
        if self.look == "light":
            cv = L.canvas(i)
            self.fns[bi](cv, k)
            L.face_panel(cv, fr)
            L.caption(cv, t, self.captions)
            return cv
        cv = C.grade(fr)
        person = C.cutout(cv, m) if m is not None else None
        self.fns[bi](cv, k, person)
        C.key_caption(cv, t, self.keys, cy=1300 if bi < 7 else 1180)
        return cv

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--look", choices=("light", "cinematic"), required=True)
    ap.add_argument("--video", required=True); ap.add_argument("--words", required=True); ap.add_argument("--mask")
    ap.add_argument("--beats", help="comma-separated cue words, one per beat after the hook")
    ap.add_argument("--preview"); ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    total = probe_duration(a.video)
    ed = Edit(a.look, load_words(a.words), total, a.beats.split(",") if a.beats else BEATS[a.look])
    def open_sources(t0):
        srcs = [Reader(a.video, W, H, start=t0)]
        if a.mask and os.path.exists(a.mask): srcs.append(Reader(a.mask, 540, 960, start=t0))
        return tuple(srcs)
    print("beats at", ", ".join(f"{x:.2f}s" for x in ed.t))
    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            srcs = open_sources(t)
            ed.frame(int(round(t * FPS)), srcs).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
            for s in srcs: s.close()
    else:
        parallel.render(a.out, int(total * FPS), ed.frame, open_sources, audio=a.video, workers=a.workers)
