"""Renders a short looping preview of every component in catalog.json, using the real engine blocks.

    python3 render_previews.py OUT_DIR --face base.mp4 --mask mask.mp4 --words base_transcript.json
        [--logos ~/Cutroom/account/logos] [--receipts DIR] [--tiles DIR] [--only id,id] [--start 9.6]
        [--clips DIR]  stock B-roll for the clip layouts: p_*.mp4 vertical, l_*.mp4 landscape
        [--frames DIR] [--emph "phrase,phrase"]
"""
import sys, os, json, argparse, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
from PIL import Image, ImageDraw, ImageOps
from cutroom import blocks as B, layout as L, captions as cap, components as C, basics as Bx, screens as Sc, viral as V
from cutroom.core import W, H, FPS, font, SFT, Reader, text_img, logo

FACE_BOX, SRC_Y = (160, 1380, 920, 1920), 830
FRAMING = L.Framing([], wide=1.0, tight=1.1, face_cy=0.4)
DUR = 3.2
a = None


def LG(name):
    return os.path.join(a.logos, f"{name}.png")


def RC(name):
    return os.path.join(a.receipts, name)


def tile(path, s, white=False):
    if white:
        bg = Image.new("RGBA", (s, s), (255, 255, 255, 255))
        m = logo(path, int(s * 0.7))
        bg.alpha_composite(m, ((s - m.width) // 2, (s - m.height) // 2))
        return B.rounded_rect(bg, int(s * 0.225))
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA").resize((s, s), Image.LANCZOS)
    return B.rounded_rect(im, int(s * 0.225))


def app_shot():
    cv = B.canvas("paper", 0)
    for i in range(14):
        y = 120 + i * 260
        B.place(cv, text_img(["Pricing", "Features", "Customers", "Docs", "Changelog", "Blog", "Sign up"][i % 7],
                             font(SFT("Bold"), 64), fill=(30, 30, 34)), 540, y, 1, 0, 1)
    tall = Image.new("RGBA", (W, H * 2), (245, 244, 240, 255))
    tall.alpha_composite(cv, (0, 0))
    tall.alpha_composite(cv, (0, H))
    return tall


DOC = ["# Role", "You are a world-class senior expert with 20+ years of experience.", "# Rules",
       "Always think step by step. Never use bullet points unless asked.",
       "Build me a landing page for my budgeting app, for students who hate spreadsheets.",
       "# Format", "Respond in markdown with H2 headings.", "# Tone", "Confident but humble."]
STOCK = [(0.00, 0.96), (0.12, 0.88), (0.25, 0.80), (0.38, 0.70), (0.50, 0.64), (0.62, 0.50), (0.75, 0.42),
         (0.88, 0.26), (1.00, 0.12)]
POST = ("Introducing Muse Wonder, our new family of frontier models with state of the art performance "
        "for personal and professional agentic work.")


def g_text_reveal(cv, k):
    for j, (txt, tw) in enumerate([("1,000", 0.4), ("10K", 0.9), ("100K", 1.4), ("1M", 1.9)]):
        B.unblur_text(cv, k, txt, tw, cy=330 + j * 190, size=120 + j * 14, color=B.RED if j == 3 else None)


def g_big_number(cv, k):
    B.big_number(cv, k - 0.2, 0, 5_000_000, cx=540, cy=560, size=150, glow=B.RED, dur=1.0)
    B.unblur_text(cv, k, "downloads in 3 weeks", 1.0, cy=720, size=56, italic=True, shine=False)


def g_line_chart(cv, k):
    B.glow_chart(cv, k, STOCK, labels={0: "$384", len(STOCK) - 1: "$88"}, box=(150, 420, 930, 900), color=B.RED,
                 dur=1.2, t0=0.2, point_times={0: 0.2, len(STOCK) - 1: 1.4})


def g_versus(cv, k):
    rows = [("Claude", 56, LG("claude-color"), 0.3), ("ChatGPT", 53, LG("openai-light"), 0.9),
            ("Meta AI", 49, LG("metaai-color"), 1.5)]
    B.versus_bars(cv, k, rows, vmax=60, title="Coding index")


def g_number_swap(cv, k):
    B.number_morph(cv, k, "600", "3", "words of prompt", "sentences", cy=600, size=300, t_switch=1.2, color_b=B.RED)


def g_prompt(cv, k):
    B.prompt_bar(cv, k, [("test my app like 5 real users", 0.3, 1.1)], enter_t=2.2, cy=640)


def g_x_post(cv, k):
    B.post(cv, k, RC("external_finkd_avatar.jpg"), "Mark Zuckerberg", "@finkd", POST,
           marks=[("state of the art", 1.0)], meta="Oct 12", stats="2.8M views", cy=620)


def g_post_chart(cv, k):
    chart = Image.open(RC("external_finkd_wonder_benchmarks.webp")).convert("RGBA")
    B.post_receipt(cv, k, RC("external_finkd_avatar.jpg"), "Mark Zuckerberg", "@finkd",
                   "Introducing Muse Wonder, our new family of frontier models.", chart, (420, 0, 1150, 244),
                   cols=[(442, 795, 1.2)], meta="Oct 12", stats="2.8M views", post_cy=480, chart_y=700)


def g_quote(cv, k):
    B.person_quote(cv, k, AVATAR, "Sully Omar", "Founder, Cutroom",
                   "Test it on five real users before you ship.", logo_path=LG("claude-color"), t_quote=0.6, cy=620)


def g_doc_cut(cv, k):
    B.delete_lines(cv, k, DOC, keep={4}, top=300, t_sel=0.4, t_del=1.5, size=28, theme="dark")


def g_doc_scroll(cv, k):
    B.scroll_doc(cv, k, DOC * 4, top=280, view_h=760, theme="dark")


def g_list(cv, k):
    B.glow_list(cv, k, ["Who is the user", "What do they want", "What good looks like"], y0=360, gap=210,
                times=[0.2, 0.9, 1.6])


def g_rewind(cv, k):
    B.rewind_counter(cv, k, 2026, 2021, settle="Oct 2021", alpha=1.0)
    front, back = tile(LG("facebook-color"), 240), tile(LG("meta-color"), 240, white=True)
    if k > 1.1:
        B.flip_tile(cv, k - 1.9, front, back, 540, 760, a=B.clamp((k - 1.1) / 0.2))


def g_flip(cv, k):
    front, back = tile(LG("facebook-color"), 300), tile(LG("meta-color"), 300, white=True)
    B.flip_tile(cv, k - 1.2, front, back, 540, 620)


def g_dots(cv, k):
    src, tg, tc = (270, 640), (800, 470), (800, 810)
    B.focus_in(cv, k, tile(LG("openai-light"), 220, white=True), *src, shadow=(0, 20, 26, 200))
    B.dot_stream(cv, k - 0.5, src, [(tg, 0.2), (tc, 1.0)])
    for path, kk, pos in ((LG("claude-color"), 0.7, tg), (LG("metaai-color"), 1.5, tc)):
        if k > kk:
            B.focus_in(cv, k - kk, B._badge(path, 190), *pos, shadow=(0, 18, 24, 200))


def g_logo(cv, k):
    B.logo_burst(cv, k, LG("claude-color"), cy=620)


def g_phone(cv, k):
    B.phone(cv, k, APP_PATH, cy=760, scale=0.85, rot=0)


def g_section_title(cv, k):
    B.title(cv, k, [("Why templates", False), ("fail", True)], cy=600, size=84)


def g_title_box(cv, k):
    B.title_box(cv, k - 0.1, "Claude can now test your app for you", emoji="😮", cy=520)


def g_sticky(cv, k):
    B.sticky_notes(cv, k, [B.Note("Ask for one thing", 0.2, 330, 520, rot=-4),
                           B.Note("Show an example", 0.9, 740, 760, rot=3)], theme="dark")


def g_sticker(cv, k):
    B.cutout(cv, k, AVATAR, name="Sully Omar", sub="Founder", cy=600, size=440)


def g_marker(cv, k):
    im = text_img("five real users", font(SFT("Bold"), 96), fill=(240, 240, 240))
    B.place(cv, im, 540, 620, 1, 0, 1)
    w, h = im.width - 2 * im.pad, im.height - 2 * im.pad
    B.marker_circle(cv, k - 0.5, (540 - w / 2, 620 - h / 2, 540 + w / 2, 620 + h / 2))


def g_focus(cv, k):
    t = k % 1.6
    B.focus_in(cv, t - 0.2, tile(LG("claude-color"), 320), 540, 620, d=0.35)


def g_push(cv, k):
    B.focus_in(cv, 1.0, text_img("Never frozen", font(SFT("Bold"), 110), fill=(240, 240, 240)), 540, 620)


def g_ripple(cv, k):
    B.focus_in(cv, 1.0, tile(LG("claude-color"), 260), 540, 620)
    t = k % 1.2
    if t > 0.3:
        B.ripple(cv, t - 0.3, 540, 620, r0=80, r1=400)


def g_label(cv, k):
    B.focus_in(cv, 1.0, tile(LG("claude-color"), 280), 540, 560)
    B.tag(cv, k - 0.6, "First Five · Claude skill", 540, 820, size=40)


def g_tier_list(cv, k):
    B.tier_list(cv, k, [(0, LG("claude-color"), 0.4), (0, LG("claudecode-color"), 0.9), (1, LG("openai-light"), 1.4),
                        (2, LG("metaai-color"), 1.9), (3, LG("muse-app-icon"), 2.4)],
                labels="SABCD", x0=90, y0=150, w=900, rh=150)


def g_price_tag(cv, k):
    B.focus_in(cv, k, tile(LG("muse-app-icon"), 420), 540, 560, shadow=(0, 20, 34, 180))
    B.price_tag(cv, k - 0.9, "$19.99/mo", 640, 860)


def g_relay(cv, k):
    B.relay_line(cv, k, [("Record", 0.3), ("Cut", 0.9), ("Review", 1.5), ("Ship", 2.1)], y=620, x0=150, x1=930)


def g_score(cv, k):
    B.score_ring(cv, k - 0.1, 92, cx=540, cy=560, r=230, label="kept using it")


def g_folders(cv, k):
    B.folder_tree(cv, k, "cutroom/", [("skills", 0.6), ("library", 1.0), ("videos", 1.4)], cy=330)


def g_value_pair(cv, k):
    B.value_pair(cv, k, ("$", 0), ("$", 4726), label="made in month one", chapter="01  Contrast", cy=600)


def g_checklist(cv, k):
    panel = C.checklist_panel(k + 1.0, 940, 1140, "Before you post", [(1.2, "Hook in the first second"),
                              (1.7, "Cut every pause"), (2.2, "Captions on"), (2.7, "One idea per beat")], y0=260)
    cv.alpha_composite(panel, (70, 120))


def l_step(cv, k, face):
    Bx.step(cv, k, 1, "Cut the pauses", cy=190)
    Bx.prompt(cv, k - 0.4, "Cut every pause longer than half a second", cy=600, t_type=0.2, cps=34,
              file="raw.mp4", t_file=0.1, t_check=1.8)


def l_hook(cv, k, face):
    Bx.hook(cv, k, [[("Claude edited", False)], [("this", False), ("entire", True)], [("video", False)]],
            sub="no timeline, no premiere")


def l_prompt(cv, k, face):
    Bx.prompt(cv, k, "Cut the silences and add bold captions", file="raw.mp4", t_file=0.2, t_check=1.6,
              t_send=2.3, cps=24)


def l_check(cv, k, face):
    Bx.checklist(cv, k, [("Cut the pauses", 0.5), ("Captions on", 1.1), ("Music under", 1.7)],
                 title="Before you post")


def l_count(cv, k, face):
    Bx.counter(cv, k, 1200, 412000, sub="Posted Tuesday")


def l_folder(cv, k, face):
    Bx.folder(cv, k, "my-video/", [("raw.mp4", 0.4), ("storyboard.md", 0.8), ("captions/", 1.2),
                                    ("final.mp4", 1.6)])


def l_list(cv, k, face):
    Bx.numbered(cv, k, [("Hook in one line", 0.3), ("Cut every pause", 0.9), ("Captions on", 1.5)])


def l_bars(cv, k, face):
    Bx.bars(cv, k, [("#1", 197000), ("#2", 140000), ("#3", 123000), ("#4", 82000), ("#5", 48000),
                    ("#6", 33000), ("#7", 18000)], "My top reels by", accent_word="views")


def l_compare(cv, k, face):
    Bx.compare(cv, k, STILLS)


def l_cta(cv, k, face):
    Bx.cta(cv, k)


def s_assistant(cv, k, face):
    Sc.assistant(cv, k, "Cut the pauses and add captions", "Done. Cut 14 pauses and added captions in "
                 "your style.", cps=34)


def s_terminal(cv, k, face):
    Sc.terminal(cv, k, [("cmd", "cut the pauses in raw.mp4", 0.15), ("out", "found 14 pauses, 38s", 1.0),
                        ("edit", "cut.mp4", 1.35), ("edit", "captions.srt", 1.6), ("ok", "Ready to review", 2.0)])


def s_notes(cv, k, face):
    Sc.notes(cv, k, "Hooks to film", [("- I edit every video in one prompt", 0.2), ("- 3 hours to 3 minutes", 0.9),
                                       ("- Stop editing your own videos", 1.6)])


def s_texts(cv, k, face):
    Sc.texts(cv, k, "Sam", [(False, "how do you post every day??", 0.5), (True, "Claude edits them", 1.3),
                            (False, "wait what", 2.2)])


def s_post(cv, k, face):
    Sc.post(cv, k, "Maya Reyes", "@mayamakes", "I haven't opened an editor in a month. Claude cuts every video now.",
            stats=(("Replies", 0, 214), ("Reposts", 0, 1240), ("Likes", 0, 12400)))


def s_analytics(cv, k, face):
    Sc.analytics(cv, k, 1284000, [3, 4, 3, 5, 6, 5, 8, 9, 12, 11, 16, 22, 30, 41])


def s_inbox(cv, k, face):
    Sc.inbox(cv, k, [("Mia", "Your edit is ready", "Cut 14 pauses and added captions to raw.mp4", 0.1),
                     ("Studio", "Brand deal: 3 reels", "Loved the last video, want to work together?", 0.9),
                     ("Cutroom", "New note on take 2", "Tighten the hook at 0:03", 1.7)])


def s_browser(cv, k, face):
    Sc.browser(cv, k, "example.com/editing-with-ai", "How creators edit faster",
               ["Most creators spend hours on every short.", "The ones posting daily hand the cut to an agent and "
                "only review the result.", "Then they spend that time filming."], mark=(1, 0), t_mark=1.5)


BASICS = {"step-header": l_step, "hook-card": l_hook, "prompt-card": l_prompt, "check-card": l_check,
          "view-count": l_count, "folder-card": l_folder, "list-card": l_list, "bar-chart": l_bars,
          "compare-row": l_compare, "comment-cta": l_cta, "chat-app": s_assistant, "terminal-app": s_terminal,
          "notes-app": s_notes, "text-thread": s_texts, "social-post": s_post, "analytics-app": s_analytics,
          "inbox-app": s_inbox, "browser-page": s_browser}


CLIPS, WIDE = [], []


def page(k):
    cv = Image.new("RGBA", (W, H), (40, 40, 44, 255))
    Sc.browser(cv, k, "example.com/editing-with-ai", "How creators edit faster",
               ["Most creators spend hours on every short.", "The ones posting daily hand the cut to an agent."],
               mark=(1, 0), t_mark=1.2, cx=W / 2, cy=H / 2, w=940, h=1100)
    return cv


def reels(k, n, offset=0):
    return [CLIPS[(i + offset) % len(CLIPS)] for i in range(n)]


def wide(k, i=0):
    return WIDE[i % len(WIDE)]


def head(k, t, face):
    return FRAMING.face(face, k).convert("RGBA")


def v_grid(k, t, face, mask):
    cv = B.canvas("dark", 0)
    B.image_grid(cv, k, reels(k, 4), gap=8)
    cap.draw(cv, t, SPANS, "full")
    return cv


def v_wall(k, t, face, mask):
    cv = head(k, t, face) if k < 0.6 else V.swap(face, mask, k - 0.6, tiles=reels(k, 6))
    cap.draw(cv, t, SPANS, "face")
    return cv


def v_landscape(k, t, face, mask):
    cv = head(k, t, face) if k < 0.6 else V.inset(wide(k, 1), k - 0.6, w=1040, cy=600, via="@source", ratio=9 / 16)
    cap.draw(cv, t, SPANS, "full" if k >= 0.6 else "face")
    return cv


def v_split(k, t, face, mask):
    cv = B.canvas("dark", int(k * FPS))
    STACK.draw(cv, face, mask, k)
    B.push_layer(cv, V.cover(wide(k, 2), W, 960).convert("RGBA"), k, DUR, amount=0.0, cx=540, cy=480)
    STACK.draw(cv, face, mask, k)
    cap.draw(cv, t, SPANS, "split")
    return cv


def v_screen(k, t, face, mask):
    return V.screen(page(k), k, box=SCREEN_BOX, box_k=k - 1.2, zoom_k=k - 2.0)


def v_float(k, t, face, mask):
    cv = head(k, t, face)
    V.floating_clip(cv, k - 0.25, wide(k), cx=540, cy=310, w=560, via="via @source")
    cap.draw(cv, t, SPANS, "face")
    return cv


def v_fan(k, t, face, mask):
    cv = head(k, t, face)
    V.fan(cv, k - 0.25, reels(k, 3, 1), cy=390, w=240)
    cap.draw(cv, t, SPANS, "face")
    return cv


def v_depth(k, t, face, mask):
    cv = face.convert("RGBA").copy()
    V.depth(cv, k - 0.2, reels(k, 4), cutout=V.person(face, mask))
    cap.draw(cv, t, SPANS, "face")
    return cv


def v_fly(k, t, face, mask):
    cv = face.convert("RGBA").copy()
    V.fly(cv, k - 0.2, reels(k, 4, 2), V.person(face, mask), head=(540, 720))
    cap.draw(cv, t, SPANS, "face")
    return cv


SCREEN_BOX = (190, 905, 890, 1010)
VIDEO = {"video-grid": v_grid, "clip-wall": v_wall, "landscape-clip": v_landscape, "clip-split": v_split,
         "screen-zoom": v_screen, "floating-clip": v_float, "clip-fan": v_fan, "clips-around": v_depth,
         "clips-fly-out": v_fly}


def basics_frame(cid, k, face):
    cv = Bx.canvas()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    BASICS[cid](lay, k, face)
    B.push_layer(cv, lay, k, DUR, amount=0.03, cx=540, cy=520)
    Bx.face_panel(cv, face)
    Bx.caption(cv, k, LOCAL_WORDS)
    return cv


def f_page_split(k, t, face, mask):
    cv = Bx.canvas()
    Bx.transcript(cv, k, [("0.44s", "This", 0.3), ("0.70s", "one", 0.5), ("0.92s", "trick", 0.7),
                          ("1.44s", "saved", 0.9), ("1.74s", "me", 1.1), ("2.06s", "hours", 1.3)], t_done=1.6)
    Bx.face_panel(cv, face)
    Bx.caption(cv, k, LOCAL_WORDS)
    return cv


def f_slash(k, t, face, mask):
    cv = Bx.canvas()
    result = FRAMING.face(face, k).convert("RGBA")
    if k >= 1.6:
        cap.draw(result, t, SPANS, "face")
    Bx.chat(cv, k, "/captions bold", result, hint="Bold word-by-word captions", t_send=1.25, t_result=1.55)
    return cv


def f_prompt_result(k, t, face, mask):
    cv = Bx.canvas()
    if k < 1.5:
        place_label(cv, "Write this", Bx.MUTED)
        Bx.prompt(cv, k, "Cut the pauses, punch in on every point, bold captions", cy=560, cps=40,
                  t_send=1.2, out=1.4)
        Bx.face_panel(cv, face)
    else:
        q = Bx.expo((k - 1.5) / 0.35)
        place_label(cv, "Get this", Bx.ACCENT)
        top = int(1150 - (1150 - 330) * q)
        res = FRAMING.face(face, k, punch=1.15).convert("RGBA")
        cap.draw(res, t, SPANS, "face")
        Bx.face_panel(cv, res, box=(40, top, 1040, 1880), radius=28)
    return cv


def place_label(cv, txt, col):
    B.place(cv, Bx.label(txt, 40, col, 600), 540, 230)


def tiles(n, offset=0):
    paths = sorted(os.listdir(a.tiles))
    return [Image.open(os.path.join(a.tiles, paths[(i + offset) % len(paths)])) for i in range(n)]


def f_ranking(k, t, face, mask):
    cv = graphic_frame("tier-list", k, face, mask)
    cap.draw(cv, t, SPANS, "stack")
    return cv


def f_explainer(k, t, face, mask):
    cv = graphic_frame("relay-line", k, face, mask)
    cap.draw(cv, t, SPANS, "stack")
    return cv


def f_depth(k, t, face, mask):
    cv = B.canvas("dark", 0)
    B.ui_wall(cv, k, TILES, cols=3, w=330, speed=60, top=-120)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    cv.alpha_composite(shade)
    B.person_over(cv, face, mask)
    B.views_card(cv, k - 0.5, 1240512, "Sully Omar", "38.2K subscribers", avatar=AVATAR, cy=1420)
    return cv


def f_cutout(k, t, face, mask):
    if k >= DUR / 2:
        return f_depth(k - DUR / 2, t, face, mask)
    cv = B.canvas("dark", 0)
    B.image_grid(cv, k, TILES[3:7], gap=8)
    cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 70)))
    B.person_over(cv, face, mask, scale=0.72)
    cap.draw(cv, t, SPANS, "face")
    return cv


