"""Cut planning: transcription, energy envelope, silence-snapped segments, base assembly, QA.

Rules this module enforces (see references/cut-rules.md):
  * boundaries snap to the quietest 10 ms point near the requested time (never mid-word)
  * pauses are found on the DRIED voice (speech_env: Apple voice isolation): room echo otherwise keeps every
    pause above SIL_DB and nothing gets trimmed
  * on face-visible sections, pauses > MAX_PAUSE are shortened, leaving HANDLE of air on both sides (~0.16 s joins)
  * inside `tight` windows (face covered by full-screen B-roll) pauses > 0.25 s are trimmed
  * QA re-transcribes the assembled cut and fails on doubled words ("so so") / lost words. Use ElevenLabs Scribe:
    it is verbatim (keeps repeats, false starts); Groq Whisper silently drops them, so its QA passes cuts that repeat
"""
import json, os, re, subprocess, tempfile, wave
import numpy as np

from . import account

HOP = 0.01          # envelope resolution (s)
MAX_PAUSE = 0.25    # trim pauses longer than this (was 0.50: left 0.3-0.5 s of dead air at most joins)
TIGHT_PAUSE = 0.25  # face hidden under B-roll: trim pauses longer than this
HANDLE = 0.08       # air kept either side of a trimmed pause (was 0.12)
SIL_DB = -42        # silence threshold on the RAW audio (dBFS)
SIL_DB_DRY = -38    # silence threshold on the dried voice (speech_env)

# ------------------------------------------------------------------ transcription
def transcribe(media, out_json, prompt=""):
    """Word-timestamped transcript -> {"text", "words": [{"word", "start", "end"}], "provider"}.
    ElevenLabs Scribe when ELEVENLABS_API_KEY is set (more accurate on names, tighter word times),
    else Groq whisper-large-v3 (GROQ_API_KEY). Keys are never printed. `prompt` only helps Groq."""
    with tempfile.TemporaryDirectory() as td:
        mp3 = os.path.join(td, "a.mp3")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", media, "-ac", "1", "-ar", "16000", "-b:a", "64k", mp3], check=True)
        if os.environ.get("ELEVENLABS_API_KEY"):
            res = _scribe(mp3, td)
        elif cutroom_site() and account.key():
            res = _hosted(mp3, td)
        elif os.environ.get("GROQ_API_KEY"):
            res = _groq(mp3, td, prompt)
        else:
            raise RuntimeError("no transcription: sign in to Cutroom, or set ELEVENLABS_API_KEY or GROQ_API_KEY")
    json.dump(res, open(out_json, "w"), indent=1)
    return res

def _curl_json(td, header, url, fields):
    # The key goes through a curl config file so it never shows up in the process list.
    cfg = os.path.join(td, "h")
    with open(cfg, "w") as f: f.write(f'header = "{header}"\n')
    cmd = ["curl", "-s", "-K", cfg, url]
    for k, v in fields: cmd += ["-F", f"{k}={v}"]
    return json.loads(subprocess.check_output(cmd))

def _scribe(mp3, td):
    model = os.environ.get("SCRIBE_MODEL", "scribe_v2")
    res = _curl_json(td, f"xi-api-key: {os.environ['ELEVENLABS_API_KEY']}", "https://api.elevenlabs.io/v1/speech-to-text",
                     [("model_id", model), ("language_code", "en"), ("timestamps_granularity", "word"),
                      ("tag_audio_events", "false"), ("file", f"@{mp3}")])
    if "words" not in res: raise RuntimeError(f"transcription failed: {str(res)[:300]}")
    words = [{"word": w["text"], "start": w["start"], "end": w["end"]} for w in res["words"] if w.get("type") == "word"]
    return {"text": res.get("text", ""), "words": words, "provider": f"elevenlabs/{model}"}

def cutroom_site():
    return account.site()

def _hosted(mp3, td):
    cfg = os.path.join(td, "h")
    with open(cfg, "w") as f: f.write(f'header = "Authorization: Bearer {account.key()}"\n')
    out = subprocess.check_output(["curl", "-s", "-m", "600", "-K", cfg, "-H", "content-type: audio/mpeg",
                                   "--data-binary", f"@{mp3}", f"{cutroom_site()}/transcribe"])
    res = json.loads(out)
    if "words" not in res: raise RuntimeError(f"transcription failed: {res.get('error', str(res)[:300])}")
    return res

