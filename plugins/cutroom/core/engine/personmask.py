"""Person alpha matte video for Linux (the cloud editor). Same contract as personmask.swift.

Usage: python3 personmask.py <in.mp4> <out_w> <out_h>  > raw gray8 frames on stdout
Pipe into: ffmpeg -f rawvideo -pix_fmt gray -s WxH -r 30 -i - -c:v libx264 -crf 8 -pix_fmt yuv420p mask.mp4

Robust Video Matting: a real alpha matte with hair detail, and recurrent, so the edge stays
steady from frame to frame.
- MATTE_URL + MATTE_TOKEN set: runs on the cutroom-matte GPU service (tools/matte/modal_matte.py),
  ~30s for a 60s reel. The video is shrunk to out size before upload.
- Otherwise: ONNX on CPU (minutes), model from PERSONMASK_MODEL (default: the E2B template copy).
"""

import os
import subprocess
import sys
import tempfile

import numpy as np

MODEL = os.environ.get("PERSONMASK_MODEL", "/opt/models/rvm_resnet50_fp32.onnx")


def main() -> None:
    src, ow, oh = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    service = matte_service(src)
    if service:
        remote(src, ow, oh, *service)
    else:
        local(src, ow, oh)


def matte_service(src: str):
    if os.environ.get("MATTE_URL") and os.environ.get("MATTE_TOKEN"):
        return os.environ["MATTE_URL"], os.environ["MATTE_TOKEN"]
    from cutroom import account
    site, key = account.site(), account.key()
    if not site or not key:
        return None
    import json

    seconds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                             capture_output=True, text=True).stdout.strip() or "0"
    with tempfile.TemporaryDirectory() as td:
        cfg = f"{td}/h"
        with open(cfg, "w") as f:
            f.write(f'header = "Authorization: Bearer {key}"\n')
        out = subprocess.run(["curl", "-s", "-m", "30", "-K", cfg, "-X", "POST", f"{site}/matte?seconds={seconds}"],
                             capture_output=True, text=True).stdout
    try:
        res = json.loads(out)
        return res["url"], res["token"]
    except (ValueError, KeyError):
        print("Cutroom matte service unavailable, using CPU", file=sys.stderr)
        return None


def remote(src: str, ow: int, oh: int, matte_url: str, matte_token: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        small, cfg, mask = f"{td}/small.mp4", f"{td}/h", f"{td}/mask.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={ow}:{oh}", "-an",
                        "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", small], check=True)
        # The token goes through a curl config file so it never shows up in the process list.
        with open(cfg, "w") as f:
            f.write(f'header = "Authorization: Bearer {matte_token}"\n')
        url = f"{matte_url.rstrip('/')}/?w={ow}&h={oh}"
        code = subprocess.check_output(["curl", "-s", "-m", "900", "-K", cfg, "-X", "POST", "--data-binary",
                                        f"@{small}", url, "-o", mask, "-w", "%{http_code}"]).decode()
        if code != "200":
            print(f"matte service returned HTTP {code}, falling back to CPU", file=sys.stderr)
            return local(src, ow, oh)
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", mask, "-vf", f"scale={ow}:{oh}",
                                       "-f", "rawvideo", "-pix_fmt", "gray", "-"])
        sys.stdout.buffer.write(raw)
        print(f"done {len(raw) // (ow * oh)} frames (GPU)", file=sys.stderr)


def local(src: str, ow: int, oh: int) -> None:
    import onnxruntime as ort

    # RVM works on a downsampled copy internally; ~512px on the long side suits a talking head.
    ratio = np.array([min(1.0, 512 / max(ow, oh))], np.float32)
    session = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    decode = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={ow}:{oh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    state = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    frame_bytes = ow * oh * 3
    out = sys.stdout.buffer
    n = 0
    while True:
        raw = decode.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            break
        rgb = np.frombuffer(raw, np.uint8).reshape(oh, ow, 3)
        x = (rgb.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        _, pha, *state = session.run(
            None,
            {"src": x, "r1i": state[0], "r2i": state[1], "r3i": state[2], "r4i": state[3], "downsample_ratio": ratio},
        )
        out.write((np.clip(pha[0, 0], 0, 1) * 255).astype(np.uint8).tobytes())
        n += 1
        if n % 300 == 0:
            print(f"mask frame {n}", file=sys.stderr)
    decode.wait()
    print(f"done {n} frames", file=sys.stderr)


if __name__ == "__main__":
    main()