def f_product(k, t, face, mask):
    cv = B.canvas("dark", int(k * FPS))
    STACK.draw(cv, face, mask, k)
    top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top.paste(B.canvas("paper", 0).crop((0, 0, W, 960)), (0, 0))
    B.focus_in(top, k, tile(LG("muse-app-icon"), 360), 540, 400, shadow=(0, 20, 34, 120))
    B.price_tag(top, k - 0.8, "$19.99/mo", 650, 640)
    B.push_layer(cv, top, k, DUR, amount=0.03, cx=540, cy=480)
    STACK.draw(cv, face, mask, k)
    cap.draw(cv, t, SPANS, "split")
    return cv


FORMATS = {"ranking": f_ranking, "explainer-panel": f_explainer, "cutout": f_cutout,
           "product-split": f_product, "page-split": f_page_split, "slash-demo": f_slash,
           "prompt-to-result": f_prompt_result}


GRAPHICS = {
    "text-reveal": g_text_reveal, "big-number": g_big_number, "line-chart": g_line_chart, "versus-bars": g_versus,
    "number-swap": g_number_swap, "prompt-box": g_prompt, "x-post": g_x_post, "post-chart": g_post_chart,
    "quote-card": g_quote, "doc-cut": g_doc_cut, "doc-scroll": g_doc_scroll, "numbered-list": g_list,
    "year-rewind": g_rewind, "card-flip": g_flip, "dot-stream": g_dots, "logo-reveal": g_logo, "phone-scroll": g_phone,
    "section-title": g_section_title, "title-box": g_title_box, "sticky-notes": g_sticky, "sticker": g_sticker,
    "marker": g_marker, "focus-pull": g_focus, "slow-push": g_push, "ripple": g_ripple, "label": g_label,
    "tier-list": g_tier_list, "price-tag": g_price_tag, "relay-line": g_relay, "score-ring": g_score,
    "folder-tree": g_folders, "value-pair": g_value_pair, "checklist": g_checklist,
}
PUSHED = {"slow-push": 0.12}


