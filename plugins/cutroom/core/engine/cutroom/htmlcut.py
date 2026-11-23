"""Autocut drawn as an HTML page (edit/cut/) and rendered by the Hyperframes that `cutroom compose` pins.

The page holds the cut footage, the punch-in as a scale on it, the captions and the hook card, laid out with the
same fonts, sizes and timings as the Pillow renderer in autocut.py, so either one makes the same video.
"""
import html, json, os, re, shutil, subprocess, sys

from . import brand, captions as cap, core
from .core import FPS

CORE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(CORE, "bin", "cutroom.mjs")
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"
RUN = """(() => {
  const tl = gsap.timeline({ paused: true });
  for (const op of OPS) {
    if (op.length === 3) tl.set(op[0], op[2], op[1]);
    else tl.fromTo(op[0], op[2], { ...op[3], duration: op[4], ease: op[5] }, op[1]);
  }
  __EXTRA__
  window.__timelines["__ID__"] = tl;
})();"""


def pinned():
    with open(CLI) as f:
        return re.search(r'"(hyperframes@[0-9][0-9.]*)"', f.read()).group(1)


def runtime():
    return f"https://cdn.jsdelivr.net/npm/@hyperframes/core@{pinned().split('@')[1]}/dist/hyperframe.runtime.iife.js"


def available():
    return bool(shutil.which("npx")) and os.path.exists(CLI)


def rgb(c, a=1.0):
    return f"rgba({c[0]},{c[1]},{c[2]},{round(a, 3)})"


def shadow(alpha, blur=10, dy=3):
    return f"text-shadow:0 {dy}px {2 * blur}px {rgb((0, 0, 0), alpha / 255)};" if alpha else ""


def num(x):
    return round(float(x), 3)


class Fonts:

    def __init__(self, home):
        self.home, self.faces, self.rules = home, {}, []

    def resolve(self, path, var, index):
        if os.path.exists(path): return path, var, index
        alt = os.path.expanduser("~/Library/Fonts/" + os.path.basename(path))
        if os.path.exists(alt): return alt, var, index
        src, var = core._fallback(path, index)
        return src, var, 0

    def family(self, src, index):
        key = (src, index)
        if key in self.faces: return self.faces[key]
        name = f"cutroom-font-{len(self.faces)}"
        if src.lower().endswith((".ttc", ".otc")):
            fam, style = core.font(src, 40, index=index).getname()
            post = (fam + "-" + style).replace(" ", "")
            where = f'local("{fam} {style}"), local("{post}")'
        else:
            os.makedirs(os.path.join(self.home, "assets", "fonts"), exist_ok=True)
            file = name + os.path.splitext(src)[1].lower()
            shutil.copyfile(src, os.path.join(self.home, "assets", "fonts", file))
            where = f'url("assets/fonts/{file}")'
        self.rules.append(f"@font-face{{font-family:\"{name}\";src:{where};font-weight:1 1000;font-style:normal;}}")
        self.faces[key] = name
        return name

    def settings(self, src, var):
        axes = core._axes(src)
        if src in brand.fonts() and (var is None or src != core.TIKTOK):
            return ",".join(f"'{t.decode()}' {min(hi, 800) if t == b'wght' else d:g}" for t, d, hi in axes)
        if var is None or not axes: return "normal"
        return ",".join(f"'{t.decode()}' {v:g}" for (t, _, _), v in zip(axes, var))

    def face(self, path, size, var=None, index=0):
        f = core.font(path, size, var, index)
        src, var, index = self.resolve(path, var, index)
        asc, desc = f.getmetrics()
        css = (f"font-family:'{self.family(src, index)}';font-size:{size}px;font-weight:400;"
               f"font-variation-settings:{self.settings(src, var)};line-height:{asc + desc}px;")
        return css, f

    def display(self, size, weight):
        return self.face(core.DISPLAY, size, [36, 100, weight, 0])

    def css(self):
        return "\n".join(self.rules)


def width(f, text, tracking=0.0):
    if not tracking: return f.getlength(text)
    return sum(f.getlength(c) for c in text) + tracking * f.size * (len(text) - 1)


