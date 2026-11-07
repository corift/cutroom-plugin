import os
"""Sound design, synthesized with numpy (no sample packs needed; drop real files into
assets/sfx/ and pass them as events to override).

Palette (from @rpn / @kallaway analysis, see references/sound-design.md):
  bed     warm low synth pad under the whole piece, ducked ~9 dB under the voice
  boom    sub-bass hit (60->32 Hz, ~2 s decay) on section titles / the hook / the end card
  whoosh  airy band-passed noise swell into a split/full-screen change (peaks AT the cut)
  riser   0.8 s filtered noise + rising tone into a big reveal
  tick    very soft high blip for checklist items / numbers (NOT a cartoon plop)
  dropout bed + voice-room goes silent for ~0.4 s right before the final hit
No pops, boings, bubble plops, or cartoon swooshes.
"""
import subprocess, wave
import numpy as np

SR = 48000

def _t(d): return np.arange(int(d * SR)) / SR

def _lp(x, cutoff):
    """One-pole low-pass (cutoff may be an array for sweeps)."""
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc; y[i] = acc
    return y

def _bp(x, lo, hi): return _lp(x, hi) - _lp(x, lo)

def boom(d=2.2, f0=62, f1=32, gain=1.0):
    t = _t(d)
    f = f1 + (f0 - f1) * np.exp(-t * 5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 2.1)
    click = _lp(np.random.randn(len(t)), 1800) * np.exp(-t * 60) * 0.25
    x = np.tanh((body + click) * 1.6) * 0.9
    return x * gain

def whoosh(d=0.55, gain=0.35, bright=5500):
    """Peaks at d*0.75 -> place so that start = cut - 0.75*d."""
    t = _t(d)
    envl = np.sin(np.pi * np.clip(t / (d * 0.75), 0, 1) / 2) ** 3
    envl *= np.where(t > d * 0.75, np.exp(-(t - d * 0.75) * 18), 1)
    n = np.random.randn(len(t))
    cut = 600 + bright * (t / d) ** 1.5
    x = _bp(n, 250, cut) * envl
    return x / (np.abs(x).max() + 1e-9) * gain

def riser(d=0.9, gain=0.22):
    t = _t(d)
    n = _bp(np.random.randn(len(t)), 400, 800 + 7000 * (t / d) ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * (t / d) ** 2) / SR) * 0.25
    x = (n / (np.abs(n).max() + 1e-9) + tone) * (t / d) ** 2.2
    return x * gain

def tick(gain=0.12, f=2400):
    t = _t(0.09)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 70) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t * 110)
    return x * gain

def pad(dur, chord=(146.83, 220.0, 277.18, 329.63, 440.0), gain=0.06, cutoff=900):
    """Slow detuned-saw pad (Dmaj9-ish), gently filtered, with slow swell."""
    t = _t(dur)
    x = np.zeros_like(t)
    for i, f in enumerate(chord):
        for det in (-0.004, 0.0, 0.005):
            ph = (f * (1 + det) * t + np.random.rand()) % 1.0
            x += (2 * ph - 1) * (0.7 if i else 1.0)
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)
    x = _lp(x, cutoff * (0.7 + 0.5 * lfo))
    x /= np.abs(x).max() + 1e-9
    return x * gain

def read_voice(media):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", media, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def duck_curve(voice, depth_db=-9, att=0.05, rel=0.35):
    """1.0 when voice is silent, depth when talking (smoothed)."""
    hop = int(SR * 0.01)
    n = len(voice) // hop
    rms = np.sqrt((voice[:n * hop].reshape(n, hop) ** 2).mean(1))
    talk = (20 * np.log10(rms + 1e-9) > -38).astype(float)
    g, out = 0.0, np.empty(n)
    for i, v in enumerate(talk):
        k = 0.01 / (att if v > g else rel); g += (v - g) * min(1, k); out[i] = g
    target = 1 - out * (1 - 10 ** (depth_db / 20))
    return np.repeat(target, hop)

def mix(voice_media, dur, events, out_wav, bed=None, dropouts=(), bed_fade=(0.0, 1.5), dry=85):
    """events: [(time, np.array)] mono clips. bed: mono array (looped/cropped to dur).
    dropouts: [(t0, t1)] where bed + fx are muted (voice untouched).
    dry: the voice goes through Apple voice isolation at this wet % first (room echo + noise out;
    "it sounds perfect"). 85 leaves a touch of room so it doesn't sound processed; 0/None = raw voice."""
    if dry:
        from . import voice
        voice_media = voice.dried(voice_media, dry) or voice_media
    n = int(dur * SR)
    v = np.zeros(n); vv = read_voice(voice_media)[:n]; v[:len(vv)] = vv
    fx = np.zeros(n)
    for t, clip in events:
        i = int(t * SR)
        if i < 0: clip = clip[-i:]; i = 0
        m = min(len(clip), n - i)
        if m > 0: fx[i:i + m] += clip[:m]
    b = np.zeros(n)
    if bed is not None:
        reps = int(np.ceil(n / len(bed)))
        b = np.tile(bed, reps)[:n]
        fi = int(bed_fade[1] * SR); b[:fi] *= np.linspace(0, 1, fi) ** 2
        fo = int(1.2 * SR); b[-fo:] *= np.linspace(1, 0, fo)
        dc = duck_curve(v); m = min(len(dc), n); b[:m] *= dc[:m]
    mute = np.ones(n)
    for a0, a1 in dropouts:
        i0, i1 = int(a0 * SR), int(a1 * SR); r = int(0.04 * SR)
        mute[i0:i1] = 0; mute[i0 - r:i0] = np.linspace(1, 0, r)
    x = v + (fx + b) * mute
    stereo = np.stack([x, x], 1)
    stereo = np.clip(stereo, -1, 1)
    tmp = out_wav + ".raw.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    # final loudness: -14 LUFS integrated, -1 dBTP (Instagram/TikTok normal)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                    "-ar", str(SR), out_wav], check=True)
    subprocess.run(["rm", tmp])
    return out_wav

def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tail = r[r.rfind("Summary:"):]
    return " ".join(l.strip() for l in tail.splitlines() if ("I:" in l or "Peak:" in l))

# ================================================================== real samples (preferred)
# The shipped sound library (packages/core/assets/sfx). Override with CUTROOM_ASSETS.
LIBRARY = os.path.join(os.environ.get("CUTROOM_ASSETS") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets"), "")
SFX_DIR = LIBRARY + "sfx/"
# The user's own sounds (account/assets/sfx), searched first, so a name there overrides ours.
USER_SFX_DIR = os.path.join(os.environ["CUTROOM_ACCOUNT"], "sfx") + "/" if os.environ.get("CUTROOM_ACCOUNT") else None

def load(name, gain=1.0, start=0.0, dur=None, fade=0.05):
    """Load a sample from assets/sfx (or a path) as mono 48k, peak-normalised, times `gain`.
    Place it with the sample's own onset in mind (see references/sound-design.md table)."""
    path = name if "/" in name else (USER_SFX_DIR + name if USER_SFX_DIR and os.path.exists(USER_SFX_DIR + name) else SFX_DIR + name)
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path]
    if dur: cmd += ["-t", str(dur)]
    raw = subprocess.check_output(cmd + ["-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x / (np.abs(x).max() + 1e-9)
    f = int(fade * SR)
    if dur and len(x) > 2 * f: x[-f:] *= np.linspace(1, 0, f)
    return x * gain

def at(t, clip, onset):
    """Event whose audible onset/peak (`onset` s into the file) lands exactly on t."""
    return (t - onset, clip)
