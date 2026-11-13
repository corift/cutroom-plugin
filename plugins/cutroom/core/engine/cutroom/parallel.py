"""Parallel render: split the frame range into short chunks and render them on every core, each chunk
in its own forked process (own ffmpeg readers seeked to the chunk start, own encoder), then stitch with
concat -c copy and mux the audio. Pillow compositing is single-threaded, so this is where the speed-up
comes from. Chunks are short and handed out as cores free up, so a heavy stretch of the edit never
leaves the other cores idle. Encoding runs on the Mac's media engine when there is one (core.h264).

Rules for a render script to be chunk-safe:
- compose(t, ...) must depend only on t (no state carried from frame to frame). Module-level RNG is fine.
- Anything that reads a video sequentially must open its reader seeked to the frame it starts at
  (see `clip_offset` for B-roll clips that start mid-timeline).
"""
import multiprocessing as mp, os, shutil, subprocess, sys, tempfile, time
from .core import FPS, W, H, BITRATE, h264, hardware_encoder

CHUNK_SECONDS = 2

def clip_offset(t, a, lead=0.04, fps=FPS):
    """Source offset for a clip shown from `a` (reader opened at the first frame >= a - lead).
    Sequential render opens at that first frame, so offset = t - first_frame_t; a chunk starting
    mid-clip gets the same value."""
    first = -(-round((a - lead) * fps * 1e6) // 1_000_000) / fps   # ceil without float drift
    return max(0.0, t - first)

def _encoder(path, fps, threads, size):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
           "-r", str(fps), "-i", "-"] + h264(threads, size) + [path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)

def _worker(i0, i1, make_frame, open_sources, path, fps, threads, done, size):
    srcs = open_sources(i0 / fps)
    enc = _encoder(path, fps, threads, size)
    for i in range(i0, i1):
        enc.stdin.write(make_frame(i, srcs).convert("RGB").tobytes())
        with done.get_lock(): done.value += 1
    enc.stdin.close(); enc.wait()
    for s in (srcs if isinstance(srcs, (list, tuple)) else [srcs]):
        if hasattr(s, "close"): s.close()
    sys.stdout.flush()
    os._exit(enc.returncode)

def _bounds(n, workers, fps):
    size = max(1, min(int(CHUNK_SECONDS * fps), -(-n // workers)))
    return [(i, min(n, i + size)) for i in range(0, n, size)]

def render(out, n, make_frame, open_sources, audio=None, workers=None, crf=16, fps=FPS, size=(W, H)):
    """make_frame(i, srcs) -> PIL image for frame i.  open_sources(t0) -> readers seeked to t0
    (a tuple of core.Reader is typical; anything with .close() is closed at the end).
    size is the frame size make_frame returns; the bitrate scales with it."""
    hardware = hardware_encoder()
    cores = os.cpu_count() or 4
    workers = min(workers or (cores if hardware else max(1, cores - 2)), n)
    ctx = mp.get_context("fork")
    tmp = tempfile.mkdtemp(prefix="cutroom_chunks_", dir=os.path.dirname(os.path.abspath(out)))
    chunks = _bounds(n, workers, fps)
    paths = [os.path.join(tmp, f"c{k:04d}.mp4") for k in range(len(chunks))]
    done, t_start = ctx.Value("i", 0), time.time()
    waiting, running, failed, last = list(enumerate(chunks)), [], False, t_start
    while (waiting and not failed) or running:
        while waiting and not failed and len(running) < workers:
            k, (i0, i1) = waiting.pop(0)
            p = ctx.Process(target=_worker, args=(i0, i1, make_frame, open_sources, paths[k], fps, 2, done, size))
            p.start(); running.append(p)
        time.sleep(0.02)
        for p in [p for p in running if not p.is_alive()]:
            p.join(); running.remove(p)
            failed = failed or p.exitcode != 0
        if time.time() - last >= 5:
            last = time.time(); el = last - t_start; d = done.value
            print(f"frame {d}/{n}  {d / el:.1f} fps  eta {(n - d) * el / d if d else 0:.0f}s", flush=True)
    if failed:
        raise RuntimeError(f"chunk worker failed; chunks kept in {tmp}")
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for path in paths: f.write(f"file '{os.path.basename(path)}'\n")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if audio: cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    cmd += ["-c:v", "copy", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    el = time.time() - t_start
    print(f"done {out}  {n} frames in {el:.1f}s ({n / el:.1f} fps, {workers} workers, {'hardware' if hardware else 'x264'} encoder)", flush=True)