class Layer:

    def __init__(self, name, size, scale):
        self.name, self.size, self.scale = name, size, scale
        self.nodes, self.ops, self.style, self.extra, self.data = [], [], [], "", {}

    def id(self, *parts): return "-".join([self.name, *map(str, parts)])
    def set(self, el, t, props): self.ops.append([f"#{el}", num(max(0.0, t)), props])
    def show(self, el, t0, t1):
        self.set(el, t0, {"opacity": 1})
        self.set(el, t1, {"opacity": 0})

    def tween(self, el, t, start, end, d, ease):
        self.ops.append([f"#{el}", num(max(0.0, t)), start, end, num(d), ease])

    def file(self):
        w, h = self.size
        stage = (w / self.scale, h / self.scale)
        script = RUN.replace("__ID__", self.name).replace("__EXTRA__", self.extra)
        consts = "".join(f"const {k} = {json.dumps(v, separators=(',', ':'))};\n    " for k, v in {"OPS": self.ops, **self.data}.items())
        return f"""<template>
  <style>
    #{self.name}-root {{ position: absolute; inset: 0; overflow: hidden; }}
    #{self.name}-stage {{ position: absolute; left: 0; top: 0; width: {stage[0]:g}px; height: {stage[1]:g}px; transform: scale({self.scale:g}); transform-origin: 0 0; }}
    #{self.name}-stage > * {{ position: absolute; opacity: 0; white-space: pre; color: #fff; }}
    {"    ".join(self.style)}
  </style>
  <div id="{self.name}-root" data-composition-id="{self.name}" data-width="{w}" data-height="{h}">
    <div id="{self.name}-stage">
      {chr(10).join("      " + n for n in self.nodes).strip()}
    </div>
  </div>
  <script>
    {consts}{script}
  </script>
</template>
"""


def phrase_looks(layer, fonts, look):
    style, cx, y = look["style"], look["stage"][0] / 2, look["y"]
    plain = fonts.face(core.HELV, 68, index=1 if core.HELV.endswith("HelveticaNeue.ttc") else 0)[0]
    serif = fonts.face(cap.SERIF_IT, 74, [28, 520, 0])[0]
    mono = fonts.face(core.MONO, 44)[0]
    sub = fonts.display(54, 600)[0]
    for i, span in enumerate(look["spans"]):
        text = span["text"].replace("’", "'")
        if style == "subtitle":
            css = sub + "letter-spacing:-0.01em;" + shadow(230)
        elif style == "rpn":
            text = text.upper()
            css = mono + "letter-spacing:0.04em;padding:14px 22px 10px;border-radius:14px;background:" + rgb(core.PILL, 225 / 255) + ";"
        else:
            text = text.rstrip(",")
            css = (serif if style == "kallaway" and span["em"] else plain + "letter-spacing:-0.045em;") + shadow(200)
        el = layer.id("span", i)
        layer.nodes.append(f'<div id="{el}" style="left:{cx:g}px;top:{y:g}px;transform:translate(-50%,-50%);{css}">{html.escape(text)}</div>')
        layer.show(el, span["s"], span["e"])


def word_looks(layer, fonts, look):
    pop = look["style"] == "pop"
    css, f = fonts.display(84 if pop else 70, 900 if pop else 800)
    gap = int(f.size * 0.26) + (0 if pop else 4)
    cx, y = look["stage"][0] / 2, look["y"]
    n = layer.name
    if pop:
        word = (f"{css}color:#fff;-webkit-text-stroke:14px #000;paint-order:stroke fill;" + shadow(150, 8, 6))
        on = f"color:{rgb(cap.MARKER)};"
    else:
        word = f"{css}color:#fff;letter-spacing:-0.02em;border-radius:16px;" + shadow(170)
        on = f"background:{rgb(cap.ACCENT)};padding:9px 18px 3px;text-shadow:none;"
    layer.style += [f".{n}-line {{ display: flex; align-items: center; gap: {gap}px; transform: translate(-50%,-50%); }}\n",
                    f".{n}-word {{ {word} }}\n", f".{n}-word[data-on=\"1\"] {{ {on} }}\n"]
    for i, span in enumerate(look["spans"]):
        el, parts = layer.id("span", i), []
        words = span["words"]
        for k, w in enumerate(words):
            text = w["w"].replace("’", "'").rstrip(",.")
            wid = layer.id("span", i, k)
            parts.append(f'<span id="{wid}" class="{n}-word">{html.escape(text.upper() if pop else text)}</span>')
            start = span["s"] if k == 0 else w["s"]
            end = words[k + 1]["s"] if k + 1 < len(words) else span["e"]
            layer.set(wid, start, {"attr": {"data-on": "1"}})
            if k + 1 < len(words): layer.set(wid, end, {"attr": {"data-on": "0"}})
        layer.nodes.append(f'<div id="{el}" class="{n}-line" style="left:{cx:g}px;top:{y:g}px;">{"".join(parts)}</div>')
        layer.show(el, span["s"], span["e"])


