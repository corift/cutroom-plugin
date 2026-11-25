"""Autocut: the whole edit as one small JSON file, so any model (or no model) can drive it.

  python3 -m cutroom.autocut ingest VIDEO_DIR          clips/ -> edit/source.mp4, transcript, sentences, first edit.json
  python3 -m cutroom.autocut show VIDEO_DIR            the sentences with what is kept and cut, and the settings
  python3 -m cutroom.autocut set VIDEO_DIR '{"cut": [3], "keep": [5], "captions": {"style": "pop"}}'
  python3 -m cutroom.autocut render VIDEO_DIR          edit.json -> edit/cut_vN.mp4 (+ cut.script.md, storyboard.json)
  python3 -m cutroom.autocut check VIDEO_DIR           listen back to the cut: every join, clipped or stray words, what was heard
  python3 -m cutroom.autocut plan VIDEO_DIR            edit.json -> edit/plan_vN.json: the same cut as data, for a device to render
  python3 -m cutroom.autocut status VIDEO_DIR          one JSON line: clips, what is ingested, renders, settings
  python3 -m cutroom.autocut sheet VIDEO_DIR [FILE] [FPS]   a contact sheet of FILE (default: the latest render, else the source) -> edit/sheet_*.jpg
  python3 -m cutroom.autocut adopt VIDEO_DIR FILE      a video made outside render becomes the next edit/cut_vN.mp4
  python3 -m cutroom.autocut reference VIDEO_DIR NAME  clips/NAME is a video to imitate, not footage: left out of the edit, measured (shots, pace, shape) and laid out as edit/sheet_*.jpg

VIDEO_DIR holds clips/ (the uploads, joined in name order or clips/order.json) and edit/ (everything made here).
edit.json:
  cut        sentence ids left out          auto      ids the retake detector cut (a subset of cut)
  trims      [[s, e]] source seconds removed inside kept sentences (stumbles, restarts)
  nudges     [{"edge": start|end, "at": source seconds, "by": seconds}] one cut edge moved: positive keeps more sound
  captions   {"style": plain|kallaway|pop|box|subtitle|rpn|spread|feature|masthead|none, "position": top|middle|bottom|null,
              "emphasis": ["key phrase"], "fixes": {"heard": "meant"}}
  format     vertical | source              pace      tight | natural
  zoom       punch | none                   hook      text shown over the first seconds ("" for none)
  template   a named look from TEMPLATES; setting it replaces captions.style, pace, zoom and format
"""
import difflib, functools, hashlib, json, os, re, subprocess, sys

from PIL import Image, ImageDraw

from . import captions as cap, cutplan as cp, parallel
from .core import FPS, Reader, cover, display, font, mezzanine, probe_duration, probe_size, stamp, text_img, wrap, HELV

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
EDITORIAL = ("spread", "feature", "masthead")
STYLES = ("plain", "kallaway", "pop", "box", "subtitle", "rpn", "none", *EDITORIAL)
POSITIONS = {"top": 0.2, "middle": 0.5, "bottom": 0.74}
DEFAULTS = {"template": "clean", "cut": [], "auto": [], "trims": [], "nudges": [], "format": "vertical", "pace": "tight", "zoom": "none", "hook": "",
            "captions": {"style": "plain", "position": None, "emphasis": [], "fixes": {}}}
TEMPLATES = {
    "clean": {"captions": "plain", "pace": "tight", "zoom": "none", "format": "vertical", "hook": False},
    "punchy": {"captions": "pop", "pace": "tight", "zoom": "punch", "format": "vertical", "hook": True},
    "bold": {"captions": "kallaway", "pace": "tight", "zoom": "punch", "format": "vertical", "hook": False},
    "calm": {"captions": "subtitle", "pace": "natural", "zoom": "none", "format": "vertical", "hook": False},
    "podcast": {"captions": "box", "pace": "natural", "zoom": "none", "format": "source", "hook": False},
    "raw": {"captions": "none", "pace": "tight", "zoom": "none", "format": "source", "hook": False},
    "spread": {"captions": "spread", "pace": "tight", "zoom": "none", "format": "vertical", "hook": False},
    "feature": {"captions": "feature", "pace": "tight", "zoom": "punch", "format": "vertical", "hook": False},
    "masthead": {"captions": "masthead", "pace": "tight", "zoom": "none", "format": "vertical", "hook": False},
}
PACES = {"tight": dict(max_pause=0.25, handle=0.08), "natural": dict(max_pause=0.6, handle=0.16)}
ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZOOM = 1.14
ZOOM_HOLD = 2.2
HOOK_SECONDS = 3.2

# ------------------------------------------------------------------ files
def edit_dir(video): return os.path.join(video, "edit")
def path(video, name): return os.path.join(edit_dir(video), name)

def read(video, name, default=None):
    try:
        with open(path(video, name)) as f: return json.load(f)
    except OSError:
        return default

def write(video, name, value):
    os.makedirs(edit_dir(video), exist_ok=True)
    with open(path(video, name), "w") as f: json.dump(value, f, indent=1)

def load_edit(video):
    saved = read(video, "edit.json", {})
    edit = {**DEFAULTS, **saved}
    edit["captions"] = {**DEFAULTS["captions"], **saved.get("captions", {})}
    return edit

