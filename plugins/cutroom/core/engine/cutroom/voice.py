"""Dry voice: Apple's on-device voice isolation (AUSoundIsolation, the model behind Final Cut's Voice Isolation),
run offline through scripts/voiceisolate.swift. Removes room echo + background noise, keeps timing sample-exact.

Used by default for every video (echo-y rooms leave a lot of dead air):
  * cutplan.speech_env(src)  plans pauses on the voice dried at 100% (the echo tail otherwise hides every pause)
  * sound.mix(..., dry=0.85) mixes the voice dried at 85% (a touch of room left so it doesn't sound processed)
macOS only. Elsewhere (cloud sandbox) available() is False and callers fall back to the raw audio with a warning.
TODO: cloud fallback via a Modal endpoint, like the matte service (tools/matte/modal_matte.py)."""
import hashlib, os, shutil, subprocess, sys

SWIFT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voiceisolate.swift")
CACHE = os.path.expanduser("~/.cache/cutroom")
BIN = os.path.join(CACHE, "voiceisolate")

def available():
    return sys.platform == "darwin" and (os.path.exists(BIN) or shutil.which("swiftc") is not None)

def _binary():
    """Compile voiceisolate.swift once (rebuilt when the source changes)."""
    os.makedirs(CACHE, exist_ok=True)
    stamp = BIN + ".src"
    src_hash = hashlib.sha1(open(SWIFT, "rb").read()).hexdigest()
    if not (os.path.exists(BIN) and os.path.exists(stamp) and open(stamp).read() == src_hash):
        subprocess.run(["swiftc", "-O", SWIFT, "-o", BIN], check=True, capture_output=True)
        open(stamp, "w").write(src_hash)
    return BIN

def isolate(media, out_wav, wet=100):
    """media (any audio/video) -> mono 48k wav of the dried voice. Cached next to out_wav: skipped if newer than media."""
    if os.path.exists(out_wav) and os.path.getmtime(out_wav) > os.path.getmtime(media) and out_wav.endswith(f"_iso{int(wet)}.wav"):
        return out_wav
    raw = out_wav + ".raw.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", media, "-vn", "-ac", "1", "-ar", "48000", raw], check=True)
    subprocess.run([_binary(), raw, out_wav, str(wet)], check=True, capture_output=True)
    os.remove(raw)
    return out_wav

def dried(media, wet=100):
    """Path of the dried voice for `media` (made on first use, cached), or None when isolation isn't available."""
    if not available():
        print(f"voice: AUSoundIsolation not available here (macOS only), using the raw audio of {media}")
        return None
    stem = os.path.splitext(os.path.basename(media))[0]
    return isolate(media, os.path.join(os.path.dirname(os.path.abspath(media)), f"{stem}_iso{int(wet)}.wav"), wet)