def token(fonts, text, kind, size, color=(255, 255, 255)):
    from . import viral as V
    if kind == "serif":
        css, f = fonts.face(V.INSTRUMENT, size)
        tracking = 0.0
    else:
        css, f = fonts.display(size, {"caps": 600, "line": 700}[kind])
        tracking = 0.16 if kind == "caps" else -0.01
        text = text.upper() if kind == "caps" else text
    css += f"letter-spacing:{tracking}em;color:{rgb(color)};" + shadow(120, 12, 4)
    return {"css": css, "text": text, "width": width(f, text, tracking), "asc": f.getmetrics()[0]}


def flow(toks, sizes, *, maxw, gap, align="center", x0=0.0, lead=0.78):
    lines, cur, wd = [], [], 0.0
    for i, t in enumerate(toks):
        if cur and wd + gap + t["width"] > maxw:
            lines.append((cur, wd))
            cur, wd = [], 0.0
        wd += (gap if cur else 0) + t["width"]
        cur.append(i)
    if cur: lines.append((cur, wd))
    pos, y = [None] * len(toks), 0.0
    heights = [max(sizes[i] for i in ln) * lead for ln, _ in lines]
    for (ln, wd), lh in zip(lines, heights):
        y += lh
        x = x0 if align == "left" else -wd / 2
        for i in ln:
            pos[i] = (x - 2, y)
            x += toks[i]["width"] + gap
    total = sum(heights)
    return [(x, by - total / 2 - total * 0.12) for x, by in pos]


def place_tokens(layer, group, toks, pos, cx, cy):
    ids = []
    for k, (t, (x, by)) in enumerate(zip(toks, pos)):
        el = layer.id(group, k)
        ids.append(el)
        layer.nodes.append(f'<div id="{el}" style="left:{cx + x:.1f}px;top:{cy + by - t["asc"]:.1f}px;{t["css"]}">{html.escape(t["text"])}</div>')
    return ids


def editorial(layer, fonts, look):
    from . import viral as V
    style, words, keys, cx = look["style"], look["words"], look["keys"], look["stage"][0] / 2
    cy = look["cy"] or {"spread": 1360, "feature": 1420, "masthead": 1500}[style]
    if style == "masthead":
        n = 0
        for g, l0, l1 in V._lines(words):
            m = V._main(g, keys)
            for part, p0, p1 in V.groups([w for i, w in enumerate(g) if i != m], 4):
                a, b = max(l0, p0), min(l1, p1)
                if b <= a or all(V._small(w["w"]) for w in part): continue
                toks = [token(fonts, V.clean(w["w"]), "caps", 50) for w in part]
                ids = place_tokens(layer, f"g{n}", toks, flow(toks, [58] * len(toks), maxw=940, gap=18), cx, cy)
                for el, w in zip(ids, part):
                    layer.tween(el, w["s"] - 0.03, {"opacity": 0}, {"opacity": 1}, 0.18, "power2.out")
                    layer.set(el, b, {"opacity": 0})
                n += 1
        return
    for n, (g, t0, t1) in enumerate(V.groups(words, 5)):
        if style == "spread":
            big = [V.key_of(V.clean(w["w"])) in keys or not V._small(V.clean(w["w"])) for w in g]
            toks = [token(fonts, V.clean(w["w"]), "serif" if b else "caps", 168 if b else 46) for w, b in zip(g, big)]
            pos = flow(toks, [168 if b else 60 for b in big], maxw=820, gap=34, lead=0.84)
        else:
            m = V._main(g, keys)
            toks = [token(fonts, V.clean(w["w"]), "serif", 150, V.FEATURE_RED) if i == m else token(fonts, V.clean(w["w"]), "line", 62)
                    for i, w in enumerate(g)]
            pos = flow(toks, [150 if i == m else 68 for i in range(len(g))], maxw=900, gap=24, align="left", x0=90 - cx)
        ids = place_tokens(layer, f"g{n}", toks, pos, cx, cy)
        for el, w in zip(ids, g):
            if style == "spread":
                layer.tween(el, w["s"] - 0.03, {"opacity": 0}, {"opacity": 1}, 0.2, "power2.out")
                layer.tween(el, w["s"] - 0.03, {"filter": "blur(16px)"}, {"filter": "blur(0px)"}, 0.2, "none")
            else:
                layer.tween(el, w["s"] - 0.03, {"opacity": 0, "y": 26}, {"opacity": 1, "y": 0}, 0.22, "power2.out")
            layer.set(el, t1, {"opacity": 0})