def graphic_frame(cid, k, face, mask):
    cv = B.canvas("dark", int(k * FPS))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    GRAPHICS[cid](lay, k)
    B.push_layer(cv, lay, k, DUR, amount=PUSHED.get(cid, 0.04), cx=540, cy=660)
    B.face_inset(cv, face, mask, FACE_BOX, src_y=SRC_Y, theme="dark")
    return cv


def layout_frame(cid, k, t, face, mask):
    if cid == "talking-head":
        cv = FRAMING.face(face, k).convert("RGBA")
        cap.draw(cv, t, SPANS, "face")
    elif cid == "punch-in":
        cv = FRAMING.face(face, k, punch=1.4).convert("RGBA")
        cap.draw(cv, t, SPANS, "face")
    elif cid == "face-inset":
        cv = graphic_frame("big-number", k, face, mask)
        cap.draw(cv, t, SPANS, "stack")
    elif cid == "split":
        cv = B.canvas("dark", int(k * FPS))
        STACK.draw(cv, face, mask, k)
        B.push_layer(cv, APP.crop((0, int(k * 120), W, int(k * 120) + 960)).resize((W, 960)), k, DUR, amount=0.0,
                     cx=540, cy=480)
        STACK.draw(cv, face, mask, k)
        cap.draw(cv, t, SPANS, "split")
    else:
        cv = B.canvas("dark", 0)
        B.push_layer(cv, APP.crop((0, int(k * 200), W, int(k * 200) + H)), k, DUR, amount=0.04)
        cap.draw(cv, t, SPANS, "full")
    return cv


