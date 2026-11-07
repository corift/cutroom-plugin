"""Render shots from an HTML page to 1080x1920 30fps video.

  render_html.py PAGE.html OUTDIR shot:dur ... [--alpha]

The page is 432x768 (rendered at 2.5x) and defines window.render(shot, t, dur), which draws
frame t of that shot. Without --alpha, each shot becomes OUTDIR/ui-<shot>.mp4 (full-screen
UI cutaways). With --alpha, the background is transparent and each shot becomes
OUTDIR/ov-<shot>.mov (ProRes 4444) for assemble's "overlays".
"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

FPS = 30
args = [a for a in sys.argv[1:] if a != "--alpha"]
alpha = "--alpha" in sys.argv
page_url, out_dir = Path(args[0]).resolve().as_uri(), Path(args[1])
out_dir.mkdir(parents=True, exist_ok=True)
codec = (["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"] if alpha
         else ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16"])

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 432, "height": 768}, device_scale_factor=2.5)
    page.goto(page_url)
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    for spec in args[2:]:
        shot, dur = spec.split(":")
        out = out_dir / (f"ov-{shot}.mov" if alpha else f"ui-{shot}.mp4")
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                               "-i", "-", *codec, str(out)], stdin=subprocess.PIPE)
        for i in range(round(float(dur) * FPS)):
            page.evaluate(f"render('{shot}', {i / FPS}, {dur})")
            ff.stdin.write(page.screenshot(type="png", omit_background=alpha))
        ff.stdin.close()
        ff.wait()
        print(out)
    browser.close()
