"""Demo reel for the cinematic room look (cutroom.cinematic): a graded talking head with the top half free, a
serif title, floating screens, text behind the person, a blur-in keyword over a dimmed shot, an odometer, the
native comment bar and Follow button. Without --face it draws a stand-in room and person.

    python3 cinematic_showcase.py OUT.mp4 [--face base.mp4 --mask mask.mp4 --face-start 0] [--preview t1,t2,...]
"""
import sys, os, math, argparse
sys.path.insert(0, os.environ.get("CUTROOM_ENGINE", ""))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from cutroom import cinematic as C, light as L
from cutroom.core import W, H, FPS, font, SFT, MONO, Reader
from cutroom import parallel

def stand_in_room():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.dstack([46 + 0 * xx, 48 + 0 * xx, 54 + 0 * xx])
    lamp = np.exp(-(((xx - 150) / 260) ** 2 + ((yy - 560) / 420) ** 2))[..., None] * np.array([150, 92, 40])
    win = np.exp(-(((xx - 930) / 300) ** 2 + ((yy - 420) / 600) ** 2))[..., None] * np.array([40, 92, 104])
    floor = np.clip((yy - 1300) / 600, 0, 1)[..., None] * np.array([-20, -20, -22])
    im = Image.fromarray(np.clip(base + lamp + win + floor, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for x, y, r, c in [(220, 760, 46, (255, 196, 120, 60)), (860, 300, 30, (180, 230, 255, 50)), (700, 640, 22, (255, 210, 150, 40))]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    d.rectangle((640, 980, 1080, 1010), fill=(70, 52, 40, 255))
    return im.filter(ImageFilter.GaussianBlur(14)).convert("RGB")

def stand_in_person():
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    d.ellipse((160, 1240, 920, 2300), fill=255); d.rounded_rectangle((470, 1080, 610, 1300), 40, fill=255)
    d.ellipse((380, 760, 700, 1150), fill=255)
    body = Image.new("RGB", (W, H), (34, 40, 52)); d2 = ImageDraw.Draw(body)
    d2.ellipse((380, 760, 700, 1150), fill=(206, 160, 128)); d2.rounded_rectangle((470, 1080, 610, 1300), 40, fill=(190, 146, 116))
    d2.ellipse((370, 720, 710, 920), fill=(40, 30, 26)); d2.ellipse((160, 1240, 920, 2300), fill=(52, 62, 50))
    return body.filter(ImageFilter.GaussianBlur(2)), m.filter(ImageFilter.GaussianBlur(2))

ROOM = stand_in_room()
BODY, MASK = stand_in_person()

def stand_in_frame(t):
    dx, dy = 6 * math.sin(t * 0.9), 4 * math.sin(t * 1.3 + 1)
    fr = ROOM.copy(); fr.paste(BODY, (int(dx), int(dy)), MASK)
    m = Image.new("L", (W, H), 0); m.paste(MASK, (int(dx), int(dy))); return fr, m

def screen_prompt():
    cv = L.canvas(); L.prompt_card(cv, 5.0, "Make every graphic in this reel move on the beat.", t_type=0, cps=99, cy=520)
    return cv.crop((40, 300, 1040, 760)).convert("RGB")

def screen_terminal():
    im = Image.new("RGB", (1000, 560), (14, 14, 16)); d = ImageDraw.Draw(im); f = font(MONO, 30)
    for i, (c, s) in enumerate([((217, 119, 87), "✻ Rendering reel_v3.mp4"), ((150, 150, 156), "  frames 812/812"),
                                ((120, 200, 140), "  ✓ every cut in a silence"), ((120, 200, 140), "  ✓ captions in sync"),
                                ((230, 230, 230), "  saved to videos/launch/")]):
        d.text((48, 70 + i * 82), s, font=f, fill=c)
    return im

SCREENS = (screen_prompt(), screen_terminal())

def S_title(cv, k, person):
    C.serif_title(cv, k, "How I edit / *every video* with / *Claude Opus 5.5*", cy=260)
def S_cards(cv, k, person):
    C.float_card(cv, k - 0.1, SCREENS[0], cy=330, w=900, source="via claude.ai")
    C.float_card(cv, k - 1.3, SCREENS[1], cy=700, w=760, source="via terminal")
def S_behind(cv, k, person): C.behind_word(cv, k - 0.1, "CLAUDE", person, cy=820, size=330)
def S_headline(cv, k, person): C.headline(cv, k - 0.2, "stand out", cy=360)
def S_odometer(cv, k, person): C.odometer(cv, k - 0.1, 0, 26, cy=360, label="effects, one prompt")
def S_hook(cv, k, person): C.hook_box(cv, k, "Content is free now. / Taste isn't.", cy=300)
def S_spot(cv, k, person): C.spotlight(cv, k, cx=540, cy=1100, r=520)
def S_cta(cv, k, person):
    C.comment_bar(cv, k - 0.1, "MOTION", cy=1460, t_type=0.4, t_post=1.3)
    if k > 1.7: C.follow_row(cv, k - 1.7, "sully", cy=1640, t_tap=0.8)

SEGS = [("serif_title", 3.0, S_title), ("float_card", 3.0, S_cards), ("behind_word", 2.4, S_behind),
        ("headline (dims the shot)", 2.0, S_headline), ("odometer", 2.0, S_odometer), ("hook_box", 2.0, S_hook),
        ("spotlight", 2.4, S_spot), ("comment_bar + follow_row", 3.6, S_cta)]
STARTS, acc = [], 0.0
for s in SEGS: STARTS.append(acc); acc += s[1]
TOTAL = acc
SERIF_CAPS = [("This whole reel was edited by Claude.", 0.2, 2.9), ("It pulls the screens in for me.", 3.1, 5.9)]
KEY_CAPS = [("and it can put text *behind me*", 6.1, 8.3), ("this is how you", 8.5, 9.1), ("this is how you *stand out*", 9.1, 10.3),
            ("one prompt gets you", 10.5, 11.2), ("one prompt gets you *26 effects*", 11.2, 12.4)]
SERIF_CAPS2 = [("Content is free now.", 12.5, 13.6), ("And it lights the room for you.", 14.5, 16.7)]
KEY_CAPS2 = [("comment *motion*", 16.9, 18.4), ("and *follow* for more", 18.5, 20.4)]

def seg_at(t):
    for i in range(len(SEGS) - 1, -1, -1):
        if t >= STARTS[i]: return i, t - STARTS[i]
    return 0, t

def make_frame(i, srcs):
    t = i / FPS
    si, k = seg_at(t)
    name, dur, fn = SEGS[si]
    if srcs:
        fr = srcs[0].next(); m = srcs[1].next() if len(srcs) > 1 else None
    else: fr, m = stand_in_frame(t)
    cv = C.grade(fr)
    person = C.cutout(cv, m) if m is not None else None
    fn(cv, k, person)
    C.serif_caption(cv, t, SERIF_CAPS + SERIF_CAPS2, cy=1330)
    C.key_caption(cv, t, KEY_CAPS + KEY_CAPS2, cy=1250)
    ImageDraw.Draw(cv).text((48, 60), f"cinematic · {name}", font=font(SFT("Medium"), 26), fill=(200, 200, 204), anchor="lm")
    return cv

def open_sources(t0, a):
    if not a.face: return ()
    srcs = [Reader(a.face, 1080, 1920, start=a.face_start + t0)]
    if a.mask and os.path.exists(a.mask): srcs.append(Reader(a.mask, 540, 960, start=a.face_start + t0))
    return tuple(srcs)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--face"); ap.add_argument("--mask"); ap.add_argument("--face-start", type=float, default=0.0)
    ap.add_argument("--preview"); ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if a.preview:
        for t in [float(x) for x in a.preview.split(",")]:
            srcs = open_sources(t, a)
            make_frame(int(round(t * FPS)), srcs).convert("RGB").save(f"{os.path.splitext(a.out)[0]}_{t:05.2f}.jpg", quality=88)
            for s in srcs: s.close()
    else:
        parallel.render(a.out, int(TOTAL * FPS), make_frame, lambda t0: open_sources(t0, a), workers=a.workers)