def _groq(mp3, td, prompt):
    fields = [("model", "whisper-large-v3"), ("response_format", "verbose_json"),
              ("timestamp_granularities[]", "word"), ("language", "en"), ("file", f"@{mp3}")]
    if prompt: fields.append(("prompt", prompt))
    res = _curl_json(td, f"Authorization: Bearer {os.environ['GROQ_API_KEY']}",
                     "https://api.groq.com/openai/v1/audio/transcriptions", fields)
    if "words" not in res: raise RuntimeError(f"transcription failed: {str(res)[:300]}")
    res["provider"] = "groq/whisper-large-v3"
    return res

# ------------------------------------------------------------------ energy / silence
def envelope(media, sr=16000):
    """RMS dBFS per 10 ms."""
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", media, "-ac", "1", "-ar", str(sr),
                                   "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    h = int(sr * HOP); n = len(a) // h
    return 20 * np.log10(np.sqrt((a[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)

def speech_env(src):
    """(envelope, silence threshold) for planning a cut: the dried voice (Apple voice isolation, macOS) when available,
    else the raw audio. Use: env, th = cp.speech_env(SRC); cp.trim_edges(cp.plan(KEEPS, env, thresh=th), env, thresh=th)"""
    from . import voice
    dry = voice.dried(src, 100)
    return (envelope(dry), SIL_DB_DRY) if dry else (envelope(src), SIL_DB)

def silences(env, thresh=SIL_DB, min_d=0.12):
    quiet = env < thresh
    out, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None: start = i
        if (not q or i == len(quiet) - 1) and start is not None:
            if (i - start) * HOP >= min_d: out.append((start * HOP, i * HOP))
            start = None
    return out

def snap(t, env, window=0.15):
    """Move t to the quietest point within ±window (ties -> closest)."""
    i0, i1 = max(0, int((t - window) / HOP)), min(len(env) - 1, int((t + window) / HOP))
    seg = env[i0:i1 + 1]
    if not len(seg): return t
    cand = np.where(seg <= seg.min() + 1.5)[0] + i0
    best = cand[np.argmin(np.abs(cand * HOP - t))]
    return round(best * HOP, 3)

# ------------------------------------------------------------------ planning
def plan(keeps, env, tight=(), max_pause=MAX_PAUSE, tight_pause=TIGHT_PAUSE, handle=HANDLE, thresh=SIL_DB):
    """keeps: [(src_start, src_end[, snap_window]), ...] rough content ranges (sentence level).
    Use a tiny snap_window (e.g. 0.02) when a boundary must stay exactly where you measured it
    (e.g. right before a retake's first word).
    tight: [(src_start, src_end)] windows where the face is hidden -> trim harder.
    thresh: silence level (dB). In an echo-y room plan on a dried voice track (voiceisolate.swift, 100% wet):
    the raw room tail sits above -42 dB and hides every pause.
    Returns [(s, e)] segments in source time."""
    sil = silences(env, thresh)
    segs = []
    for k in keeps:
        s, e = k[0], k[1]
        win = k[2] if len(k) > 2 else 0.15
        s = s if s <= 0.01 else snap(s, env, win)   # never snap the very first frame into a word
        e = snap(e, env, win)
        cur = s
        for a, b in sil:
            if a <= s or b >= e: continue
            limit = tight_pause if any(ta <= a and b <= tb for ta, tb in tight) else max_pause
            if b - a > limit:
                segs.append((cur, round(a + handle, 3)))
                cur = round(b - handle, 3)
        segs.append((cur, e))
    return [(a, b) for a, b in segs if b - a > 0.08]

def trim_edges(segs, env, thresh=SIL_DB, head=0.08, tail=0.10):
    """Waveform pass: pull every segment's start/end in to where speech energy actually begins/ends
    (+ a small handle). Kills dead air that sits at a keep's edges (e.g. reaching for the camera
    after the last word), which plan() never touches because it only trims pauses *inside* keeps."""
    out = []
    for a, b in segs:
        i0, i1 = int(a / HOP), min(len(env) - 1, int(b / HOP))
        loud = np.where(env[i0:i1 + 1] >= thresh)[0]
        if not len(loud): continue
        na = max(a, round((i0 + loud[0]) * HOP - head, 3))
        nb = min(b, round((i0 + loud[-1]) * HOP + tail, 3))
        if nb - na > 0.08: out.append((na, nb))
    return out

def report(segs):
    """Human-readable cut plan for the review gate."""
    t, lines = 0.0, []
    for i, (a, b) in enumerate(segs):
        lines.append(f"{i:02d}  src {a:6.2f}-{b:6.2f}  out {t:6.2f}  len {b - a:5.2f}"
                     + ("   <-- SHORT (<0.6s)" if b - a < 0.6 else ""))
        t += b - a
    lines.append(f"total {t:.2f}s, {len(segs)} segments, {len(segs) - 1} cuts")
    return "\n".join(lines)

# ------------------------------------------------------------------ assembly
def build(src, segs, out, fps=30, polish=True, speed=1.0):
    """Trim/concat with 12 ms audio fades at every join; writes out + segments.json next to it.
    speed > 1 speeds the whole cut up (setpts + atempo); segments.json out_start is in sped-up time."""
    parts, labels = [], []
    for i, (s, e) in enumerate(segs):
        d = e - s; f = min(0.012, d / 4)
        parts.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps={fps}[v{i}]")
        parts.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d={f},afade=t=out:st={d - f:.4f}:d={f}[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    vout = "[vc]" if speed != 1.0 else "[v]"
    parts.append("".join(labels) + f"concat=n={len(segs)}:v=1:a=1{vout}[araw]")
    if speed != 1.0:
        parts.append(f"[vc]setpts=PTS/{speed},fps={fps}[v]")
    chain = ("highpass=f=80,equalizer=f=3500:t=q:w=1.2:g=2.5,"
             "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,"
             "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000") if polish else "aresample=48000"
    chain += ",aformat=channel_layouts=stereo"  # ffmpeg 5.x (cloud editor) can't pick a layout after loudnorm
    parts.append(f"[araw]{'atempo=%s,' % speed if speed != 1.0 else ''}{chain}[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(parts),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
                    "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le" if out.endswith(".mov") else "aac",
                    "-b:a", "256k", out], check=True)
    t, meta = 0.0, []
    for s, e in segs:
        meta.append({"src_start": s, "src_end": e, "out_start": round(t, 4)}); t += (e - s) / speed
    json.dump(meta, open(os.path.join(os.path.dirname(out) or ".", "segments.json"), "w"), indent=1)
    return meta

def src_to_out(t, meta):
    """Map a source timestamp to output time (None if it was cut)."""
    for m in meta:
        if m["src_start"] <= t <= m["src_end"]:
            return round(m["out_start"] + t - m["src_start"], 3)
    return None

# ------------------------------------------------------------------ QA
def _norm(w): return re.sub(r"[^a-z0-9']", "", w.lower())

def qa(media, out_json, expected=""):
    """Re-transcribe the cut. Flags doubled words and (if `expected` given) missing words."""
    res = transcribe(media, out_json)
    ws = [_norm(w["word"]) for w in res["words"]]
    issues = []
    if "elevenlabs" not in str(res.get("provider", "")):
        issues.append("QA ran on Groq Whisper, which drops repeated words: set ELEVENLABS_API_KEY for a verbatim check")
    for a, b in zip(res["words"], res["words"][1:]):          # dead air the planner missed
        if b["start"] - a["end"] > MAX_PAUSE + 0.1:
            issues.append(f"pause {b['start'] - a['end']:.2f}s at {a['end']:.2f}s ('{a['word'].strip()}' -> '{b['word'].strip()}')")
    for i in range(1, len(ws)):
        if ws[i] and ws[i] == ws[i - 1] and ws[i] not in ("that", "had"):
            issues.append(f"doubled '{ws[i]}' at {res['words'][i]['start']:.2f}s")
    if expected:
        exp = [_norm(w) for w in expected.split() if _norm(w)]
        got = " ".join(ws)
        missing = [w for w in dict.fromkeys(exp) if w not in got]
        if missing: issues.append("possibly missing: " + ", ".join(missing[:20]))
    print("QA transcript:", res.get("text", "").strip())
    print("QA issues:", issues or "none")
    return issues