def behind(layer, fonts, look, tops):
    from . import viral as V
    lines, cx = [], look["stage"][0] / 2
    for n, (g, t0, t1) in enumerate(V._lines(look["words"])):
        txt = V.clean(g[V._main(g, look["keys"])]["w"]).lower()
        size = 330
        while core.font(V.INSTRUMENT, size).getlength(txt) > 1000 and size > 120: size -= 10
        css = fonts.face(V.INSTRUMENT, size)[0] + shadow(90, 18, 6)
        el = layer.id("word", n)
        layer.nodes.append(f'<div id="{el}" style="left:{cx:g}px;top:560px;transform:translate(-50%,-50%);">'
                           f'<div id="{el}-in" style="{css}">{html.escape(txt)}</div></div>')
        layer.show(el, t0, t1)
        layer.tween(el + "-in", t0, {"opacity": 0, "scale": 1.06}, {"opacity": 1, "scale": 1}, 0.3, "power2.out")
        layer.tween(el + "-in", t0, {"filter": "blur(14px)"}, {"filter": "blur(0px)"}, 0.3, "none")
        lines.append([el, num(t0), num(t1), V._masthead_word(txt).height])
    layer.data = {"LINES": lines, "TOPS": tops, "FPS": FPS, "H": look["size"][1]}
    layer.extra = """const place = (t) => {
    const top = TOPS[Math.max(0, Math.min(TOPS.length - 1, Math.round(t * FPS)))];
    for (const [el, t0, t1, h] of LINES) {
      if (t < t0 || t >= t1) continue;
      const cy = top < 0 ? 560 : Math.min(Math.max(top - h * 0.08, h * 0.5), H * 0.45);
      document.getElementById(el).style.top = cy + "px";
    }
  };
  const clock = { t: 0 };
  tl.fromTo(clock, { t: 0 }, { t: DURATION, duration: DURATION, ease: "none", onUpdate: () => place(clock.t) }, 0);
  place(0);"""
    layer.data["DURATION"] = look["total"]


def hook_layer(layer, fonts, look):
    from .autocut import hook_lines
    css, f = fonts.display(64, 800)
    asc, desc = f.getmetrics()
    lines = hook_lines(look["hook"], f)
    rows = "".join(f'<div style="height:{asc + desc + 6}px">{html.escape(l)}</div>' for l in lines)
    el = layer.id("card")
    end = look["hook_end"]
    layer.nodes.append(f'<div id="{el}" style="left:{look["stage"][0] / 2:g}px;top:{look["size"][1] * 0.13 / look["scale"]:.1f}px;'
                       f'transform:translateX(-50%);{css}line-height:{asc + desc}px;color:rgb(12,12,14);text-align:center;'
                       f'background:#fff;border-radius:28px;padding:22px 34px;">{rows}</div>')
    layer.tween(el, 0, {"opacity": 0}, {"opacity": 1}, min(0.18, end / 2), "none")
    layer.tween(el, max(0.0, end - 0.2), {"opacity": 1}, {"opacity": 0}, min(0.2, end / 2), "none")


def head_tops(matte, look):
    import numpy as np
    w, h = look["size"]
    mw, mh = core.probe_size(matte)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", matte, "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    tops, flips, i = [], look["flips"], 0
    y0 = (h - h / look["zoom"]) * 0.38
    while True:
        buf = p.stdout.read(mw * mh)
        if len(buf) < mw * mh: break
        rows = np.flatnonzero((np.frombuffer(buf, np.uint8).reshape(mh, mw) > 128).any(axis=1))
        top = rows[0] * h / mh if len(rows) else -1
        if top >= 0 and sum(1 for f in flips if f <= i / FPS) % 2:
            top = max(0.0, (top - y0) * look["zoom"])
        tops.append(round(float(top), 1))
        i += 1
    p.wait()
    return tops


def person_clip(base, matte, out, size):
    w, h = size
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", base, "-i", matte, "-filter_complex",
                    f"[1:v]scale={w}:{h},format=gray[m];[0:v]format=yuva420p[f];[f][m]alphamerge[v]", "-map", "[v]", "-an",
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                    "-crf", "20", "-b:v", "0", out], check=True)


