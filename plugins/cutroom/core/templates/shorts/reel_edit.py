"""Edit a talking-head clip in the reel look (skills/reel-edit): jump cuts, a punch-in on every cut, a new caption
style per section, words behind the head, full-screen word slabs, a transcript split screen, screen cuts, background
swaps, reference videos in five forms, popped cards, whip /
glitch / flash transitions and a sound on every hit.

    python3 reel_edit.py OUT.mp4 --video talk.mp4 --words words.json [--mask mask.mp4] [--plan plan.json]
                         [--face-y 0.34] [--preview 1.6,8.0]

The plan is written from the transcript (see skills/reel-edit/SKILL.md). Every time in it is a cue: a spoken
phrase ("design file"), found in the transcript after `after` (a cue or source seconds), or a number of source
seconds. Without --plan an automatic one is built from the sentences and saved as OUT.plan.json to edit.
"""
import sys, os, json, argparse, inspect, tempfile, wave
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from cutroom import viral as V, blocks as B, sound as S, parallel
from cutroom.core import W, H, FPS, probe_duration
from look_edit import load_words, norm

CAPTION_CYCLE = ["pop", "serif", "pop", "sticker"]
TRANSITION_CYCLE = [None, "whip", "flash", "glitch", "whip"]
ZOOM_CYCLE = [1.0, 1.3, 1.1, 1.35]
SFX_FOR = {"whip": ("whoosh", 1.0), "glitch": ("shutter", 1.0), "crack": ("impact", 0.8), "circle": ("whoosh", 0.8),
           "zoom": ("whoosh", 0.8)}
REF_SFX = {"inset": ("whoosh", 0.7), "fan": ("click", 0.8), "float": ("whoosh", 0.7), "fly": ("whoosh", 0.9),
           "result": ("impact", 0.8)}
FULL_FRAME = ("inset", "result")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
STOP = set("about after again also always because been before being could didn't doesn't every from have here into "
           "just like make made really should something that their there these thing things think this those through "
           "video what when where which while with would your you're".split())


def find(words, phrase, after=-1.0):
    seq = [norm(x) for x in str(phrase).split()]
    for i in range(len(words) - len(seq) + 1):
        if words[i]["s"] > after and all(norm(words[i + j]["w"]) == seq[j]
                                         or (j == len(seq) - 1 and norm(words[i + j]["w"]).startswith(seq[j]))
                                         for j in range(len(seq))):
            return words[i]["s"]
    return None


def keep_from_words(words, total, gap=0.3, pad=0.08):
    keep = [[max(0.0, words[0]["s"] - pad), words[0]["e"]]]
    for w_ in words[1:]:
        if w_["s"] - keep[-1][1] > gap:
            keep[-1][1] = min(total, keep[-1][1] + pad)
            keep.append([w_["s"] - pad, w_["e"]])
        else:
            keep[-1][1] = w_["e"]
    keep[-1][1] = min(total, keep[-1][1] + 0.35)
    return [[round(x, 2), round(y, 2)] for x, y in keep]


def auto_plan(words, total):
    sections, cur = [], []
    for i, w_ in enumerate(words):
        cur.append(w_)
        nxt = words[i + 1]["s"] if i + 1 < len(words) else total
        if cur[-1]["e"] - cur[0]["s"] >= 3.0 and (w_["w"][-1:] in ".?!" or nxt - w_["e"] > 0.3):
            sections.append(cur)
            cur = []
    if cur:
        if sections and cur[-1]["e"] - cur[0]["s"] < 1.5:
            sections[-1] += cur
        else:
            sections.append(cur)
    keep = keep_from_words(words, total)
    plan = {"keep": keep if len(keep) > 1 else None, "sections": [], "moments": []}
    for i, sec in enumerate(sections):
        cands = [V.key_of(w_["w"]) for w_ in sec if len(V.key_of(w_["w"])) >= 5 and V.key_of(w_["w"]) not in STOP]
        key = max(cands, key=len) if cands else None
        plan["sections"].append({"at": round(sec[0]["s"], 2), "caption": CAPTION_CYCLE[i % len(CAPTION_CYCLE)],
                                 "zoom": ZOOM_CYCLE[i % len(ZOOM_CYCLE)],
                                 "transition": TRANSITION_CYCLE[i % len(TRANSITION_CYCLE)] if i else None,
                                 "keys": [key] if key else []})
    first = plan["sections"][0]["keys"] if plan["sections"] else []
    if first:
        plan["moments"].append({"do": "punch", "at": first[0], "until": "+0.8", "zoom": 1.5})
    return plan


