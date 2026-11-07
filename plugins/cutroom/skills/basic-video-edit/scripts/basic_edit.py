"""Basic video edit: silence-snapped sentence cuts + clean burned-in captions, for any video.
Reuses the cut/caption code of the Cutroom engine (cutroom.cutplan / cutroom.captions).

  python basic_edit.py transcribe SRC transcript.json
  python basic_edit.py cut SRC keeps.json base.mp4 [--dry] [--qa] [--tight tight.json]
  python basic_edit.py voice base.mp4 voice.wav                      # optional de-boom EQ for close/boomy mics
  python basic_edit.py caption base.mp4 base_transcript.json out.mp4 [options]
      --vertical        center-crop to 1080x1920 (default: keep the source size/aspect)
      --y 0.80          caption center as a fraction of height (default 0.84 landscape, 0.72 vertical)
      --pill            dark pill behind captions (busy or bright backgrounds)
      --font montserrat caption face: helvetica (default, Helvetica Neue Bold) | montserrat (Montserrat Black)
      --emph "a b,c d"  phrases shown in italic serif (comma-separated)
      --fix "Cloud=Claude,opus=Opus"   mis-hear fixes (whole words)
      --audio voice.wav use this audio instead of the base's
      --preview 1.5,8,20  write stills to previews/ instead of rendering
keeps.json: [[src_start, src_end], [s, e, 0.02], ...]  (sentence-level, source seconds; 3rd value = snap window)
"""
import sys, os, json, subprocess
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))  # $CUTROOM_CORE/engine; the agent also sets PYTHONPATH
from PIL import Image
from cutroom import cutplan as cp, captions as cap
from cutroom.core import Reader, probe_duration, paste, font, text_img

FPS = 30
VOICE_EQ = ("highpass=f=90:poles=2,equalizer=f=150:t=q:w=0.9:g=-6,equalizer=f=300:t=q:w=1.2:g=-2,"
            "acompressor=threshold=-18dB:ratio=2.5:attack=5:release=80:makeup=1.5")
MONTSERRAT = os.path.join(os.path.dirname(__file__), "..", "fonts", "Montserrat.ttf")   # variable font, OFL

def caption_img(text, pill, em, face):
    """Kallaway caption in the chosen face; emphasis keeps the italic serif."""
    if face == "helvetica" or em: return cap.caption_img(text, "kallaway", pill=pill, em=em)
    im = text_img(text.replace("’", "'").rstrip(","), font(MONTSERRAT, 64, [900]), fill=(255, 255, 255),
                  tracking=-0.02, shadow=0 if pill else 200)
    return cap._pill(im, 26, 10, 18) if pill else im

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def size_of(path):
    w, h = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", path]).decode().split(",")[:2]
    return int(w), int(h)

def cmd_cut(src, keeps_json, out):
    keeps = [tuple(k) for k in json.load(open(keeps_json))]
    tight = [tuple(k) for k in json.load(open(arg("--tight")))] if "--tight" in sys.argv else []
    segs = cp.plan(keeps, cp.envelope(src), tight=tight)
    print(cp.report(segs))
    if "--dry" in sys.argv: return
    cp.build(src, segs, out)
    print("built", out)
    if "--qa" in sys.argv:
        cp.qa(out, os.path.splitext(out)[0] + "_transcript.json")

def cmd_voice(base, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", base, "-vn", "-af", VOICE_EQ + ",loudnorm=I=-14:TP=-1",
                    "-ar", "48000", out], check=True)
    print("wrote", out)

def cmd_caption(base, transcript, out):
    vertical = "--vertical" in sys.argv
    w, h = (1080, 1920) if vertical else size_of(base)
    w, h = w - w % 2, h - h % 2
    y = float(arg("--y", 0.72 if h > w else 0.84)) * h
    scale = min(w, h) / 1080                     # caption art is designed for a 1080-wide short
    fixes = dict(p.split("=", 1) for p in arg("--fix", "").split(",") if "=" in p)
    emph = [p.strip() for p in arg("--emph", "").split(",") if p.strip()]
    words = cap.join_phrases(cap.load_words(transcript, fixes=fixes), emph)
    spans = cap.chunk(words, "kallaway")
    pill = "--pill" in sys.argv
    face = arg("--font", "helvetica")

    def frame(img, t):
        canvas = img.convert("RGBA")
        cur = next((c for c in spans if c["s"] <= t < c["e"]), None)
        if cur:
            im = caption_img(cur["text"], pill, cur["em"], face)
            if abs(scale - 1) > 0.02:
                im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            paste(canvas, im, w / 2 - im.width / 2, y - im.height / 2)
        return canvas.convert("RGB")

    reader = Reader(base, w, h, 0, fill=True)    # fill=True center-crops when --vertical
    if "--preview" in sys.argv:
        os.makedirs("previews", exist_ok=True)
        want = {int(round(float(x) * FPS)) for x in arg("--preview").split(",")}
        for i in range(max(want) + 1):
            img = reader.next()
            if i in want: frame(img, i / FPS).save(f"previews/c_{i / FPS:06.2f}.jpg", quality=85)
        print("stills in previews/"); return
    audio = arg("--audio", base)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", str(FPS), "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac",
                            "-b:a", "256k", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = int(probe_duration(base) * FPS)
    for i in range(n):
        enc.stdin.write(frame(reader.next(), i / FPS).tobytes())
        if i % 600 == 0: print(f"frame {i}/{n}", flush=True)
    enc.stdin.close(); enc.wait(); reader.close()
    print("done", out)

if __name__ == "__main__":
    c, a = sys.argv[1], [x for x in sys.argv[2:] if not x.startswith("--")]
    if c == "transcribe": cp.transcribe(a[0], a[1]); print("wrote", a[1])
    elif c == "cut": cmd_cut(a[0], a[1], a[2])
    elif c == "voice": cmd_voice(a[0], a[1])
    elif c == "caption": cmd_caption(a[0], a[1], a[2])
    else: print(__doc__)