def clips(video):
    folder = os.path.join(video, "clips")
    names = sorted(n for n in os.listdir(folder) if n.lower().endswith(VIDEO_EXT)) if os.path.isdir(folder) else []
    try:
        with open(os.path.join(folder, "order.json")) as f: order = json.load(f)
    except (OSError, ValueError):
        order = []
    held = references(video)
    ranked = [n for n in order if n in names] + [n for n in names if n not in order]
    return [os.path.join(folder, n) for n in ranked if n not in held]

def references(video):
    try:
        with open(os.path.join(video, "clips", "references.json")) as f: return json.load(f)
    except (OSError, ValueError):
        return []

# ------------------------------------------------------------------ ingest
def _has_audio(media):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                   "-of", "csv=p=0", media]).decode().strip()
    return bool(out)

def _display_size(media):
    w, h = probe_size(media)
    rot = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream_side_data=rotation", "-of", "csv=p=0", media]).decode().strip().strip(",")
    return (h, w) if rot and abs(int(float(rot.split(",")[0]))) % 180 == 90 else (w, h)

def _frame(size):
    w, h = size
    if h > w * 1.2: return 1080, 1920
    if w > h * 1.2: return 1920, 1080
    return 1080, 1080

def join(video):
    """Every clip scaled to one frame size and frame rate and joined into edit/source.mp4. Returns the clip table."""
    files = clips(video)
    if not files: raise SystemExit("no clips: add video files to clips/ first")
    w, h = _frame(_display_size(files[0]))
    inputs, parts, table, t = [], [], [], 0.0
    for i, f in enumerate(files):
        inputs += ["-i", f]
        d = probe_duration(f)
        parts.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},setsar=1,format=yuv420p[v{i}]")
        if _has_audio(f):
            parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
        else:
            parts.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{d}[a{i}]")
        table.append({"name": os.path.basename(f), "start": round(t, 3), "duration": round(d, 3)})
        t += d
    parts.append("".join(f"[v{i}][a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=1:a=1[v][a]")
    os.makedirs(edit_dir(video), exist_ok=True)
    out = path(video, "source.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
                    *mezzanine((w, h)), "-c:a", "aac", "-b:a", "256k", out], check=True)
    write(video, "clips.json", table)
    return table

def _norm(word): return re.sub(r"[^a-z0-9']", "", word.lower())