def page(look, layers, fonts):
    w, h = look["size"]
    total = num(look["total"])
    z = look["zoom"]
    sound = {"footage": 'data-has-audio="true"'}
    footage = lambda name, src, track: (
        f'<div id="{name}-zoom" class="zoom" style="z-index:{track}"><video id="{name}" class="clip" src="{src}" {sound.get(name, "muted")} playsinline '
        f'data-start="0" data-duration="{total}" data-media-start="0" data-track-index="{track}"></video></div>')
    parts = [footage("footage", "assets/base.mp4", 1)]
    zooms = ["#footage-zoom"]
    for name, kind, end, track in layers:
        if name == "person":
            parts.append(footage("person", "assets/person.webm", track))
            zooms.append("#person-zoom")
            continue
        parts.append(f'<div id="{name}" class="scene" style="z-index:{track}" data-composition-id="{name}" '
                     f'data-composition-src="compositions/{name}.html" data-start="0" data-duration="{num(end)}" '
                     f'data-track-index="{track}" data-track-kind="{kind}" data-width="{w}" data-height="{h}"></div>')
    flips = []
    for k, t in enumerate(look["flips"]):
        flips.append([num(t), z if k % 2 == 0 else 1])
    body = "\n      ".join(parts)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <script src="{GSAP}"></script>
    <script src="{runtime()}"></script>
    <style>
      {fonts.css()}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {w}px; height: {h}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; }}
      .zoom {{ position: absolute; inset: 0; overflow: hidden; transform-origin: 50% 38%; }}
      .zoom video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      .scene {{ position: absolute; inset: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{w}" data-height="{h}" data-fps="{FPS}">
      {body}
    </div>
    <script>
      (() => {{
        const tl = gsap.timeline({{ paused: true }});
        const flips = {json.dumps(flips)};
        for (const [t, scale] of flips) tl.set({json.dumps(", ".join(zooms))}, {{ scale }}, t);
        tl.set("#root", {{}}, {total});
        window.__timelines["main"] = tl;
      }})();
    </script>
  </body>
</html>
"""


def write(home, look, base, matte=None):
    if os.path.isdir(home): shutil.rmtree(home)
    os.makedirs(os.path.join(home, "compositions"))
    os.makedirs(os.path.join(home, "assets"))
    fonts = Fonts(home)
    os.replace(base, os.path.join(home, "assets", "base.mp4"))
    layers, files = [], {}
    style, size, scale = look["style"], look["size"], look["scale"]
    if look["magazine"]:
        if matte:
            back = Layer("behind", size, 1.0)
            behind(back, fonts, look, head_tops(matte, look))
            files["behind"] = back
            layers.append(("behind", "graphics", look["total"], 2))
            person_clip(os.path.join(home, "assets", "base.mp4"), matte, os.path.join(home, "assets", "person.webm"), size)
            layers.append(("person", "video", look["total"], 3))
        front = Layer("captions", size, 1.0)
        editorial(front, fonts, look)
        files["captions"] = front
    elif look["spans"]:
        front = Layer("captions", size, scale)
        (word_looks if style in cap.WORD_STYLES else phrase_looks)(front, fonts, look)
        files["captions"] = front
    if "captions" in files: layers.append(("captions", "captions", look["total"], 4))
    if look["hook"]:
        card = Layer("hook", size, scale)
        hook_layer(card, fonts, look)
        files["hook"] = card
        layers.append(("hook", "graphics", look["hook_end"], 5))
    for name, layer in files.items():
        with open(os.path.join(home, "compositions", f"{name}.html"), "w") as f: f.write(layer.file())
    with open(os.path.join(home, "index.html"), "w") as f: f.write(page(look, layers, fonts))
    with open(os.path.join(home, "hyperframes.json"), "w") as f:
        json.dump({"paths": {"blocks": "compositions", "assets": "assets"}, "media": {"autoProxy": True}}, f, indent=2)
    return layers


def reason(lines):
    lines = [x for x in lines if x and not x.startswith("npm notice")]
    failed = next((i for i, x in enumerate(lines) if x.startswith("✗")), None)
    if failed is None: return lines[-1] if lines else ""
    return " ".join(" ".join(lines[failed:failed + 2]).lstrip("✗ ").split())[:300]


def render(home, out):
    home = os.path.abspath(home)
    silent = os.path.join(home, "render.mp4")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "NPM_CONFIG_UPDATE_NOTIFIER": "false"}
    p = subprocess.Popen(["npx", "--yes", pinned(), "render", "-o", silent, "--quiet"], cwd=home, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
    said = []
    for line in p.stdout:
        sys.stderr.write(line)
        said = [*said[-40:], line.strip()]
    if p.wait():
        raise RuntimeError(reason(said) or f"hyperframes exited with {p.returncode}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", os.path.join(home, "assets", "base.mp4"), "-map", "0:v",
                    "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                   check=True)
    os.remove(silent)
