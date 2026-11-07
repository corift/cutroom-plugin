"""UGC ad edit: prep A-roll clips, find fillers and exact cut points, layer punch-ins and
B-roll onto a basic-video-edit base cut, review the timing, and finish with an end card.

  prep      CLIP... -o raw.mp4 [--speed 1.05]   normalise clips to 1080x1920@30, speed up, concat
  fillers   VIDEO                                list uh/um and doubled words Groq dropped
  envelope  VIDEO START DUR                      loudness every 30ms, to find the dip between syllables
  gaps      VIDEO [--from S --to E]              every pause with its length, flags TIGHT and DRAG joins
  breath    VIDEO AT DUR -o out.mp4              insert a held-frame pause filled with room tone at AT, shift the transcript
  audiocheck VIDEO [--transcript T]              dead silence, clicks, and stray sounds; run before every delivery
  declick   VIDEO T... -o out.mp4                smooth the clicks audiocheck found, keeping the length
  sway      VIDEO                                subtle handheld drift -> <stem>-sway.mp4 (+ transcript)
  assemble  spec.json                            punch-ins + B-roll + overlays -> <stem>-layered.mp4 + <stem>-cap_transcript.json
  sfx       VIDEO spec.json OUT                  synthesised pops/ticks/taps/dings from spec "sfx", mixed under the voice
  review    VIDEO [--from S --to E]              shot-change scan + 6fps contact sheet, flags shots < 0.6s
  endcard   IMAGE out.mp4 [--dur 1.8]            silent end-card clip
  finish    captioned.mp4 endcard.mp4 out.mp4    concat, web-ready, warns if over 30MB
"""
import argparse, json, math, os, re, struct, subprocess, sys

W, H, FPS = 1080, 1920, 30
WHISPER_MODEL = os.path.expanduser("~/Library/Application Support/superwhisper/ggml-small.en.bin")
FILLER_PROMPT = "Um, so, uh, I like, uh, used it. Hmm, uh, yeah."
ENC = ["-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p"]
AUD = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
CAP_HOLD = 0.35  # basic-video-edit keeps a caption up this long after its last word
norm = lambda w: re.sub(r"\W", "", w).lower()
NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand"}


def word_time(words, word, after=0.0):
    for w in words:
        if w["start"] >= after and norm(w["word"]) == word.lower():
            return w["start"]
    sys.exit(f"{word!r} not found after {after}s. Check the base transcript's spelling.")


def when(words, item):
    """A timeline time from {"at": s} or {"word": w, "after": s, "lead": s}."""
    if "at" in item:
        return item["at"]
    return word_time(words, item["word"], item.get("after", 0)) - item.get("lead", 0.1)