def sentences_of(words, table):
    """Words -> sentences: split on end punctuation and on long pauses, never longer than ~30 words."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text = w["word"].strip()
        gap = nxt["start"] - w["end"] if nxt else 9
        ends = text[-1:] in ".?!" or gap > 0.9 or (len(cur) >= 30 and text[-1:] == ",") or len(cur) >= 42
        boundary = nxt and any(w["start"] < c["start"] - 0.1 and nxt["start"] > c["start"] - 0.4 for c in table[1:])
        if ends or boundary or not nxt:
            out.append(cur); cur = []
    sentences = []
    for n, group in enumerate(out, 1):
        s, e = group[0]["start"], group[-1]["end"]
        clip = max((k for k, c in enumerate(table) if c["start"] <= s + 0.2), default=0)
        sentences.append({"id": n, "s": round(s, 3), "e": round(e, 3), "clip": clip,
                          "text": " ".join(w["word"].strip() for w in group)})
    return sentences

def _shared(a, b):
    blocks = difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()
    return sum(m.size for m in blocks if m.size >= 2), max((m.size for m in blocks), default=0)

RESTART = {"wait", "hold", "sorry", "again", "redo", "restart", "scratch", "cut", "oops", "hang"}
ASIDE = RESTART | {"on", "let", "me", "start", "that", "try", "one", "more", "time", "okay", "ok", "um", "uh", "hmm",
                   "actually", "no", "from", "the", "top", "i", "i'm", "gonna", "going", "to", "do", "it", "just", "a", "sec", "second", "so"}
DANGLING = {"and", "but", "so", "or", "because", "the", "a", "an", "to", "of", "my", "your", "with", "for", "in", "on", "at",
            "is", "was", "that", "if", "when", "like", "then", "i", "we", "you", "it's", "i'm"}

def retakes(sentences):
    """Sentence ids that look like an abandoned take of a later sentence: {id: reason}."""
    found = {}
    keyed = [[_norm(w) for w in s["text"].split() if _norm(w)] for s in sentences]
    for i, a in enumerate(keyed):
        if not a: continue
        for j in range(i + 1, min(i + 4, len(keyed))):
            b = keyed[j]
            if len(b) < 3: continue
            total, longest = _shared(a, b)
            same_start = len(a) >= 3 and a[:3] == b[:3]
            said_again = len(a) >= 4 and longest >= 3 and total / len(a) >= 0.6
            said_cleaner = len(b) >= 6 and longest >= 4 and total / len(b) >= 0.7
            if said_again or said_cleaner or (same_start and len(a) <= len(b)):
                found[sentences[i]["id"]] = f"retake of #{sentences[j]['id']}"
                break
    for n, (s, a) in enumerate(zip(sentences, keyed)):
        if s["id"] in found: continue
        text = s["text"].strip().rstrip('"”')
        last = n == len(sentences) - 1
        if a and len(a) <= 7 and all(w in ASIDE for w in a) and any(w in RESTART for w in a): found[s["id"]] = "restart aside"
        elif len(a) <= 1 and len(sentences) > 3: found[s["id"]] = "fragment"
        elif re.search(r"(\.\.\.|…|--|—|-)[?!.]*$", text): found[s["id"]] = "trails off"
        elif last and len(sentences) > 3 and text[-1:] not in ".?!" and a and a[-1] in DANGLING: found[s["id"]] = "trails off"
        elif len(a) <= 2 and text[-1:] not in ".?!": found[s["id"]] = "false start"
    return found

def restarts(words):
    """Stumbles inside a sentence ("so the first, so the first thing"): [[s, e]] covering the abandoned words."""
    keyed, trims, i = [_norm(w["word"]) for w in words], [], 0
    while i < len(words):
        hit = None
        for n in (5, 4, 3, 2):
            if i + n > len(words) or (n == 2 and len(keyed[i]) + len(keyed[i + 1]) < 6): continue
            for j in range(i + n, min(i + n + 4, len(words) - n + 1)):
                if keyed[i:i + n] == keyed[j:j + n] and all(keyed[i:i + n]):
                    hit = j; break
            if hit: break
        if hit:
            trims.append([round(words[i]["start"], 3), round(words[hit]["start"], 3)])
            i = hit
        else:
            i += 1
    return trims

def ingest(video, first=None):
    """Join and transcribe the clips. `first` is a patch applied only when this folder has no edit yet."""
    fresh = read(video, "edit.json") is None
    table = join(video)
    res = cp.transcribe(path(video, "source.mp4"), path(video, "transcript.json"))
    sentences = sentences_of(res["words"], table)
    write(video, "sentences.json", sentences)
    auto = retakes(sentences)
    write(video, "hints.json", {str(k): v for k, v in auto.items()})
    previous = read(video, "edit.json", {})
    edit = {**load_edit(video), "cut": sorted(auto), "auto": sorted(auto), "trims": restarts(res["words"]), "nudges": []}
    for k in ("format", "pace", "zoom", "hook", "captions"):
        if k in previous: edit[k] = previous[k]
    write(video, "edit.json", edit)
    if fresh and first: apply(video, first)
    return show(video)

# ------------------------------------------------------------------ show / set
def _clock(t): return f"{int(t // 60)}:{t % 60:04.1f}"

def kept_seconds(sentences, edit):
    cut = set(edit["cut"])
    total = sum(s["e"] - s["s"] for s in sentences if s["id"] not in cut)
    return total - sum(e - s for s, e in edit["trims"]
                       if any(x["id"] not in cut and x["s"] <= s and e <= x["e"] + 0.5 for x in sentences))

def show(video):
    sentences, edit = read(video, "sentences.json"), load_edit(video)
    if sentences is None: raise SystemExit("nothing ingested yet: run ingest first")
    hints, table = read(video, "hints.json", {}), read(video, "clips.json", [])
    cut = set(edit["cut"])
    lines = [f"{len(table)} clip(s), {_clock(sum(c['duration'] for c in table))} of footage, "
             f"{len(sentences)} sentences, about {_clock(kept_seconds(sentences, edit))} kept.", ""]
    clip = -1
    for s in sentences:
        if s["clip"] != clip and len(table) > 1:
            clip = s["clip"]; lines.append(f"-- clip {clip + 1}: {table[clip]['name']}")
        mark = "CUT " if s["id"] in cut else "keep"
        why = f"  [{hints[str(s['id'])]}]" if str(s["id"]) in hints else ""
        lines.append(f"#{s['id']} {mark} {_clock(s['s'])}  {s['text']}{why}")
    c = edit["captions"]
    lines += ["", f"settings: template={edit['template']}, captions={c['style']}" + (f" at {c['position']}" if c["position"] else "")
              + f", format={edit['format']}, pace={edit['pace']}, zoom={edit['zoom']}, hook={json.dumps(edit['hook'])}",
              f"emphasis={json.dumps(c['emphasis'])} fixes={json.dumps(c['fixes'])}",
              f"{len(edit['trims'])} stumble(s) trimmed inside sentences."]
    if TEMPLATES.get(edit["template"], {}).get("hook") and not edit["hook"]:
        lines.append("This template opens with a hook title: write one (7 words or fewer).")
    return "\n".join(lines)

def status(video):
    sentences, table = read(video, "sentences.json"), read(video, "clips.json", [])
    edit = load_edit(video)
    renders = versions(video)
    names = [os.path.basename(f) for f in clips(video)]
    latest = f"cut_v{renders[-1]}.mp4" if renders and os.path.exists(path(video, f"cut_v{renders[-1]}.mp4")) else None
    planned = read(video, f"plan_v{renders[-1]}.json") if renders and not latest else None
    return {"clips": names, "ingested": [c["name"] for c in table], "stale": names != [c["name"] for c in table],
            "sentences": len(sentences or []), "kept": round(kept_seconds(sentences, edit), 1) if sentences else 0,
            "footage": round(sum(c["duration"] for c in table), 1), "versions": renders, "latest": latest,
            "duration": round(probe_duration(path(video, latest)), 1) if latest else planned["duration"] if planned else 0,
            "settings": {"template": edit["template"], "captions": edit["captions"]["style"], "format": edit["format"],
                         "pace": edit["pace"], "zoom": edit["zoom"], "hook": edit["hook"]}}

def apply(video, patch):
    """Merge a patch into edit.json. `cut` and `keep` are lists of sentence ids; the rest replaces settings."""
    edit, sentences = load_edit(video), read(video, "sentences.json", [])
    ids = {s["id"] for s in sentences}
    cut = set(edit["cut"])
    if "template" in patch:
        look = TEMPLATES.get(patch["template"])
        if not look: raise SystemExit(f"template is one of {', '.join(TEMPLATES)}")
        edit.update(template=patch["template"], pace=look["pace"], zoom=look["zoom"], format=look["format"])
        edit["captions"]["style"] = look["captions"]
        if not look["hook"]: edit["hook"] = ""
    unknown = [i for i in [*patch.get("cut", []), *patch.get("keep", [])] if i not in ids]
    if unknown: raise SystemExit(f"no sentence {unknown}: ids run 1 to {len(sentences)}")
    cut |= set(patch.get("cut", [])); cut -= set(patch.get("keep", []))
    if patch.get("keep_only"): cut = ids - set(patch["keep_only"])
    edit["cut"] = sorted(cut)
    for k, allowed in (("format", ("vertical", "source")), ("pace", tuple(PACES)), ("zoom", ("punch", "none"))):
        if k in patch:
            if patch[k] not in allowed: raise SystemExit(f"{k} is one of {', '.join(allowed)}")
            edit[k] = patch[k]
    if "hook" in patch: edit["hook"] = str(patch["hook"] or "").strip()
    c = patch.get("captions") or {}
    if "style" in c:
        if c["style"] not in STYLES: raise SystemExit(f"captions.style is one of {', '.join(STYLES)}")
        edit["captions"]["style"] = c["style"]
    if "position" in c:
        if c["position"] not in (None, *POSITIONS): raise SystemExit("captions.position is top, middle, bottom or null")
        edit["captions"]["position"] = c["position"]
    if "emphasis" in c: edit["captions"]["emphasis"] = [str(p) for p in c["emphasis"]]
    if "fixes" in c: edit["captions"]["fixes"] = {**edit["captions"]["fixes"], **c["fixes"]}
    if "trims" in patch: edit["trims"] = [[float(a), float(b)] for a, b in patch["trims"]]
    for n in patch.get("nudges", []):
        if n.get("edge") not in ("start", "end"): raise SystemExit("nudge edge is start or end")
        edit["nudges"].append({"edge": n["edge"], "at": round(float(n["at"]), 3), "by": round(max(-0.4, min(0.4, float(n["by"]))), 3)})
    if patch.get("clear_nudges"): edit["nudges"] = []
    write(video, "edit.json", edit)
    return edit

# ------------------------------------------------------------------ render
def keeps_of(sentences, words, edit):
    """Kept sentences as source ranges: neighbours merged, trims carved out, each range ending in the pause after it."""
    cut, runs = set(edit["cut"]), []
    for s in sentences:
        if s["id"] in cut: continue
        if runs and runs[-1]["last"] == s["id"] - 1 and s["s"] - runs[-1]["e"] < 1.5: runs[-1].update(e=s["e"], last=s["id"])
        else: runs.append({"s": s["s"], "e": s["e"], "last": s["id"]})
    starts = sorted(w["start"] for w in words)
    keeps = []
    for r in runs:
        after = next((t for t in starts if t > r["e"] + 0.01), r["e"] + 0.4)
        a, b = max(0.0, r["s"] - 0.06), min(r["e"] + 0.18, max(r["e"] + 0.02, after - 0.03))
        for ts, te in sorted(edit["trims"]):
            if a < ts and te < b:
                keeps.append((a, ts - 0.02, 0.03)); a = te - 0.02
        keeps.append((a, b))
    return [k for k in keeps if k[1] - k[0] > 0.15]

def out_words(words, meta, fixes):
    mapped = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        t = cp.src_to_out(mid, meta)
        if t is None: continue
        half = (w["end"] - w["start"]) / 2
        text = w["word"].strip()
        core = re.sub(r"[,.?!]+$", "", text)
        if core in fixes: text = fixes[core] + text[len(core):]
        if text: mapped.append({"w": text, "s": max(0.0, t - half), "e": t + half})
    for i, w in enumerate(mapped):
        if i: w["s"] = max(w["s"], mapped[i - 1]["s"] + 0.04)
    for i, w in enumerate(mapped):
        nxt = mapped[i + 1]["s"] if i + 1 < len(mapped) else w["e"] + 0.5
        w["e"] = max(min(w["e"], nxt), w["s"] + 0.06)
    return mapped

def zoom_points(meta, total):
    """Output times where the punch-in flips: at real cuts, no more often than every ZOOM_HOLD seconds."""
    points, last = [], 0.0
    for prev, m in zip(meta, meta[1:]):
        t = m["out_start"]
        if m["src_start"] - prev["src_end"] > 0.3 and t - last >= ZOOM_HOLD and total - t > 1.0:
            points.append(t); last = t
    return points

def caption_art(span, t, style):
    if style in EDITORIAL: style = "plain"
    if style in cap.WORD_STYLES:
        active = max((i for i, w in enumerate(span["words"]) if w["s"] <= t), default=0)
        return cap.words_img(span["words"], active, style)
    if style == "subtitle": return cap.subtitle_img(span["text"])
    if style == "plain": return cap.caption_img(span["text"], "kallaway")
    return cap.caption_img(span["text"], style, pill=style == "rpn", em=span["em"])

def hook_lines(text, f, width=1080):
    limit = width - 150
    lines = wrap(text, f, limit)
    for _ in range(8):
        if len(lines) < 2 or f.getlength(lines[-1]) >= 0.5 * max(f.getlength(l) for l in lines): break
        limit -= 40
        tighter = wrap(text, f, limit)
        if len(tighter) > len(lines): break
        lines = tighter
    return lines[:3]

def hook_art(text, width):
    f = display(64, 800)
    lines = hook_lines(text, f, width)
    asc, desc = f.getmetrics()
    lh, px, py = asc + desc + 6, 34, 22
    w = int(max(f.getlength(l) for l in lines)) + 2 * px
    im = Image.new("RGBA", (w, lh * len(lines) + 2 * py), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 28, fill=(255, 255, 255, 255))
    for i, line in enumerate(lines):
        d.text(((im.width - f.getlength(line)) / 2, py + i * lh), line, font=f, fill=(12, 12, 14))
    return im

def versions(video):
    names = os.listdir(edit_dir(video)) if os.path.isdir(edit_dir(video)) else []
    return sorted({int(m.group(1) or m.group(2)) for n in names if (m := re.match(r"(?:cut_v(\d+)\.mp4|plan_v(\d+)\.json)$", n))})

def next_version(video):
    return max(versions(video), default=0) + 1

def segments_of(video, edit):
    sentences = read(video, "sentences.json")
    if sentences is None: raise SystemExit("nothing ingested yet: run ingest first")
    words = read(video, "transcript.json")["words"]
    keeps = keeps_of(sentences, words, edit)
    if not keeps: raise SystemExit("every sentence is cut: keep at least one")
    env, thresh = cp.speech_env(path(video, "source.mp4"))
    spoken = [(w["start"], w["end"]) for w in words]
    segs = cp.trim_edges(cp.plan(keeps, env, thresh=thresh, words=spoken, **PACES[edit["pace"]]), env, thresh=thresh, words=spoken)
    return nudged(segs, edit["nudges"]), words, sentences

def nudged(segs, nudges):
    """Move single cut edges: each nudge finds the edge within 0.3 s of `at` and keeps `by` more seconds of sound there."""
    segs = [list(s) for s in segs]
    for n in nudges:
        col = 1 if n["edge"] == "end" else 0
        if not segs: break
        i = min(range(len(segs)), key=lambda k: abs(segs[k][col] - n["at"]))
        if abs(segs[i][col] - n["at"]) > 0.3: continue
        if col:
            limit = segs[i + 1][0] if i + 1 < len(segs) else float("inf")
            segs[i][1] = round(max(segs[i][0] + 0.1, min(segs[i][1] + n["by"], limit)), 3)
        else:
            limit = segs[i - 1][1] if i else 0.0
            segs[i][0] = round(min(segs[i][1] - 0.1, max(segs[i][0] - n["by"], limit)), 3)
    return [tuple(s) for s in segs]

def _edge(word, at, edge, env, thresh):
    """What a cut edge does to the word it touches: None, or (problem, nudge that fixes it)."""
    mid = (word["start"] + word["end"]) / 2
    said = word["word"].strip()
    if edge == "end":
        over = word["end"] - at
        if over <= 0.03: return None
        if mid < at: return f'"{said}" loses its last {over:.2f}s', round(over + 0.05, 2)
        return f'{at - word["start"]:.2f}s of the cut word "{said}" is left in', round(-(at - word["start"]) - 0.03, 2)
    over = at - word["start"]
    if over <= 0.03: return None
    if mid > at: return f'"{said}" loses its first {over:.2f}s', round(over + 0.04, 2)
    return f'{word["end"] - at:.2f}s of the cut word "{said}" is left in', round(-(word["end"] - at) - 0.03, 2)

def check(video):
    """Listen back to the cut before rendering: each join with the words either side, edges that clip a kept word or
    leave part of a cut one (from the word timings), and what a fresh transcript of the cut audio hears."""
    edit = load_edit(video)
    segs, words, _ = segments_of(video, edit)
    src = path(video, "source.mp4")
    env, thresh = cp.speech_env(src)
    spoken = lambda ws: " ".join(w["word"].strip() for w in ws)
    lines, flags, kept, t = [], 0, [], 0.0
    for i, (a, b) in enumerate(segs):
        touching = [w for w in words if w["end"] > a and w["start"] < b]
        inside = [w for w in touching if a <= (w["start"] + w["end"]) / 2 <= b]
        kept += inside
        notes = []
        for edge, at, word in (("start", a, touching[:1]), ("end", b, touching[-1:])):
            found = word and _edge(word[0], at, edge, env, thresh)
            if found:
                flags += 1
                notes.append(f'    ! {found[0]}. Fix: {{"edge": "{edge}", "at": {at}, "by": {found[1]}}}')
        lines.append(f'{i + 1:2d}. {_clock(t)}  src {a:.2f}-{b:.2f}  "{spoken(inside[:4])} ... {spoken(inside[-4:])}"')
        lines += notes
        t += b - a
    heard = path(video, "check.m4a")
    pieces = ";".join(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}]" for i, (a, b) in enumerate(segs))
    joined = "".join(f"[a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[out]"
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", f"{pieces};{joined}", "-map", "[out]",
                        "-ac", "1", "-ar", "16000", heard], check=True)
        got = cp.transcribe(heard, path(video, "check.json"))["words"]
        want, have = [_norm(w["word"]) for w in kept], [_norm(w["word"]) for w in got]
        diffs = []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, want, have, autojunk=False).get_opcodes():
            if op == "equal": continue
            near = spoken(kept[max(0, i1 - 2):i1])
            diffs.append(f'    after "{near}": meant "{spoken(kept[i1:i2])}", heard "{spoken(got[j1:j2])}"')
        listened = ["Heard back the same words as the plan."] if not diffs else [
            "Listening back heard these differently (a missing or half word next to a join is a clipped cut; a spelling change is not):", *diffs[:20]]
    except Exception as error:
        listened = [f"Could not listen back: {error}"]
    head = f"{len(segs)} pieces, {flags} edge(s) flagged." + (" Send each Fix in change_edit nudges, then check again." if flags else "")
    return "\n".join([head, *lines, *listened])


def plan(video):
    """The cut render() would make, as data: edit/plan_vN.json for a device that renders from its own copy of the clips."""
    edit = load_edit(video)
    segs, words, sentences = segments_of(video, edit)
    meta, total = [], 0.0
    for s, e in segs:
        meta.append({"src_start": s, "src_end": e, "out_start": round(total, 4)}); total += e - s
    sw, sh = probe_size(path(video, "source.mp4"))
    w, h = (1080, 1920) if edit["format"] == "vertical" else (sw - sw % 2, sh - sh % 2)
    c = edit["captions"]
    style = c["style"]
    spoken = out_words(words, meta, c["fixes"])
    spans = [] if style == "none" else cap.chunk(cap.join_phrases(spoken, c["emphasis"]), "plain" if style in EDITORIAL else style)
    default_y = (0.78 if style == "subtitle" else 0.6) if h > w else 0.86
    n = next_version(video)
    made = {"version": n, "size": [w, h], "frame": [sw, sh], "fps": FPS, "duration": round(total, 3),
            "footage": round(probe_duration(path(video, "source.mp4")), 1), "cuts": len(segs) - 1,
            "clips": read(video, "clips.json", []), "segments": meta,
            "captions": {"style": "plain" if style in EDITORIAL else style, "y": POSITIONS[c["position"]] if c["position"] else default_y, "scale": min(w, h) / 1080,
                         "marker": list(cap.MARKER), "accent": list(cap.ACCENT),
                         "spans": [{"s": round(x["s"], 3), "e": round(x["e"], 3), "text": x["text"], "em": x["em"],
                                    "words": [{"w": k["w"], "s": round(k["s"], 3), "e": round(k["e"], 3)} for k in x["words"]]} for x in spans]},
            "hook": {"text": edit["hook"], "end": round(min(HOOK_SECONDS, total), 3), "y": 0.13},
            "zoom": {"scale": ZOOM, "cy": 0.38, "flips": [round(t, 3) for t in zoom_points(meta, total)] if edit["zoom"] == "punch" else []}}
    write(video, f"plan_v{n}.json", made)
    write(video, "cut_transcript.json", {"words": [{"word": x["w"], "start": round(x["s"], 3), "end": round(x["e"], 3)} for x in spoken]})
    with open(path(video, "cut.script.md"), "w") as f:
        cut = set(edit["cut"])
        f.write("\n".join(s["text"] for s in sentences if s["id"] not in cut) + "\n")
    return {"file": f"edit/plan_v{n}.json", "version": n, "duration": round(total, 1), "footage": made["footage"],
            "cuts": len(segs) - 1, "size": [w, h], "device": True}

def renderer():
    from . import htmlcut
    chosen = os.environ.get("CUTROOM_RENDERER", "").lower()
    if chosen == "pillow": return "pillow"
    if not htmlcut.available(): return "pillow"
    return "html" if chosen == "html" or sys.platform == "darwin" else "pillow"

def look_of(video, edit, words, meta, total, size):
    w, h = size
    c = edit["captions"]
    style = c["style"]
    spoken = out_words(words, meta, c["fixes"])
    spans = [] if style == "none" else cap.chunk(cap.join_phrases(spoken, c["emphasis"]), "plain" if style in EDITORIAL else style)
    scale = min(w, h) / 1080
    default_y = (0.78 if style == "subtitle" else 0.6) if h > w else 0.86
    y = (POSITIONS[c["position"]] if c["position"] else default_y) * h
    magazine = style in EDITORIAL and (w, h) == (1080, 1920)
    keys = set()
    if magazine:
        from . import viral as V
        keys = {V.key_of(V.clean(k)) for p in c["emphasis"] for k in p.split()}
    return {"size": (w, h), "total": total, "style": style, "spoken": spoken, "words": spoken, "spans": spans, "scale": scale,
            "y": y / scale, "stage": (w / scale, h / scale), "cy": y if c["position"] else None, "magazine": magazine, "keys": keys,
            "flips": zoom_points(meta, total) if edit["zoom"] == "punch" else [], "zoom": ZOOM,
            "hook": edit["hook"], "hook_end": min(HOOK_SECONDS, total)}

def render(video):
    edit = load_edit(video)
    segs, words, sentences = segments_of(video, edit)
    src = path(video, "source.mp4")
    base = path(video, "base.mp4")
    meta = cp.build(src, segs, base)
    total = probe_duration(base)
    sw, sh = probe_size(base)
    size = (1080, 1920) if edit["format"] == "vertical" else (sw - sw % 2, sh - sh % 2)
    look = look_of(video, edit, words, meta, total, size)
    mask = person_mask(video, base, segs) if look["magazine"] and look["style"] == "masthead" else None
    n = next_version(video)
    out = path(video, f"cut_v{n}.mp4")
    drawn = renderer()
    fallback = None
    if drawn == "html":
        from . import htmlcut
        home = path(video, "cut")
        try:
            htmlcut.write(home, look, base, mask)
            htmlcut.render(home, out)
        except Exception as error:
            print(f"the html render failed, drawing with pillow instead: {error}", file=sys.stderr)
            drawn = "pillow"
            fallback = str(error)[:300]
            if not os.path.exists(base): os.replace(os.path.join(home, "assets", "base.mp4"), base)
    if drawn == "pillow":
        draw(look, base, mask, out)
    if os.path.exists(base): os.remove(base)
    spoken = look["spoken"]
    write(video, "cut_transcript.json", {"words": [{"word": x["w"], "start": round(x["s"], 3), "end": round(x["e"], 3)} for x in spoken]})
    write(video, "storyboard.json", {"beats": [], "transcript": "cut_transcript.json"})
    with open(path(video, "cut.script.md"), "w") as f:
        cut = set(edit["cut"])
        f.write("\n".join(s["text"] for s in sentences if s["id"] not in cut) + "\n")
    return {"file": f"edit/cut_v{n}.mp4", "version": n, "duration": round(total, 1),
            "footage": round(probe_duration(src), 1), "cuts": len(segs) - 1, "size": list(size), "renderer": drawn,
            **({"fallback": fallback} if fallback else {})}

def draw(look, base, mask, out):
    w, h = look["size"]
    total, style, spans, scale, spoken = look["total"], look["style"], look["spans"], look["scale"], look["spoken"]
    y, flips, hook_end, magazine, keys = look["y"] * scale, look["flips"], look["hook_end"], look["magazine"], look["keys"]
    hook = hook_art(look["hook"], 1080) if look["hook"] else None
    lines = {"cy": look["cy"]} if look["cy"] is not None else {}
    if magazine:
        from . import viral as V

    def sized(im):
        if abs(scale - 1) < 0.02: return im
        return im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)

    @functools.lru_cache(maxsize=None)
    def hook_sized(): return sized(hook)

    def frame(i, srcs):
        t = i / FPS
        img = srcs[0].next()
        zoomed = sum(1 for p in flips if p <= t) % 2
        if zoomed: img = cover(img, w, h, z=ZOOM, cy=0.38)
        if magazine: return magazine_frame(t, img, srcs[1].next() if mask else None, zoomed)
        span = next((s for s in spans if s["s"] <= t < s["e"]), None)
        if not span and not (hook and t < hook_end): return img
        canvas = img.copy()
        if hook and t < hook_end:
            im = hook_sized()
            fade = min(1.0, t / 0.18, (hook_end - t) / 0.2)
            stamp(canvas, im, w / 2 - im.width / 2, h * 0.13, fade)
        if span:
            im = sized(caption_art(span, t, style))
            stamp(canvas, im, w / 2 - im.width / 2, y - im.height / 2)
        return canvas

    def magazine_frame(t, img, matte, zoomed):
        canvas = img.convert("RGBA")
        if matte is not None:
            if zoomed: matte = cover(matte, w, h, z=ZOOM, cy=0.38)
            V.masthead_back(canvas, t, spoken, keys, V.person(canvas, matte))
        V.CAPTIONS[style](canvas, t, spoken, keys, **lines)
        if hook and t < hook_end:
            im = hook_sized()
            stamp(canvas, im, w / 2 - im.width / 2, h * 0.13, min(1.0, t / 0.18, (hook_end - t) / 0.2))
        return canvas

    def sources(t0):
        base_reader = Reader(base, w, h, t0, fill=True)
        return (base_reader, Reader(mask, w, h, t0, fill=True)) if mask else (base_reader,)

    parallel.render(out, int(total * FPS), frame, sources, audio=base, size=(w, h))

def _masker():
    if sys.platform != "darwin":
        return [sys.executable, os.path.join(ENGINE, "personmask.py")]
    swift = os.path.join(ENGINE, "personmask.swift")
    tool = os.path.join(os.path.expanduser("~/Library/Caches/cutroom"), "personmask")
    if not os.path.exists(tool) or os.path.getmtime(tool) < os.path.getmtime(swift):
        os.makedirs(os.path.dirname(tool), exist_ok=True)
        subprocess.run(["swiftc", "-O", swift, "-o", tool], check=True)
    return [tool]

def person_mask(video, media, segs):
    """A person matte of the cut (white where the person is), kept per cut so re-renders of the same cut reuse it."""
    name = "mask_" + hashlib.sha1(json.dumps(segs).encode()).hexdigest()[:10] + ".mp4"
    out = path(video, name)
    if os.path.exists(out): return out
    for old in os.listdir(edit_dir(video)):
        if old.startswith("mask_") and old.endswith(".mp4"): os.remove(path(video, old))
    sw, sh = probe_size(media)
    mw, mh = sw // 2 - sw // 2 % 2, sh // 2 - sh // 2 % 2
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [ENGINE, os.environ.get("PYTHONPATH")]))}
    part = out + ".part.mp4"
    maker = subprocess.Popen([*_masker(), media, str(mw), str(mh)], stdout=subprocess.PIPE, env=env)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{mw}x{mh}", "-r", str(FPS), "-i", "-",
                    "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", part], stdin=maker.stdout, check=True)
    maker.stdout.close()
    if maker.wait(): raise RuntimeError("the person mask failed")
    os.replace(part, out)
    return out

def sheet(video, media=None, fps=None):
    latest = status(video)["latest"]
    media = media or path(video, latest or "source.mp4")
    if not os.path.exists(media): raise SystemExit(f"no such file: {media}")
    os.makedirs(edit_dir(video), exist_ok=True)
    total = probe_duration(media)
    cols, rows = 6, 4
    step = 1 / float(fps) if fps else max(total / (cols * rows), 0.25)
    rows = max(1, min(8, -(-int(total / step + 0.999) // cols)))
    out = path(video, f"sheet_{os.path.splitext(os.path.basename(media))[0]}.jpg")
    gap = 4
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", media, "-frames:v", "1", "-vf",
                    f"fps=1/{step:.3f},scale=-2:360,tile={cols}x{rows}:padding={gap}", "-q:v", "4", out], check=True)
    im = Image.open(out).convert("RGB")
    d = ImageDraw.Draw(im)
    cw, ch = (im.width - gap * (cols - 1)) / cols, (im.height - gap * (rows - 1)) / rows
    for i in range(cols * rows):
        t = i * step + step / 2
        if t > total: break
        x, y = (i % cols) * (cw + gap) + 6, (i // cols) * (ch + gap) + 6
        stamp = _clock(t)
        d.rectangle((x, y, x + 12 * len(stamp) + 8, y + 26), fill=(0, 0, 0))
        d.text((x + 4, y + 2), stamp, font=font(HELV, 20), fill=(255, 255, 255))
    im.save(out, quality=82)
    return {"file": out, "frames": cols * rows, "every": round(step, 2), "duration": round(total, 1)}

def adopt(video, media):
    if not os.path.exists(media): raise SystemExit(f"no such file: {media}")
    n = next_version(video)
    out = path(video, f"cut_v{n}.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", media, "-c", "copy", "-movflags", "+faststart", out], check=True)
    src = path(video, "source.mp4")
    return {"file": f"edit/cut_v{n}.mp4", "version": n, "duration": round(probe_duration(out), 1),
            "footage": round(probe_duration(src), 1) if os.path.exists(src) else 0, "cuts": 0}

def shots(media):
    """Seconds where the picture jumps: a cut, a punch-in or a full-screen graphic."""
    log = subprocess.run(["ffmpeg", "-v", "info", "-i", media, "-an", "-vf", "scale=320:-2,select='gt(scene,0.08)',showinfo",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    found = []
    for t in (round(float(t), 2) for t in re.findall(r"pts_time:([0-9.]+)", log)):
        if not found or t - found[-1] >= 0.3: found.append(t)
    return found

def reference(video, name):
    name = os.path.basename(name)
    media = os.path.join(video, "clips", name)
    if not os.path.exists(media): raise SystemExit(f"no such clip: {name}")
    held = references(video)
    if name not in held:
        with open(os.path.join(video, "clips", "references.json"), "w") as f: json.dump(held + [name], f)
    total = probe_duration(media)
    w, h = _display_size(media)
    cuts = shots(media)
    lengths = [round(b - a, 2) for a, b in zip([0.0] + cuts, cuts + [total])]
    return {"reference": name, "sheet": sheet(video, media, min(4.0, max(0.5, 48 / max(total, 1))))["file"],
            "duration": round(total, 1), "shape": "vertical" if h > w else "square" if h == w else "wide", "size": [w, h],
            "shots": len(lengths), "average_shot": round(total / len(lengths), 2), "shortest_shot": min(lengths),
            "longest_shot": max(lengths), "cuts_at": cuts[:80], "footage": [os.path.basename(f) for f in clips(video)]}

# ------------------------------------------------------------------ cli
def main(argv):
    if len(argv) < 2: print(__doc__); return 1
    cmd, video = argv[0], argv[1]
    if cmd == "ingest": print(ingest(video, json.loads(argv[2]) if len(argv) > 2 and argv[2] else None))
    elif cmd == "status": print(json.dumps(status(video)))
    elif cmd == "show": print(show(video))
    elif cmd == "set":
        apply(video, json.loads(argv[2])); print(show(video))
    elif cmd == "render": print(json.dumps(render(video)))
    elif cmd == "plan": print(json.dumps(plan(video)))
    elif cmd == "check": print(check(video))
    elif cmd == "sheet": print(json.dumps(sheet(video, *[a for a in argv[2:4] if a])))
    elif cmd == "adopt": print(json.dumps(adopt(video, argv[2])))
    elif cmd == "reference": print(json.dumps(reference(video, argv[2])))
    else: print(__doc__); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