class Reel:
    def __init__(self, words, plan, tl, sfx, has_mask=False, fy=0.34, base="."):
        self.src_words, self.plan, self.tl, self.reg, self.has_mask, self.fy = words, plan, tl, sfx, has_mask, fy
        self.base, self.clips = base, {}
        self.words = tl.map_words(words)
        self.keys = {V.key_of(k) for k in plan.get("keys", [])}
        self.events, self.hits = [], []
        self.sections = self.place_sections()
        self.moments = [self.place_moment(m) for m in plan.get("moments", [])]
        self.moments = [m for m in self.moments if m]
        self.add_sfx()

    def src_time(self, cue, after=-1.0):
        if cue is None:
            return None
        if isinstance(cue, (int, float)):
            return float(cue)
        if isinstance(cue, str) and cue.startswith("+"):
            return after + float(cue[1:])
        return find(self.src_words, cue, after)

    def out_time(self, cue, after=-1.0):
        s = self.src_time(cue, after)
        return None if s is None else self.tl.out(s)

    def place_sections(self):
        out, after = [], -1.0
        for n, sec in enumerate(self.plan["sections"]):
            s = 0.0 if n == 0 else self.src_time(sec["at"], after)
            if s is None:
                print("section cue not found:", sec["at"])
                continue
            after = s
            out.append(dict(sec, t=self.tl.out(s), keys={V.key_of(k) for k in sec.get("keys", [])} | self.keys))
        for a, b in zip(out, out[1:]):
            a["end"] = b["t"]
        out[-1]["end"] = self.tl.duration
        return out

    def place_moment(self, m):
        after = self.src_time(m.get("after"), -1.0) if m.get("after") is not None else -1.0
        s = self.src_time(m["at"], after if after is not None else -1.0)
        if s is None:
            print("moment cue not found:", m["do"], m["at"])
            return None
        t = self.tl.out(s)
        sec = self.section_at(t)
        u = self.out_time(m.get("until"), s) if m.get("until") is not None else None
        out = dict(m, t=t, end=u if u is not None else sec["end"])
        for k in ("then", "badge_at", "saved_at", "word_at", "mark_at", "to", "box_at", "zoom_at"):
            if isinstance(m.get(k), (str, int, float)) and k != "mark_at":
                out[k + "_t"] = self.out_time(m[k], s)
        if m["do"] == "split" and m.get("mark"):
            out["mark_t"] = self.out_time(m["mark"], s)
        if m["do"] == "slide":
            after_cut, out["cuts_t"] = s, []
            for c in m.get("cuts", []):
                after_cut = self.src_time(c, after_cut)
                if after_cut is None:
                    print("slide cut cue not found:", c)
                    break
                out["cuts_t"].append(self.tl.out(after_cut))
        return out

    def section_at(self, t):
        return next((s for s in reversed(self.sections) if t >= s["t"]), self.sections[0])

    def active(self, t, *kinds):
        return [m for m in self.moments if m["do"] in kinds and m["t"] <= t < m["end"]]

    def cue(self, t, name, g=1.0):
        if t is not None and name in self.reg:
            self.events.append((t, name, g))

    def add_sfx(self):
        for s in self.sections[1:]:
            if s.get("transition") in SFX_FOR:
                self.cue(s["t"], *SFX_FOR[s["transition"]])
        for m in self.moments:
            do, t = m["do"], m["t"]
            if do == "punch" and m.get("zoom", 1.5) >= 1.4:
                self.cue(t, "impact", 0.8)
                self.hits.append((t, 14))
            elif do in ("behind", "count"):
                self.cue(t, "whoosh" if do == "behind" else "counter", 0.6 if do == "behind" else 1.0)
                self.cue(m.get("badge_at_t"), "ding", 1.2)
            elif do == "slab":
                self.cue(t, "shutter", 1.3)
            elif do == "split":
                self.cue(t, "whoosh", 1.0)
                self.cue(m.get("mark_t"), "click", 0.7)
            elif do in ("card", "chip", "badge"):
                self.cue(t + (0.15 if do == "card" else 0), "click", 0.6)
            elif do == "note":
                self.cue(t, "typing", 1.0)
                self.cue(m.get("saved_at_t"), "click", 0.8)
            elif do == "comment":
                self.cue(t, "whoosh", 0.7)
                self.cue(m.get("word_at_t"), "impact", 0.9)
                if m.get("word_at_t") is not None:
                    self.hits.append((m["word_at_t"], 12))
            elif do == "flash":
                self.cue(t, "impact", 0.6)
            elif do == "clip":
                self.cue(t, "whoosh", 0.7)
            elif do == "point":
                self.cue(t + 0.1, "click", 0.6)
            elif do == "screen":
                self.cue(t, "whoosh", 0.8)
                self.cue(m.get("box_at_t"), "click", 0.9)
                self.cue(m.get("zoom_at_t"), "whoosh", 0.6)
            elif do == "swap":
                self.cue(t, "whoosh", 0.9)
            elif do == "slide":
                self.cue(t, "whoosh", 0.6)
                for c in m["cuts_t"]:
                    self.cue(c, "click", 0.5)
                if m.get("exit", True):
                    self.cue(m["end"] - V.SLIDE_FALL, "whoosh", 0.4)
            elif do == "refs":
                self.cue(t, *REF_SFX.get(m.get("mode", "inset"), ("whoosh", 0.7)))
            elif do == "orbit":
                self.cue(t, "whoosh", 0.8)
                self.cue(m["end"] - 0.3, "whoosh", 0.4)
            elif do == "spotlight":
                self.cue(t, "whoosh", 0.5)
        for e in self.plan.get("sfx", []):
            self.cue(self.out_time(e["at"], self.src_time(e.get("after"), -1.0) if e.get("after") else -1.0),
                     e["name"], e.get("gain", 1.0))
        self.events.sort()

    def zoom(self, t):
        return self.base_zoom(t) * (1.1 if self.active(t, "swap") else 1.0)

    def base_zoom(self, t):
        sec = self.section_at(t)
        punches = self.active(t, "punch")
        if punches:
            p = punches[-1]
            return p.get("zoom", 1.5) + 0.06 * (t - p["t"])
        z = self.cut_zoom(t, sec)
        for m in self.active(t, "spotlight"):
            k, out = t - m["t"], m["end"] - m["t"] - 0.3
            push = z + (m.get("zoom", 1.4) - z) * V.cubic(min(1.0, k / m.get("push", 0.8)))
            z += (push - z) * (1 - V.inout(max(0.0, min(1.0, (k - out) / 0.3))))
        return z

    def cut_zoom(self, t, sec):
        cuts = [c for c in self.tl.cuts if sec["t"] <= c <= t]
        t0 = max([sec["t"]] + cuts)
        z = sec.get("zoom", 1.0) * (1.12 if len(cuts) % 2 else 1.0)
        return z + 0.035 * (t - t0)

    def shake(self, t):
        dx = dy = 0.0
        for a, amp in self.hits:
            x, y = B.shake(t, a, amp, 0.32)
            dx, dy = dx + x, dy + y
        return dx, dy

    def caption_rest(self, t):
        sec = self.section_at(t)
        return sec.get("cy", inspect.signature(V.CAPTIONS[sec.get("caption", "pop")]).parameters["cy"].default)

    def caption(self, cv, t, cy=None):
        sec = self.section_at(t)
        covers = [m for m in self.active(t, "behind", "comment", "count") if not m.get("captions")
                  and (m["do"] != "comment" or m.get("word_at_t") is not None and t >= m["word_at_t"])]
        if covers or any(m.get("mode") == "result" for m in self.active(t, "refs")):
            return
        fn = V.CAPTIONS[sec.get("caption", "pop")]
        ws = [w_ for w_ in self.words if sec["t"] - 0.01 <= w_["s"] < sec["end"]]
        kw = {"keys": sec["keys"]} if "keys" in fn.__code__.co_varnames else {}
        if cy is not None or "cy" in sec:
            kw["cy"] = cy if cy is not None else sec["cy"]
        fn(cv, t, ws, **kw)

    def transitions(self, cv, t):
        for s in self.sections[1:]:
            name = s.get("transition")
            if name and -0.12 <= t - s["t"] < 0.45:
                kw = {"direction": s.get("direction", 1)} if name == "whip" else {}
                cv = V.transition(cv, name, t - s["t"], **kw)
        for m in self.moments:
            if m["do"] == "flash":
                cv = V.flash(cv, t - m["t"])
        return cv

    def frames(self, m, k, size=(720, 1280), key="files"):
        out = []
        for i, f in enumerate(m.get(key) or [m["file"]]):
            r = self.clips.setdefault((id(m), i), V.ClipReader(os.path.join(self.base, f), size[0], size[1], m.get("start", 0.0)))
            out.append(r.at(k))
        return out

    def slide_media(self, m, t):
        files = m.get("files") or [m["file"]]
        i = sum(c <= t for c in m["cuts_t"])
        i = min(i, len(files) - 1)
        since = t - (m["cuts_t"][i - 1] if i else m["t"])
        path = os.path.join(self.base, files[i])
        join = m.get("join", H // 2)
        if os.path.splitext(path)[1].lower() in VIDEO_EXT:
            reader = self.clips.setdefault((id(m), i), V.ClipReader(path, W, H - join, m.get("start", 0.0)))
            return reader.at(since)
        focus = tuple(m.get("focus", {}).get(files[i], (0.5, 0.5)))
        return V.slide_push(V.slide_still(path, W, H - join, focus), since, W, H - join)

    def slide(self, m, t, fr):
        k = t - m["t"]
        join = m.get("join", H // 2)
        cuts = sum(m["t"] < c <= t for c in self.tl.cuts)
        panel_z = m.get("zoom", 1.0) * (1.06 if cuts % 2 else 1.0) + 0.012 * k
        out_k = t - (m["end"] - V.SLIDE_FALL) if m.get("exit", True) else None
        cv = V.slide(fr, self.slide_media(m, t), k, self.base_zoom(t), panel_z, self.fy, join, m.get("face", 0.42), out_k)
        rest = self.caption_rest(t)
        self.caption(cv, t, round(rest + (m.get("cy", join) - rest) * V.slide_ease(k, out_k)))
        return self.transitions(cv, t)

    def frame(self, i, srcs):
        t = i / FPS
        cv = self.draw(t, srcs)
        for m in self.active(t, "label"):
            V.label(cv, m["text"], m.get("y", 120))
        return cv

    def draw(self, t, srcs):
        fr = srcs[0].at(t).convert("RGBA")
        mk = srcs[1].at(t) if len(srcs) > 1 else None
        slabs = self.active(t, "slab")
        if slabs:
            m = slabs[-1]
            bg, fg = V.SLAB.get(m.get("color", "orange"), V.SLAB["orange"])
            return self.transitions(V.slab(t - m["t"], m["text"], bg, fg), t)
        splits = self.active(t, "split")
        if splits:
            m = splits[-1]
            ws = [w_ for w_ in self.words if m["t"] - 0.01 <= w_["s"] < m["end"]]
            mark_t = m.get("mark_t")
            cv = V.split(fr, t, ws, t - m["t"], self.fy, m.get("title", "audio.json"), m.get("sub", "every word, with its time"),
                         V.key_of(m["mark"]) if m.get("mark") else None, t - mark_t if mark_t is not None else None,
                         m.get("chip", "✂ cut the gaps"))
            self.caption(cv, t)
            return self.transitions(cv, t)
        slides = self.active(t, "slide")
        if slides:
            return self.slide(slides[-1], t, fr)
        screens = self.active(t, "screen")
        if screens:
            m = screens[-1]
            k = t - m["t"]
            bt, zt = m.get("box_at_t"), m.get("zoom_at_t")
            cv = V.screen(self.frames(m, k)[0], k, m.get("box"), t - bt if bt is not None else None, t - zt if zt is not None else None)
            self.caption(cv, t)
            return self.transitions(cv, t)
        full = [m for m in self.active(t, "refs") if m.get("mode", "inset") in FULL_FRAME]
        if full and full[-1].get("mode", "inset") == "inset":
            m = full[-1]
            cv = V.inset(self.frames(m, t - m["t"])[0], t - m["t"], m.get("w", 760), m.get("y", 880), m.get("via"))
            self.caption(cv, t)
            return self.transitions(cv, t)
        z = self.zoom(t)
        dx, dy = self.shake(t)
        cv = V.shot(fr, z, self.fy, dx, dy)
        mshot = V.shot(mk, z, self.fy, dx * mk.width / W, dy * mk.width / W) if mk is not None else None
        for m in self.active(t, "blur"):
            V.blur_band(cv, m.get("y", 1250), m.get("h", 300))
        for m in self.active(t, "spotlight"):
            cv = V.spotlight(cv, t - m["t"], V.person(cv, mshot) if mshot is not None else None, m.get("text"),
                             m.get("y", H * self.fy - 290), tuple(m.get("rgb", V.NEON)), m.get("dim", 0.86), m.get("blur", 12),
                             m["end"] - m["t"] - 0.3)
        for m in self.active(t, "orbit"):
            k = t - m["t"]
            V.orbit(cv, k, self.frames(m, k, (360, 640)), V.person(cv, mshot) if mshot is not None else None,
                    (W / 2, m.get("y", H * self.fy + 40)), m.get("rx", 430), m.get("ry", 300), m.get("w", 180),
                    m.get("speed", 1.1), m.get("tilt", -8.0), m["end"] - m["t"] - 0.22)
        for m in self.active(t, "swap"):
            if mshot is not None:
                k = t - m["t"]
                tiles = self.frames(m, k, (360, 640), "wall") if m.get("wall") else None
                cv = V.swap(cv, mshot, k, V.SLAB.get(m.get("color", "orange"), V.SLAB["orange"])[0], tiles)
        for m in self.active(t, "refs"):
            mode, k = m.get("mode", "inset"), t - m["t"]
            cutout = V.person(cv, mshot) if mshot is not None else None
            if mode == "float":
                V.depth(cv, k, self.frames(m, k, (360, 640)), cutout, m["end"] - m["t"] - 0.12)
            elif mode == "fly":
                V.fly(cv, k, self.frames(m, k, (360, 640)), cutout, (W / 2, H * self.fy + 60))
        for m in self.active(t, "behind", "count", "comment"):
            if m["do"] == "comment" and not m.get("word_at_t") or m["do"] == "comment" and t < m["word_at_t"]:
                continue
            t0 = m["word_at_t"] if m["do"] == "comment" else m["t"]
            cv = V.darken(cv, (t - t0) / 0.2 if m["do"] != "count" else 1.2)
            if m["do"] == "count":
                to = m.get("to_t") or m["t"] + 1.0
                v = int(m.get("value", 100) * V.cubic((t - m["t"]) / max(0.2, to + 0.3 - m["t"])))
                lay = V.big_word(t - m["t"], f"{v}", m.get("size", 380), V.GOLD, m.get("y", 690), m.get("label"))
            elif m["do"] == "comment":
                lay = V.big_word(t - t0, m["word"], m.get("size", 400), V.GOLD, m.get("y", 700), m.get("sub", "comment"))
            else:
                lay = V.big_word(t - m["t"], m["text"], m.get("size", 330), V.WHITE, m.get("y", 700), m.get("sub"))
            if mshot is not None:
                V.behind(cv, lay, V.person(cv, mshot))
            else:
                cv.alpha_composite(lay)
            if m["do"] == "count" and m.get("badge_at_t") is not None:
                V.badge(cv, t - m["badge_at_t"], m.get("badge", "✓ all clear"), cy=m.get("badge_y", 1270))
        for m in self.active(t, "logo"):
            V.logo(cv, t - m["t"], m.get("x", 820), m.get("y", 420))
        for m in self.active(t, "card"):
            V.file_card(cv, t - m["t"], m.get("title", "design.md"), [tuple(r) for r in m.get("rows", [])], m.get("tag"), m.get("y", 360))
        for m in self.active(t, "note"):
            sk = m.get("saved_at_t")
            V.note(cv, t - m["t"] + 0.15, m["text"], t - sk if sk is not None else None, m.get("saved", "✓ saved to memory"), m.get("y", 330))
        boxes = []
        for m in self.active(t, "clip"):
            k = t - m["t"]
            reader = self.clips.setdefault(id(m), V.ClipReader(os.path.join(self.base, m["file"]), start=m.get("start", 0.0)))
            box = V.floating_clip(cv, k, reader.at(k), m.get("x", W / 2), m.get("y", 430), m.get("w", 560), m.get("rot", -3.0),
                                  m.get("via"), m["end"] - m["t"] - 0.12)
            if box:
                boxes.append(box)
        for m in self.active(t, "point"):
            target = m.get("target", "clip")
            if target == "clip":
                if not boxes:
                    continue
                x0, y0, x1, y1 = boxes[-1]
                target = ((x0 + x1) / 2 + (x1 - x0) * 0.18, y1 - 10)
            V.pointer(cv, t - m["t"], m["text"], tuple(target), m.get("x", 760), m.get("y", 1000), tuple(m.get("rgb", V.GOLD)),
                      m["end"] - m["t"] - 0.1)
        for m in self.active(t, "refs"):
            if m.get("mode") == "fan":
                V.fan(cv, t - m["t"], self.frames(m, t - m["t"], (360, 640)), m.get("y", 520))
        for m in self.active(t, "badge"):
            V.badge(cv, t - m["t"], m["text"], tuple(m.get("rgb", V.GREEN)), m.get("y", 1270))
        for m in self.active(t, "chip"):
            V.pop(cv, V.chip(m["text"], tuple(m.get("rgb", V.WHITE)), tuple(m.get("fg", V.BLACK)), m.get("size", 48), m.get("emoji")),
                  t - m["t"], m.get("x", W / 2), m.get("y", 520), m.get("rot", -3), out=m["end"] - m["t"] - 0.1)
        for m in self.active(t, "emoji"):
            V.pop(cv, V.big_emoji(m["text"], m.get("size", 220)), t - m["t"], m.get("x", 820), m.get("y", 560), m.get("rot", 8),
                  out=m["end"] - m["t"] - 0.1)
        if full:
            m = full[-1]
            cv = V.result(self.frames(m, t - m["t"])[0], t - m["t"], cv)
        self.caption(cv, t)
        for m in self.active(t, "comment"):
            V.comment_bar(cv, t - m["t"], m["word"], t - m["word_at_t"] if m.get("word_at_t") is not None else None)
        return self.transitions(cv, t)

    def mix(self, voice_path, out_wav):
        clips = []
        for t, name, g in self.events:
            r = self.reg[name]
            dur = 0.9 if name == "typing" else r.get("dur")
            clips.append(S.at(t, S.load(r["file"], r["gain"] * g * 1.6, r.get("start", 0.0), dur), r["onset"]))
        return S.mix(voice_path, self.tl.duration, clips, out_wav, dry=0)


def write_wav(path, x, sr=S.SR):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--video", required=True)
    ap.add_argument("--words", required=True)
    ap.add_argument("--mask")
    ap.add_argument("--plan")
    ap.add_argument("--face-y", type=float, default=0.34)
    ap.add_argument("--preview")
    ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    total = probe_duration(a.video)
    voice = S.read_voice(a.video)
    words = load_words(a.words)
    if a.plan:
        plan = json.load(open(a.plan))
    else:
        plan = auto_plan(words, total)
        json.dump(plan, open(os.path.splitext(a.out)[0] + ".plan.json", "w"), indent=1)
    tl = V.Timeline(plan["keep"]) if plan.get("keep") else V.Timeline.from_audio(voice, total)
    reg = {k: v for k, v in json.load(open(os.path.join(S.SFX_DIR, "sfx.json"))).items()
           if not k.startswith("_") and v.get("status") == "ok"}
    has_mask = bool(a.mask and os.path.exists(a.mask))
    reel = Reel(words, plan, tl, reg, has_mask, a.face_y, os.path.dirname(os.path.abspath(a.plan)) if a.plan else os.getcwd())
    print(f"{total:.2f}s -> {tl.duration:.2f}s, {len(tl.cuts)} jump cuts, {len(reel.sections)} sections, "
          f"{len(reel.moments)} moments, {len(reel.events)} sounds")

    def open_sources(t0):
        srcs = [V.JumpReader(a.video, tl, t0)]
        if has_mask:
            srcs.append(V.JumpReader(a.mask, tl, t0, 540, 960))
        return tuple(srcs)

    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            srcs = open_sources(t)
            reel.frame(int(round(t * FPS)), srcs).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
            for s in srcs:
                s.close()
    else:
        tmp = tempfile.mkdtemp()
        vw = os.path.join(tmp, "voice.wav")
        write_wav(vw, tl.cut_audio(voice))
        mixed = reel.mix(vw, os.path.join(tmp, "mix.wav"))
        parallel.render(a.out, int(tl.duration * FPS), reel.frame, open_sources, audio=mixed, workers=a.workers)
        print("wrote", a.out)