def captions_frame(cid, k, t, face):
    cv = FRAMING.face(face, k).convert("RGBA")
    spans = SPANS if cid == "kallaway" else MONO_SPANS if cid == "rpn" else cap.chunk(WORDS, cid)
    cap.draw(cv, t, spans, "face", style=cid)
    return cv


def render(entry):
    cid, kind = entry["id"], entry["kind"]
    start = a.start
    face_r = Reader(a.face, 1080, 1920, start=start)
    mask_r = Reader(a.mask, 540, 960, start=start)
    out = os.path.join(a.out, f"{cid}.mp4")
    n = int(DUR * FPS)
    strip = []
    clip_paths = sorted(os.path.join(a.clips, f) for f in os.listdir(a.clips) if f.endswith(".mp4")) if cid in VIDEO else []
    tall = [Reader(f, 540, 960) for f in clip_paths if os.path.basename(f).startswith("p_")]
    flat = [Reader(f, 1280, 720) for f in clip_paths if os.path.basename(f).startswith("l_")]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "scale=540:960:flags=lanczos",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "28", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", "-an", out], stdin=subprocess.PIPE)
    for i in range(n):
        k = i / FPS
        t = start + k
        face = face_r.next()
        mask = mask_r.next().convert("L")
        if cid in VIDEO:
            CLIPS[:] = [r.next() for r in tall]
            WIDE[:] = [r.next() for r in flat]
            cv = VIDEO[cid](k, t, face, mask)
        elif cid in FORMATS:
            cv = FORMATS[cid](k, t, face, mask)
        elif cid in BASICS:
            cv = basics_frame(cid, k, face)
        elif kind == "layout":
            cv = layout_frame(cid, k, t, face, mask)
        elif kind == "captions":
            cv = captions_frame(cid, k, t, face)
        else:
            cv = graphic_frame(cid, k, face, mask)
        ff.stdin.write(cv.convert("RGB").tobytes())
        if a.frames and i in STRIP:
            strip.append(cv.convert("RGB").resize((270, 480), Image.LANCZOS))
    ff.stdin.close()
    ff.wait()
    face_r.close()
    mask_r.close()
    for r in tall + flat:
        r.close()
    if strip:
        sheet = Image.new("RGB", (270 * len(strip) + 8 * (len(strip) - 1), 480), (0, 0, 0))
        for j, im in enumerate(strip):
            sheet.paste(im, (j * 278, 0))
        sheet.save(os.path.join(a.frames, f"{cid}.jpg"), quality=82)
    print(cid, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--face", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--words", required=True)
    ap.add_argument("--logos", default=os.path.expanduser("~/Cutroom/account/logos"))
    ap.add_argument("--receipts", default="")
    ap.add_argument("--tiles", default="")
    ap.add_argument("--clips", default="")
    ap.add_argument("--frames", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--start", type=float, default=9.6)
    ap.add_argument("--emph", default="First Five,real users")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.frames:
        os.makedirs(a.frames, exist_ok=True)
    STRIP = {int(DUR * FPS * f) for f in (0.15, 0.4, 0.65, 0.95)}
    TILES = tiles(12) if a.tiles else []
    words = cap.join_phrases(cap.load_words(a.words), a.emph.split(","))
    WORDS = words
    SPANS, MONO_SPANS = cap.chunk(words, "kallaway"), cap.chunk(words, "rpn")
    LOCAL_WORDS = [(w["w"], w["s"] - a.start) for w in cap.load_words(a.words)]
    STACK = L.Stack(FRAMING)
    AVATAR = os.path.join(tempfile.mkdtemp(), "avatar.png")
    first = Reader(a.face, 1080, 1920, start=a.start)
    first.next().crop((360, 560, 760, 960)).save(AVATAR)
    STILLS = []
    for skip in (0, 30, 60):
        for _ in range(skip):
            first.next()
        STILLS.append(first.next().copy())
    STILLS[0] = ImageOps.grayscale(STILLS[0]).convert("RGB").point(lambda v: int(v * 0.7))
    STILLS[2] = STILLS[2].crop((140, 250, 940, 1673))
    first.close()
    APP = app_shot()
    APP_PATH = os.path.join(tempfile.mkdtemp(), "app.png")
    APP.convert("RGB").save(APP_PATH)
    catalog = json.load(open(os.path.join(HERE, "catalog.json")))
    only = set(filter(None, a.only.split(",")))
    for entry in catalog["components"]:
        if not only or entry["id"] in only:
            render(entry)