def run(cmd, **kw):
    kw.setdefault("text", True)
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        err = r.stderr if kw["text"] else r.stderr.decode(errors="replace")
        sys.exit(err[-3000:])
    return r


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def prep(a):
    work = os.path.splitext(a.out)[0] + "_clips"
    os.makedirs(work, exist_ok=True)
    parts = []
    for clip in a.clips:
        out = os.path.join(work, os.path.basename(clip))
        # AI clips (Omni) carry ~15ms more audio than video. Trim both to the
        # video length, or the extra adds up across joins and lips drift.
        vdur = float(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=duration", "-of", "csv=p=0", clip]).stdout)
        run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-t", f"{vdur / a.speed:.4f}", "-vf",
             f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS/{a.speed},fps={FPS},setsar=1",
             "-af", f"atempo={a.speed},aresample=48000", *ENC, *AUD, out])
        parts.append(out)
    # Join with the concat filter, padding or trimming each part's audio to its
    # exact video length. The concat demuxer adds AAC padding at every join.
    vdurs = [float(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=duration", "-of", "csv=p=0", p]).stdout) for p in parts]
    fc = "".join(f"[{i}:v]setpts=PTS-STARTPTS[v{i}];[{i}:a]apad,atrim=0:{d:.4f},asetpts=PTS-STARTPTS[a{i}];"
                 for i, d in enumerate(vdurs))
    fc += "".join(f"[v{i}][a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    run(["ffmpeg", "-v", "error", "-y", *sum([["-i", p] for p in parts], []), "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", *ENC, *AUD, a.out])
    t = 0.0
    for p, d in zip(parts, vdurs):
        print(f"  {os.path.basename(p):24s} {t:6.2f} → {t + d:6.2f}")
        t += d
    print(f"{a.out}: {t:.2f}s")


def local_words(video, prompt=FILLER_PROMPT):
    """Word-level local Whisper pass. It keeps fillers and stray sounds that Groq drops."""
    wav = os.path.splitext(video)[0] + "_local.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ar", "16000", "-ac", "1", wav])
    out = run(["whisper-cli", "-m", WHISPER_MODEL, "-f", wav, "-ml", "1", "-sow", "--prompt", prompt]).stdout
    os.remove(wav)
    words = []
    for line in out.splitlines():
        m = re.match(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)", line)
        if m and m.group(7).strip():
            s = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            e = int(m.group(4)) * 3600 + int(m.group(5)) * 60 + float(m.group(6))
            words.append((s, e, m.group(7).strip()))
    return words


def fillers(a):
    words = local_words(a.video)
    found = 0
    for i, (s, e, w) in enumerate(words):
        if norm(w) in {"uh", "um", "hmm", "er", "ah", "mm"}:
            print(f"  FILLER  {w!r:10s} {s:6.2f}–{e:6.2f}"); found += 1
        if i and norm(w) and norm(w) == norm(words[i - 1][2]):
            print(f"  DOUBLE  {w!r:10s} {words[i - 1][0]:6.2f}–{e:6.2f}"); found += 1
        # Two-word repeats like "so weird, so weird".
        if i >= 3 and [norm(x[2]) for x in words[i - 1:i + 1]] == [norm(x[2]) for x in words[i - 3:i - 1]]:
            print(f"  DOUBLE  {words[i - 1][2] + ' ' + w!r:10s} {words[i - 3][0]:6.2f}–{e:6.2f}"); found += 1
    print(f"{found} to check. Timings are approximate: confirm each cut with `envelope`.")


def envelope(a):
    s = pcm(a.video, a.start, a.dur)
    win = 480
    for i in range(0, len(s) - win, win):
        rms = math.sqrt(sum(x * x for x in s[i:i + win]) / win)
        db = int(20 * math.log10(rms + 1))
        print(f"{a.start + i / 16000:7.2f} {db:3d} {'#' * max(0, db - 40)}")


def gaps(a):
    """Joins should sit at ~0.25s of air (0.15 after a word + 0.10 before the next)."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.video, "-af", f"silencedetect=noise={a.db}dB:d=0.04",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    t0, t1 = a.start or 0.0, a.end or duration(a.video)
    for x, y in zip(st, en):
        if t0 <= x <= t1:
            d = y - x
            flag = "TIGHT" if d < 0.18 else "DRAG " if d > 0.45 else "     "
            print(f"  {flag} {x:6.2f} → {y:6.2f}  ({d:.2f}s)")
    print("TIGHT at a join sounds clipped, DRAG sounds like dead air. Inside a sentence, TIGHT is normal.")


def pcm(video, start, dur, rate=16000, af="anull"):
    raw = run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", video,
               "-ac", "1", "-ar", str(rate), "-af", af, "-f", "s16le", "-"], text=False).stdout
    return struct.unpack(f"{len(raw) // 2}h", raw)


def room_tone(video, before, length):
    """Start of the quietest stretch of real room sound (not digital zero) in the 3s before `before`."""
    t0 = max(0.0, before - 3.0)
    s, win, hop = pcm(video, t0, before - t0), int(length * 16000), 160
    best = None
    for i in range(0, max(1, len(s) - win), hop):
        rms = math.sqrt(sum(x * x for x in s[i:i + win:4]) / max(1, len(s[i:i + win:4])))
        if rms > 3 and (best is None or rms < best[0]):  # rms <= 3 is digital silence
            best = (rms, t0 + i / 16000)
    return best[1] if best else None


def breath(a):
    # Snap to whole frames: video can only split and pad by frames, so an
    # unsnapped time leaves the audio up to a frame out of sync after the pause.
    t, p = round(a.at * FPS) / FPS, max(1, round(a.dur * FPS)) / FPS
    # Fill the pause with her own room sound, faded in and out. A pause of digital
    # silence makes the room drop out and back, which sounds like a thud or click.
    q = room_tone(a.video, t, p + 0.06)
    tone = (f"[1:a]atrim={q}:{q + p + 0.06},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
            f"afade=t=out:st={p + 0.03}:d=0.03,adelay={int((t - 0.03) * 1000)}:all=1[tn];") if q is not None else ""
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-i", a.video, "-filter_complex",
         f"[0:v]trim=0:{t},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={p}[v1];"
         f"[0:v]trim=start={t},setpts=PTS-STARTPTS[v2];"
         f"[0:a]atrim=0:{t},asetpts=PTS-STARTPTS,afade=t=out:st={t - 0.03}:d=0.03,apad=pad_dur={p}[a0];" + tone +
         (f"[a0][tn]amix=inputs=2:normalize=0:duration=first[a1];" if tone else "[a0]anull[a1];") +
         f"[0:a]atrim=start={t},asetpts=PTS-STARTPTS,afade=t=in:d=0.02[a2];"
         "[v1][a1][v2][a2]concat=n=2:v=1:a=1[v][a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "medium", *AUD, a.out])
    if q is None:
        print("  no room tone found before the pause: it is digital silence, so check it by ear")
    src = os.path.splitext(a.video)[0] + "_transcript.json"
    if os.path.exists(src):
        tr = json.load(open(src))
        for w in tr["words"]:
            if w["start"] >= t:
                w["start"] += p; w["end"] += p
        json.dump(tr, open(os.path.splitext(a.out)[0] + "_transcript.json", "w"))
    print(f"{a.out}: {duration(a.out):.2f}s, {p}s pause at {t}s")


def audiocheck(a):
    """Pre-delivery audio gate: dead silence, clicks, and stray sounds the main transcript missed."""
    bad = 0
    log = run(["ffmpeg", "-hide_banner", "-i", a.video, "-af", "silencedetect=noise=-75dB:d=0.03",
               "-f", "null", "-"]).stderr
    end = duration(a.video) - 0.1
    for x, y in zip(re.findall(r"silence_start: ([\d.]+)", log), re.findall(r"silence_end: ([\d.]+)", log)):
        if float(x) >= end:
            continue  # the file's own last frame
        print(f"  DEAD   {float(x):6.2f} → {float(y):6.2f}  digital silence: the room drops out"); bad += 1
    # Clicks: a jump between two samples far bigger than speech makes nearby. A click
    # from a hard cut or a glitch scores about 50; speech, "p" and "t" stay under about 22.
    s = pcm(a.video, 0, duration(a.video), 48000)
    f = 240
    jump = [max(abs(s[k] - s[k - 1]) for k in range(i + 1, i + f)) for i in range(0, len(s) - f, f)]
    for i in range(8, len(jump) - 8):
        near = sorted(jump[i - 8:i] + jump[i + 2:i + 10])[8]
        if jump[i] / (near + 50) > 30:
            print(f"  CLICK  {i * f / 48000 + 0.0025:6.2f}  fix with: declick VIDEO {i * f / 48000 + 0.0025:.3f} -o OUT"); bad += 1
    # Stray sounds: words the local pass hears that the base transcript doesn't have nearby.
    tr = a.transcript or os.path.splitext(a.video)[0] + "_transcript.json"
    if os.path.exists(tr):
        known = json.load(open(tr))
        known = known["words"] if isinstance(known, dict) else known
        for st, en, w in local_words(a.video):
            k = norm(w)
            num = lambda v: bool(re.search(r"\d", v)) or v in NUMBER_WORDS
            if k and not any((norm(x["word"]) == k or num(k) and num(norm(x["word"])))
                             and abs(x["start"] - st) < 1.0 for x in known):
                print(f"  STRAY  {st:6.2f}–{en:6.2f}  {w!r} is not in the transcript here"); bad += 1
    else:
        print(f"  (no {tr}: pass --transcript to check for stray sounds)")
    print(f"{bad} to check. Confirm each with `envelope` and a spectrogram before cutting:"
          " STRAY can be a mis-heard word, and a real one is cut with a 0.04s acrossfade, never a hard cut.")


def declick(a):
    """Duck each click with a 12ms smooth dip. Keeps the length, so nothing downstream shifts."""
    g = "*".join(f"(1-0.95*exp(-pow((t-{t})/0.006,2)))" for t in a.times)
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-af", f"aformat=channel_layouts=stereo,aeval='val(ch)*{g}':c=same",  # mono input + aeval segfaults ffmpeg
         "-c:v", "copy", *AUD, a.out])
    src = os.path.splitext(a.video)[0] + "_transcript.json"
    if os.path.exists(src):
        json.dump(json.load(open(src)), open(os.path.splitext(a.out)[0] + "_transcript.json", "w"))
    print(f"{a.out}: {len(a.times)} click(s) smoothed")


def sway(a):
    stem = os.path.splitext(a.video)[0]
    # 4% overscan, two slow sines per axis, so it reads as a hand holding the phone, not a wobble.
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf",
         "scale=1124:1998,crop=1080:1920:x='22+12*sin(t*0.83)+5*sin(t*2.1+1)':y='39+14*sin(t*0.61+2)+5*sin(t*1.7)'",
         "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-c:a", "copy", f"{stem}-sway.mp4"])
    if os.path.exists(f"{stem}_transcript.json"):
        open(f"{stem}-sway_transcript.json", "w").write(open(f"{stem}_transcript.json").read())
    print(f"{stem}-sway.mp4")


def assemble(a):
    spec = json.load(open(a.spec))
    base = spec["base"]
    stem = os.path.splitext(base)[0]
    tr = json.load(open(spec.get("transcript", f"{stem}_transcript.json")))
    words = tr["words"]
    dur = duration(base)

    # Cutaway windows first, so the face never flashes for a split second between two shots.
    min_face = spec.get("min_face", 0.8)
    cuts = sorted(({**c, "start": when(words, c), "d": c["dur"]}
                   for c in spec.get("cutaways", [])), key=lambda c: c["start"])
    for x, y in zip(cuts, cuts[1:]):
        gap = y["start"] - (x["start"] + x["d"])
        if 0 < gap < min_face:
            x["d"] += gap
    for c in cuts:
        # A stretched shot must stop short of its source's end, or the next scene's frames leak in.
        c["off"] = max(0.0, min(c.get("off", 0), duration(c["src"]) - c["d"] - 0.2))
    edges = [t for c in cuts for t in (c["start"], c["start"] + c["d"])]

    # Switch framing on a sentence end or a pause-stretched word, every ~2.5-4s, never next to a cutaway edge.
    spans, s0 = [], 0.0
    for i, w in enumerate(words[1:], 1):
        prev = words[i - 1]
        natural = re.search(r"[.?!,]$", prev["word"].strip()) or prev["end"] - prev["start"] > 0.5
        gap = w["start"] - s0
        if (natural and gap >= 2.3) or gap >= 4.0:
            t = w["start"] - 0.02
            if any(abs(t - e) < 0.7 for e in edges):
                continue
            spans.append((s0, t)); s0 = t
    spans.append((s0, dur))
    zoom_spans = spans[1::2]

    z = spec.get("zoom", 1.2)
    cw, ch = int(W / z) // 2 * 2, int(H / z) // 2 * 2
    inputs = ["-i", base]
    f = ["[0:v]split[b0][bz]", f"[bz]crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.3,scale={W}:{H},setsar=1[z]",
         f"[b0][z]overlay=enable='{'+'.join(f'between(t,{x:.3f},{y:.3f})' for x, y in zoom_spans) or '0'}'[v0]"]
    last, nocap = "[v0]", []
    for k, c in enumerate(cuts):
        start, d = c["start"], c["d"]
        inputs += ["-ss", f"{c['off']:.3f}", "-t", f"{d + 0.1:.3f}", "-i", c["src"]]  # spare frames so back-to-back shots never flash the face
        f.append(f"[{k + 1}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
                 f"setpts=PTS-STARTPTS+{start:.3f}/TB[c{k}]")
        f.append(f"{last}[c{k}]overlay=eof_action=pass:enable='between(t,{start:.3f},{start + d:.3f})'[v{k + 1}]")
        last = f"[v{k + 1}]"
        if c.get("nocap"):
            nocap.append((start, start + d))
        print(f"  {os.path.basename(c['src']):34s} {start:6.2f} → {start + d:6.2f}  (src {c['off']:.2f}s)")

    # Overlays: transparent .mov pop-ups (cards, phone, hook text) composited over everything.
    n_in = len(cuts) + 1
    for k, o in enumerate(spec.get("overlays", [])):
        t = when(words, o)
        inputs += ["-itsoffset", f"{t:.3f}", "-i", o["src"]]
        f.append(f"{last}[{n_in + k}:v]overlay=eof_action=pass[o{k}]")
        last = f"[o{k}]"
        print(f"  overlay {os.path.basename(o['src']):26s} {t:6.2f} → {t + duration(o['src']):6.2f}")

    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(f), "-map", last, "-map", "0:a",
         *ENC, "-c:a", "copy", f"{stem}-layered.mp4"])
    # Captions hold CAP_HOLD after a word, so a word just before a caption-free window would leak onto it.
    # Drop a lone word that starts inside that margin, and end earlier words before it.
    def keep(w):
        return not any(x - CAP_HOLD <= w["start"] < y for x, y in nocap)
    def trim(w):
        for x, _ in nocap:
            if w["start"] < x - CAP_HOLD < w["end"]:
                w["end"] = max(w["start"] + 0.05, x - CAP_HOLD - 0.01)
        return w
    tr["words"] = [trim(w) for w in words if keep(w)]
    for seg in tr.get("segments") or []:
        if "words" in seg:
            seg["words"] = [trim(w) for w in seg["words"] if keep(w)]
    json.dump(tr, open(f"{stem}-cap_transcript.json", "w"))
    broll = sum(c["d"] for c in cuts)
    print(f"{stem}-layered.mp4: {dur:.2f}s, B-roll {broll:.1f}s ({broll / dur:.0%}), "
          f"{len(zoom_spans)} punch-ins, {len(nocap)} caption-free windows")


def sfx(a):
    import numpy as np
    spec = json.load(open(a.spec))
    stem = os.path.splitext(spec["base"])[0]
    words = json.load(open(spec.get("transcript", f"{stem}_transcript.json")))["words"]
    SR, rng = 48000, np.random.default_rng(1)
    env = lambda d, k: (np.arange(int(d * SR)) / SR, np.exp(-k * np.arange(int(d * SR)) / SR))

    def pop():  # card appears
        t, e = env(.09, 45); return 0.55 * np.sin(2 * np.pi * np.cumsum(1100 - 5000 * t) / SR) * e
    def tick():  # counter step
        t, e = env(.03, 220); return 0.35 * np.sin(2 * np.pi * 2600 * t) * e
    def tap():  # finger on a button
        t, e = env(.05, 160); return 0.3 * (rng.uniform(-1, 1, len(t)) * 0.5 + np.sin(2 * np.pi * 1800 * t)) * e
    def ding():  # success
        t, e = env(1.2, 3.5)
        return 0.28 * (np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t) * np.exp(-2 * t)) * e
    kinds = {"pop": pop, "tick": tick, "tap": tap, "ding": ding}

    tr = np.zeros(int(SR * (duration(a.video) + 2)))
    for item in spec["sfx"]:
        t0 = when(words, {"lead": 0, **item})
        n, over = item.get("n", 1), item.get("over", 0)
        for i in range(n):
            snd, at = kinds[item["kind"]](), int((t0 + (i * over / max(1, n - 1) if n > 1 else 0)) * SR)
            tr[at:at + len(snd)] += snd[:len(tr) - at]
    wav = os.path.splitext(a.out)[0] + "_sfx.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", wav],
        input=(np.clip(tr, -1, 1) * 32767).astype(np.int16).tobytes(), text=False)
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-i", wav, "-filter_complex",
         f"[1:a]volume={spec.get('sfx_volume', 0.5)},aformat=channel_layouts=stereo[s];"
         "[0:a]aresample=48000[v];[v][s]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", *AUD, a.out])
    print(f"{a.out}: {len(spec['sfx'])} sfx cues")


def review(a):
    log = subprocess.run(["ffmpeg", "-i", a.video, "-vf", "scdet=threshold=12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    cuts = [float(x) for x in re.findall(r"lavfi\.scd\.time: ([\d.]+)", log)]
    end = duration(a.video)
    bounds = [0.0] + cuts + [end]
    shots = list(zip(bounds, bounds[1:]))
    short = [(s, e) for s, e in shots if e - s < 0.6]
    print(f"{len(shots)} shots, avg {end / len(shots):.2f}s")
    for s, e in short:
        print(f"  SHORT  {s:6.2f} → {e:6.2f}  ({e - s:.2f}s)")
    if not short:
        print("  no shots under 0.6s")
    t0, t1 = a.start or 0.0, a.end or end
    sheet = os.path.splitext(a.video)[0] + f"-review-{t0:.0f}-{t1:.0f}.jpg"
    frames = int((t1 - t0) * 6)
    cols = 18
    rows = max(1, math.ceil(frames / cols))
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", a.video,
         "-vf", f"fps=6,scale=-2:150,tile={cols}x{rows}", "-frames:v", "1", sheet])
    print(f"contact sheet (6fps, rows of 3s): {sheet}")


def endcard(a):
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(a.dur), "-i", a.image, "-f", "lavfi",
         "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"scale={W}:{H},setsar=1,fps={FPS},format=yuv420p",
         "-shortest", "-c:v", "libx264", "-preset", "fast", "-crf", "17", *AUD, a.out])
    print(a.out)


def finish(a):
    lst = os.path.splitext(a.out)[0] + "_concat.txt"
    open(lst, "w").write(f"file '{os.path.abspath(a.video)}'\nfile '{os.path.abspath(a.card)}'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264",
         "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", *AUD, "-movflags", "+faststart", a.out])
    os.remove(lst)
    mb = os.path.getsize(a.out) / 1e6
    print(f"{a.out}: {duration(a.out):.2f}s, {mb:.1f}MB" + ("  (over 30MB: raise -crf to send it)" if mb > 30 else ""))


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("prep"); s.add_argument("clips", nargs="+"); s.add_argument("-o", dest="out", required=True)
s.add_argument("--speed", type=float, default=1.05); s.set_defaults(fn=prep)
s = sub.add_parser("fillers"); s.add_argument("video"); s.set_defaults(fn=fillers)
s = sub.add_parser("envelope"); s.add_argument("video"); s.add_argument("start", type=float)
s.add_argument("dur", type=float); s.set_defaults(fn=envelope)
s = sub.add_parser("gaps"); s.add_argument("video"); s.add_argument("--from", dest="start", type=float)
s.add_argument("--to", dest="end", type=float); s.add_argument("--db", type=int, default=-32); s.set_defaults(fn=gaps)
s = sub.add_parser("breath"); s.add_argument("video"); s.add_argument("at", type=float); s.add_argument("dur", type=float)
s.add_argument("-o", dest="out", required=True); s.set_defaults(fn=breath)
s = sub.add_parser("audiocheck"); s.add_argument("video"); s.add_argument("--transcript")
s.set_defaults(fn=audiocheck)
s = sub.add_parser("declick"); s.add_argument("video"); s.add_argument("times", type=float, nargs="+")
s.add_argument("-o", dest="out", required=True); s.set_defaults(fn=declick)
s = sub.add_parser("sway"); s.add_argument("video"); s.set_defaults(fn=sway)
s = sub.add_parser("sfx"); s.add_argument("video"); s.add_argument("spec"); s.add_argument("out"); s.set_defaults(fn=sfx)
s = sub.add_parser("assemble"); s.add_argument("spec"); s.set_defaults(fn=assemble)
s = sub.add_parser("review"); s.add_argument("video"); s.add_argument("--from", dest="start", type=float)
s.add_argument("--to", dest="end", type=float); s.set_defaults(fn=review)
s = sub.add_parser("endcard"); s.add_argument("image"); s.add_argument("out")
s.add_argument("--dur", type=float, default=1.8); s.set_defaults(fn=endcard)
s = sub.add_parser("finish"); s.add_argument("video"); s.add_argument("card"); s.add_argument("out")
s.set_defaults(fn=finish)
a = p.parse_args()
a.fn(a)
