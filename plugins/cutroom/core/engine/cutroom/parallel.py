"""Parallel render: split the frame range into chunks, render each chunk in its own forked process
(own ffmpeg readers seeked to the chunk start, own x264 encoder), then stitch with concat -c copy
and mux the audio. Pillow compositing is single-threaded, so this is where the speed-up comes from
(~3 fps on one core -> roughly x cores).

Rules for a render script to be chunk-safe:
- compose(t, ...) must depend only on t (no state carried from frame to frame). Module-level RNG is fine.
- Anything that reads a video sequentially must open its reader seeked to the frame it starts at
  (see `clip_offset` for B-roll clips that start mid-timeline).
"""
import multiprocessing as mp, os, shutil, subprocess, sys, tempfile, time
from .core import FPS, W, H

def clip_offset(t, a, lead=0.04, fps=FPS):
    """Source offset for a clip shown from `a` (reader opened at the first frame >= a - lead).
    Sequential render opens at that first frame, so offset = t - first_frame_t; a chunk starting
    mid-clip gets the same value."""
    first = -(-round((a - lead) * fps * 1e6) // 1_000_000) / fps   # ceil without float drift
    return max(0.0, t - first)

BITRATE = "10M"   # plain IG/TikTok upload bitrate, 10,000 kbps. One file per version, no _mobile copy.

def _encoder(path, crf, fps, threads):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-b:v", BITRATE,
           "-maxrate", BITRATE, "-bufsize", "20M", "-pix_fmt", "yuv420p", "-threads", str(threads), path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)

def _worker(k, i0, i1, make_frame, open_sources, path, crf, fps, threads, done):
    srcs = open_sources(i0 / fps)
    enc = _encoder(path, crf, fps, threads)
    for i in range(i0, i1):
        enc.stdin.write(make_frame(i, srcs).convert("RGB").tobytes())
        with done.get_lock(): done.value += 1
    enc.stdin.close(); enc.wait()
    for s in (srcs if isinstance(srcs, (list, tuple)) else [srcs]):
        if hasattr(s, "close"): s.close()
    if enc.returncode: sys.exit(enc.returncode)

def render(out, n, make_frame, open_sources, audio=None, workers=None, crf=16, fps=FPS):
    """make_frame(i, srcs) -> PIL image for frame i.  open_sources(t0) -> readers seeked to t0
    (a tuple of core.Reader is typical; anything with .close() is closed at the end)."""
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    workers = min(workers, n)
    ctx = mp.get_context("fork")
    tmp = tempfile.mkdtemp(prefix="cutroom_chunks_", dir=os.path.dirname(os.path.abspath(out)))
    bounds = [n * k // workers for k in range(workers + 1)]
    done, t_start = ctx.Value("i", 0), time.time()
    procs = []
    for k in range(workers):
        p = ctx.Process(target=_worker, args=(k, bounds[k], bounds[k + 1], make_frame, open_sources,
                                              os.path.join(tmp, f"c{k:03d}.mp4"), crf, fps, 2, done))
        p.start(); procs.append(p)
    last = 0
    while any(p.is_alive() for p in procs):
        time.sleep(1)
        if time.time() - last >= 10:
            last = time.time(); el = last - t_start; d = done.value
            eta = (n - d) * el / d if d else 0
            print(f"frame {d}/{n}  {d / el:.1f} fps  eta {eta:.0f}s", flush=True)
    for p in procs: p.join()
    if any(p.exitcode for p in procs):
        raise RuntimeError(f"chunk worker failed; chunks kept in {tmp}")
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for k in range(workers): f.write(f"file 'c{k:03d}.mp4'\n")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if audio: cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    cmd += ["-c:v", "copy", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    el = time.time() - t_start
    print(f"done {out}  {n} frames in {el:.0f}s ({n / el:.1f} fps, {workers} workers)", flush=True)
