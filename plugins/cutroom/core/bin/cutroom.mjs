#!/usr/bin/env node
/*
 * cutroom: move files between this machine and Cutroom (R2 + Convex), and post work for review.
 * Runs the same on a Mac (the desktop app, or Claude Code in a terminal) and in the cloud sandbox.
 * Paths are Cutroom paths ("projects/<project>/videos/<name>", "account") or folders on disk.
 * A project can live in any folder: `cutroom link <project>` run in it writes .cutroom/project.json
 * there, so the folder keeps its link when it moves or is cloned (see folders.mjs).
 * No dependencies: Node 18+ only.
 *
 *   cutroom push "projects/shorts/videos/2026-10-11-gemini-argon" [--only edit/] [--include-media]
 *   cutroom pull "projects/shorts/videos/2026-10-11-gemini-argon"     (or any folder: "projects/shorts", "account")
 *   cutroom publish storyboard "<video folder>" edit/base_v1.mp4
 *   cutroom publish render "<video folder>" edit/gemini_argon_reel_v2.mp4 [--wait]
 *   cutroom publish render "<video folder>" edit/trials_v1.mp4 edit/buy_now_v1.mp4   # variations of one video
 *   cutroom final "<video folder>" [edit/trials_v3.mp4 …]   # default: every approved cut
 *   cutroom wait "<video folder>" [--kind render|storyboard]
 *   cutroom watch ["<video folder>"]      # one JSON line per review event, for Monitor
 *   cutroom link <project> [<folder>] [--videos "short form"]   # this folder (default: here) is the project
 *   cutroom link                          # show where each project lives
 *   cutroom unlink <project>              # forget this Mac's folder for the project
 *
 * (Run it as `node "$CUTROOM_CORE/bin/cutroom.mjs" …` when `cutroom` isn't on PATH.)
 *
 * --wait / wait: blocks until the user presses Send to Claude or Approve on that video in
 * Cutroom, prints what to do next (plus a JSON line) and exits. In Claude Code, run it in the
 * background: the exit wakes the session with the notes.
 *
 * Auth: CUTROOM_KEY (set for chats in the app), else the device key the desktop app saved in
 * $CUTROOM_HOME/.cutroom/credentials.json. CONVEX_URL comes from the same places. A chat also
 * sets CUTROOM_CHAT_ID, so published reviews route the user's notes back to that chat.
 * Text files are stored inline in Convex; everything else goes to R2 once per content hash,
 * so pushing again only uploads what changed. push never uploads audio, video or anything over
 * 25 MB unless --include-media is passed, so raw footage stays on this machine. publish uploads
 * only the file being reviewed, so it plays in the web app as well as the desktop app.
 * Each reel's post caption and script come from <slug>.caption.md and <slug>.script.md beside
 * the render (edit/hook_a.caption.md for edit/hook_a_v1.mp4), when they exist.
 * final copies each finished cut to final/<slug>.mp4 with its caption and script, replacing the
 * cut's previous final, so final/ always holds exactly what's done.
 */
import { spawnSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import {
  copyFileSync,
  createReadStream,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync
} from "node:fs";
import { open, rename } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, dirname, extname, join, relative, resolve } from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";

import { cutroomFolders, workspaceOf } from "./folders.mjs";

const ROOT = process.env.CUTROOM_HOME ?? join(homedir(), "Cutroom");
const CREDENTIALS = readCredentials(join(ROOT, ".cutroom/credentials.json"));
const CONVEX_URL = process.env.CONVEX_URL ?? CREDENTIALS.convexUrl;
const KEY = process.env.CUTROOM_KEY ?? CREDENTIALS.key;
const WORKSPACE =
  process.env.CUTROOM_WORKSPACE ??
  (CREDENTIALS.key
    ? (CREDENTIALS.workspace ?? (await workspaceOf({ convexUrl: CONVEX_URL, key: KEY })))
    : null);
const F = cutroomFolders({ root: ROOT, workspace: WORKSPACE });
F.toCutroom(process.cwd());
const SYNC_VERSION = "1.46.0";
const POLL_MIN = 3000;
const POLL_MAX = 30000;

const TEXT_EXT = new Set([".md", ".json", ".txt", ".srt", ".vtt", ".py", ".csv", ".yaml", ".yml"]);
const INLINE_MAX = 512 * 1024;
const SKIP =
  /(^|\/)(\.DS_Store|\.git|\.cutroom|__pycache__|node_modules|\.review|(?:sullyedit|cutroom)_chunks[^/]*)(\/|$)|\.(tmp|log)$/;
const LARGE_BYTES = 25 * 1024 * 1024;
const AV = /\.(mp4|mov|m4v|mkv|webm|m4a|mp3|wav|aac|aiff?)$/i;
const TYPES = {
  ".mp4": "video/mp4",
  ".mov": "video/quicktime",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".md": "text/markdown; charset=utf-8",
  ".txt": "text/plain; charset=utf-8"
};

const [cmd, ...args] = process.argv.slice(2);
const LOCAL_ONLY = new Set(["link", "unlink"]);
const BOOL_FLAGS = new Set(["no-video", "include-media", "text-only", "local", "upload", "wait"]);
const takesValue = (a) => a?.startsWith("--") && !BOOL_FLAGS.has(a.slice(2));
const flags = Object.fromEntries(
  args.flatMap((a, i) =>
    a.startsWith("--") ? [[a.slice(2), BOOL_FLAGS.has(a.slice(2)) || args[i + 1]]] : []
  )
);
const positional = args.filter((a, i) => !a.startsWith("--") && !takesValue(args[i - 1]));

try {
  if (cmd && cmd !== "help" && !LOCAL_ONLY.has(cmd) && (!CONVEX_URL || !KEY)) {
    throw new Error(
      "not signed in: open the Cutroom app and sign in (or set CUTROOM_KEY and CONVEX_URL)"
    );
  }
  if (cmd === "push")
    await push(folder(positional[0]), flags.only, {
      includeMedia: !!flags["include-media"],
      textOnly: !!flags["text-only"]
    });
  else if (cmd === "pull") await pull(folder(positional[0]));
  else if (cmd === "publish")
    await publish(positional[0], videoDir(positional[1]), positional.slice(2), flags);
  else if (cmd === "final") await promoteFinal(videoDir(positional[0]), positional.slice(1));
  else if (cmd === "wait") await waitFor(videoDir(positional[0]), flags.kind);
  else if (cmd === "watch") await watch(positional[0] && videoDir(positional[0]));
  else if (cmd === "link") link(positional[0], positional[1], flags.videos);
  else if (cmd === "unlink") unlink(positional[0]);
  else {
    console.log(readFileSync(fileURLToPath(import.meta.url), "utf8").split("*/")[0]);
    process.exit(cmd && cmd !== "help" ? 1 : 0);
  }
} catch (error) {
  console.error(`cutroom: ${error.message}`);
  process.exit(1);
}

/* ---------- commands ---------- */

async function push(dir, only, { includeMedia = false, textOnly = false, extra = [] } = {}) {
  const skipped = [];
  const keep = (p) => {
    if (textOnly) return TEXT_EXT.has(extname(p).toLowerCase());
    if (includeMedia) return true;
    if (AV.test(p) || statSync(F.toLocal(p)).size > LARGE_BYTES) {
      skipped.push(p);
      return false;
    }
    return true;
  };
  const local = [
    ...new Set([
      ...listFiles(F.toLocal(dir))
        .map((abs) => F.toCutroom(abs))
        .filter((p) => !only || p.startsWith(`${dir}/${only}`))
        .filter(keep),
      ...extra
    ])
  ];
  if (skipped.length)
    console.log(
      `${dir}: left ${skipped.length} media/large files on this machine (--include-media to send them)`
    );
  const remote = new Map(
    (await convex("query", "files:manifest", { prefix: dir })).map((f) => [f.path, f])
  );

  const changed = [];
  for (const path of local) {
    const abs = F.toLocal(path);
    const { size, sha256 } = await settledHash(abs);
    if (remote.get(path)?.sha256 === sha256) continue;
    const contentType = TYPES[extname(path).toLowerCase()] ?? "application/octet-stream";
    const inline = TEXT_EXT.has(extname(path).toLowerCase()) && size <= INLINE_MAX;
    changed.push({ path, abs, size, sha256, contentType, inline });
  }
  if (!changed.length) return console.log(`${dir}: up to date (${local.length} files)`);

  const media = changed.filter((f) => !f.inline);
  const known = new Set(
    media.length
      ? await convex("query", "files:knownHashes", { sha256s: media.map((f) => f.sha256) })
      : []
  );
  // One call signs every media file; the key comes back even for bytes R2 already has.
  const links = media.length
    ? await convex("action", "media:uploadUrls", {
        items: media.map(({ sha256, contentType }) => ({ sha256, contentType }))
      })
    : [];
  const linkBySha = new Map(links.map((l) => [l.sha256, l]));

  let uploaded = 0;
  for (const f of media.filter((f) => !known.has(f.sha256))) {
    process.stdout.write(`  ↑ ${f.path} (${mb(f.size)})\n`);
    const res = await fetch(linkBySha.get(f.sha256).url, {
      method: "PUT",
      headers: { "content-type": f.contentType, "content-length": String(f.size) },
      body: Readable.toWeb(createReadStream(f.abs)),
      duplex: "half"
    }).catch((error) => {
      if (statSync(f.abs).size !== f.size) {
        throw new Error(
          `${f.path} changed while uploading (still being written?). Push again once it's done.`
        );
      }
      throw error;
    });
    if (!res.ok) throw new Error(`upload failed for ${f.path}: ${res.status} ${await res.text()}`);
    uploaded += f.size;
  }

  // Commit in batches to stay well under Convex's per-mutation limits.
  const rows = changed.map((f) => ({
    path: f.path,
    sha256: f.sha256,
    size: f.size,
    contentType: f.contentType,
    ...(f.inline ? { text: readFileSync(f.abs, "utf8") } : { r2Key: linkBySha.get(f.sha256).key })
  }));
  for (let i = 0; i < rows.length; i += 40) {
    await convex("mutation", "files:commit", { files: rows.slice(i, i + 40) });
  }
  console.log(`${dir}: pushed ${changed.length} changed files, uploaded ${mb(uploaded)}`);
}

async function pull(dir, { only } = {}) {
  const remote = (await convex("query", "files:manifest", { prefix: dir })).filter((f) =>
    only ? f.path === only : !SKIP.test(f.path)
  );
  const stale = [];
  for (const f of remote) {
    const abs = F.toLocal(f.path);
    if (existsSync(abs) && statSync(abs).size === f.size && (await hashFile(abs)) === f.sha256)
      continue;
    stale.push(f);
  }
  if (!stale.length) return console.log(`${dir}: up to date (${remote.length} files)`);

  const media = stale.filter((f) => f.r2Key);
  const links = media.length
    ? await convex("action", "media:downloadUrls", {
        keys: [...new Set(media.map((f) => f.r2Key))]
      })
    : [];
  const urlByKey = new Map(links.map((l) => [l.key, l.url]));

  let downloaded = 0;
  for (const f of stale) {
    const abs = F.toLocal(f.path);
    mkdirSync(dirname(abs), { recursive: true });
    if (f.text !== undefined) {
      writeFileSync(abs, f.text);
      continue;
    }
    process.stdout.write(`  ↓ ${f.path} (${mb(f.size)})\n`);
    const res = await fetch(urlByKey.get(f.r2Key));
    if (!res.ok) throw new Error(`download failed for ${f.path}: ${res.status}`);
    const tmp = `${abs}.tmp`;
    const fh = await open(tmp, "w");
    await pipeline(Readable.fromWeb(res.body), fh.createWriteStream());
    await rename(tmp, abs);
    downloaded += f.size;
  }
  console.log(`${dir}: pulled ${stale.length} files, downloaded ${mb(downloaded)}`);
}

/**
 * Pushes the video's edit files, then posts a storyboard or render version to the review queue.
 * Storyboards read beats + transcript from edit/storyboard.json.
 */
async function publish(kind, dir, files, opts) {
  if (kind !== "render" && kind !== "storyboard")
    throw new Error("publish render|storyboard <video dir> <file>…");
  if (!files.length) throw new Error("which file? e.g. edit/my_video_v2.mp4");
  if (files.length > 1 && kind === "storyboard")
    throw new Error("a video has one storyboard: publish one file");
  if (files.length > 1 && (opts.title || opts.version))
    throw new Error("--title and --version apply to one file at a time");
  const publishedAt = Date.now();
  for (const file of files) await publishOne(kind, dir, file, opts);
  if (kind === "render") await printVariations(dir);
  if (opts.wait) await waitFor(dir, kind, publishedAt);
}

async function printVariations(dir) {
  const renders = (await convex("query", "reviews:list", {})).filter(
    (r) => r.dir === dir && r.kind === "render"
  );
  if (renders.length < 2) return;
  console.log(
    `${dir} has ${renders.length} variations: ${renders.map((r) => `${r.stem} v${r.latest}`).join(", ")}`
  );
}

async function publishOne(kind, dir, fileArg, opts) {
  const videoRel = fileArg.startsWith(`${dir}/`) ? fileArg.slice(dir.length + 1) : fileArg;
  const video = `${dir}/${videoRel}`;
  if (!F.exists(video)) throw new Error(`${video} not found`);
  const editDir = dirname(video);

  const file = videoRel.split("/").pop();
  let stem, version;
  if (kind === "storyboard") {
    // Older videos published their storyboard as "sully_storyboard"; keep that series going.
    stem = F.exists(`${editDir}/storyboard.json`) ? "storyboard" : "sully_storyboard";
    version = Number(file.match(/^base(?:_v(\d+))?\.mp4$/)?.[1] ?? 1);
  } else {
    ({ stem, version } = renderName(file));
  }
  if (opts.version) version = Number(opts.version);

  const { beats, words } = storyboardOf(F.toLocal(editDir));
  const images = [
    [["storyboard_board.jpg", "sully_storyboard_board.jpg"], "Storyboard board"],
    ...(kind === "render" ? [[["cue_check.jpg", "sully_cue_check.jpg"], "Cue check"]] : [])
  ]
    .map(([names, label]) => [names.find((n) => F.exists(`${editDir}/${n}`)), label])
    .filter(([name]) => name)
    .map(([name, label]) => ({ label, path: `${editDir}/${name}` }));

  const preview = reviewCopy(video);

  await push(dir, relative(dir, editDir) + "/", {
    textOnly: true,
    extra: [video, ...(preview ? [preview] : []), ...images.map((i) => i.path)]
  });

  const copy = Object.fromEntries(
    ["caption", "script"]
      .map((field) => [field, `${editDir}/${stem}.${field}.md`])
      .filter(([, path]) => F.exists(path))
      .map(([field, path]) => [field, readFileSync(F.toLocal(path), "utf8").trim()])
  );

  const id = await convex("mutation", "reviews:publish", {
    videoPath: dir,
    kind,
    stem,
    version,
    video,
    ...(preview ? { preview } : {}),
    images,
    beats,
    words,
    ...copy,
    ...(opts.title ? { title: opts.title } : {}),
    // From a Cutroom chat this ties the review to it, so the user's notes wake it up.
    ...(process.env.CUTROOM_CHAT_ID ? { chatId: process.env.CUTROOM_CHAT_ID } : {})
  });
  console.log(`published ${kind} ${stem} v${version} → review ${id}`);
}

function reviewCopy(video) {
  const source = F.toLocal(video);
  const path = `${dirname(video)}/.review/${basename(video)}`;
  const target = F.toLocal(path);
  if (existsSync(target) && statSync(target).mtimeMs >= statSync(source).mtimeMs) return path;
  mkdirSync(dirname(target), { recursive: true });
  const partial = `${target}.part.mp4`;
  process.stdout.write(`  making the review copy of ${basename(video)}\n`);
  const run = spawnSync(
    process.env.CUTROOM_FFMPEG ?? "ffmpeg",
    ['-y', '-v', 'error', '-i', source, '-vf', 'scale=\'if(gt(iw,ih),-2,min(720,iw))\':\'if(gt(iw,ih),min(720,ih),-2)\'', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-maxrate', '2500k', '-bufsize', '5000k', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', partial],
    { stdio: ["ignore", "ignore", "pipe"] }
  );
  if (run.error || run.status !== 0 || statSync(partial, { throwIfNoEntry: false })?.size === 0) {
    rmSync(partial, { force: true });
    console.log(
      `  no review copy (${run.error?.code ?? run.stderr?.toString().trim().split("\n").pop()}); the app plays the full file`
    );
    return undefined;
  }
  if (statSync(partial).size >= statSync(source).size) {
    rmSync(partial, { force: true });
    return undefined;
  }
  renameSync(partial, target);
  return path;
}

/** Copies finished cuts to final/<slug>.mp4 with their caption and script. No files: every approved cut. */
async function promoteFinal(dir, files) {
  const renders = (await convex("query", "reviews:list", {})).filter(
    (r) => r.dir === dir && r.kind === "render"
  );
  const videos = files.length
    ? files.map((f) => (f.startsWith(`${dir}/`) ? f : `${dir}/${f}`))
    : renders.filter((r) => r.status === "approved").map((r) => r.file);
  if (!videos.length)
    throw new Error(`no approved cut in ${dir}: name the file, e.g. edit/my_video_v2.mp4`);

  mkdirSync(F.toLocal(`${dir}/final`), { recursive: true });
  const finals = [];
  for (const video of videos) {
    const { stem } = renderName(basename(video));
    if (!F.exists(video)) await pull(dirname(video), { only: video });
    if (!F.exists(video)) throw new Error(`${video} not found`);
    const target = `${dir}/final/${stem}.mp4`;
    copyFileSync(F.toLocal(video), F.toLocal(target));
    finals.push(target);

    const review = renders.find((r) => r.stem === stem);
    const detail = review && (await convex("query", "reviews:get", { id: review.id }));
    const published = detail?.versions.find((v) => v.file === video);
    for (const field of ["caption", "script"]) {
      const source = `${dirname(video)}/${stem}.${field}.md`;
      const text =
        published?.[field] || (F.exists(source) ? readFileSync(F.toLocal(source), "utf8") : "");
      if (text) writeFileSync(F.toLocal(`${dir}/final/${stem}.${field}.md`), `${text.trim()}\n`);
    }
    console.log(`final: ${basename(video)} → ${F.toLocal(target)}`);
  }
  await push(dir, "final/", { textOnly: true, extra: finals });
}

function printEvent(e) {
  console.log(
    JSON.stringify({
      action: e.action,
      kind: e.kind,
      reel: e.videoPath,
      version: e.version,
      notes: e.notes
    })
  );
}

/**
 * Blocks until the next Send to Claude / Approve on this video (optionally one kind), then
 * prints the next step and exits. Only events after `since` count, so old notes don't fire.
 */
async function waitFor(dir, kind, since = Date.now()) {
  console.log(`waiting for notes in Cutroom on ${dir}${kind ? ` (${kind})` : ""}…`);
  const e = await new Promise((resolve, reject) => {
    const stop = followReviewEvents({
      after: since,
      onEvents: (events) => {
        const match = events.find((e) => e.videoPath === dir && (!kind || e.kind === kind));
        if (!match) return;
        stop();
        resolve(match);
      },
      onError: (error) => {
        stop();
        reject(error);
      }
    });
  });
  const what = e.kind === "storyboard" ? "storyboard" : `render v${e.version}`;
  if (e.action === "approved") {
    console.log(`\nApproved: the ${what}.`);
    console.log(
      e.kind === "storyboard"
        ? "Next: start building the edit."
        : `Next: it's done. Run: cutroom final "${dir}"`
    );
  } else {
    console.log(`\nNotes on the ${what}:`);
    for (const n of e.notes) console.log(`- ${n}`);
    console.log("Next: make the changes, publish the next version with --wait again.");
  }
  printEvent(e);
}

/** One JSON line per review event, optionally only for one video folder. Feed it to Monitor. */
async function watch(dir) {
  console.log(`watching for review events${dir ? ` on ${dir}` : ""} (ctrl-c to stop)`);
  await new Promise((_, reject) => {
    followReviewEvents({
      after: Date.now(),
      onEvents: (events) => {
        for (const e of events) if (!dir || e.videoPath === dir) printEvent(e);
      },
      onError: reject
    });
  });
}

/**
 * Calls onEvents with each batch of review events newer than `after`. Subscribes over Convex's
 * sync socket, so the query only runs again when an event is added; Node without WebSocket
 * (before 22) polls instead, slowing to once every 30s while nothing happens.
 */
function followReviewEvents({ after: since, onEvents, onError }) {
  let after = since;
  let stopped = false;
  let socket;
  let timer;
  const take = (events) => {
    after = Math.max(after, ...events.map((e) => e.createdAt));
    onEvents(events);
  };
  const poll = async (delay) => {
    try {
      const events = await convex("query", "reviews:events", { after });
      if (stopped) return;
      const next = events.length ? POLL_MIN : delay;
      if (events.length) take(events);
      if (!stopped) timer = setTimeout(() => poll(Math.min(next * 1.5, POLL_MAX)), next);
    } catch (error) {
      onError(error);
    }
  };
  const connect = () => {
    if (typeof WebSocket === "undefined") return void poll(POLL_MIN);
    const ws = (socket = new WebSocket(
      `${CONVEX_URL.replace(/^http/, "ws")}/api/${SYNC_VERSION}/sync`
    ));
    let opened = false;
    let version = 0;
    let queryId = 0;
    const send = (message) => ws.send(JSON.stringify(message));
    const subscribe = () => {
      const modifications = queryId ? [{ type: "Remove", queryId }] : [];
      queryId += 1;
      modifications.push({
        type: "Add",
        queryId,
        udfPath: "reviews:events",
        args: [{ key: KEY, after }]
      });
      send({ type: "ModifyQuerySet", baseVersion: version, newVersion: ++version, modifications });
    };
    ws.onopen = () => {
      opened = true;
      send({
        type: "Connect",
        sessionId: randomUUID(),
        connectionCount: 0,
        lastCloseReason: "InitialConnect",
        clientTs: Date.now()
      });
      subscribe();
    };
    ws.onmessage = ({ data }) => {
      const message = JSON.parse(data);
      if (message.type === "FatalError") return ws.close();
      if (message.type !== "Transition") return;
      for (const m of message.modifications) {
        if (m.queryId !== queryId) continue;
        if (m.type === "QueryFailed") {
          stopped = true;
          ws.close();
          return onError(new Error(`reviews:events: ${m.errorMessage}`));
        }
        if (m.type === "QueryUpdated" && m.value?.length) {
          take(m.value);
          if (!stopped) subscribe();
        }
      }
    };
    ws.onclose = () => {
      if (stopped) return;
      if (!opened) return void poll(POLL_MIN);
      timer = setTimeout(connect, 5000);
    };
  };
  connect();
  return () => {
    stopped = true;
    clearTimeout(timer);
    socket?.close();
  };
}

/* ---------- helpers ---------- */

function renderName(file) {
  const m = file.match(/^(.+?)(?:_v(\d+))?\.mp4$/);
  if (!m || /^base(_v\d+)?\.mp4$/.test(file))
    throw new Error(`render files are named <slug>_vN.mp4 (got ${file})`);
  return { stem: m[1], version: Number(m[2] ?? 1) };
}

function storyboardOf(editAbs) {
  const sbPath = ["storyboard.json", "sully_storyboard.json"]
    .map((n) => join(editAbs, n))
    .find(existsSync);
  if (!sbPath) return { beats: [], words: [] };
  const sb = JSON.parse(readFileSync(sbPath, "utf8"));
  const beats = (sb.beats ?? [])
    .filter((b) => b.t0 != null)
    .map((b) => ({
      id: b.id,
      t0: b.t0,
      t1: b.t1,
      layout: b.layout,
      visual: b.visual ?? "",
      asset: b.asset ?? "",
      cues: (b.cues ?? []).map((c) =>
        [c.event, c.sfx && `sfx ${c.sfx}`].filter(Boolean).join(" · ")
      )
    }));
  let words = [];
  if (sb.transcript && existsSync(join(editAbs, sb.transcript))) {
    words = (JSON.parse(readFileSync(join(editAbs, sb.transcript), "utf8")).words ?? []).map(
      (w) => ({
        w: w.word,
        s: w.start,
        e: w.end
      })
    );
  }
  return { beats, words };
}

async function convex(kind, path, args) {
  const res = await fetch(`${CONVEX_URL}/api/${kind}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ path, args: { key: KEY, ...args }, format: "json" })
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.status === "error") {
    throw new Error(`${path}: ${body.errorMessage ?? res.status}`);
  }
  return body.value;
}

function listFiles(dir) {
  if (!existsSync(dir)) throw new Error(`${dir} does not exist here`);
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const abs = join(dir, entry.name);
    if (SKIP.test(F.toCutroom(abs) ?? abs)) continue;
    if (entry.isDirectory()) out.push(...listFiles(abs));
    else if (entry.isFile()) out.push(abs);
  }
  return out;
}

/** Hashes a file once it has stopped changing, so a file that's still being written isn't pushed half done. */
async function settledHash(abs) {
  for (let tries = 0; ; tries++) {
    const before = statSync(abs);
    const sha256 = await hashFile(abs);
    const after = statSync(abs);
    if (before.size === after.size && before.mtimeMs === after.mtimeMs)
      return { size: after.size, sha256 };
    if (tries === 5)
      throw new Error(`${F.toCutroom(abs) ?? abs} keeps changing. Push again once it's written.`);
    await new Promise((r) => setTimeout(r, 2000));
  }
}

function hashFile(abs) {
  return new Promise((ok, fail) => {
    const h = createHash("sha256");
    createReadStream(abs)
      .on("data", (d) => h.update(d))
      .on("end", () => ok(h.digest("hex")))
      .on("error", fail);
  });
}

/** A Cutroom folder, given as a Cutroom path or as a folder on disk (relative to the current directory). */
function folder(arg) {
  if (!arg) throw new Error('which folder? e.g. "projects/shorts/videos/2026-10-11-gemini-argon"');
  const onDisk = resolve(process.cwd(), arg);
  const isCutroomPath =
    /^(account|projects)(\/|$)/.test(arg) && (F.exists(arg) || !existsSync(onDisk));
  const rel = (isCutroomPath ? arg : F.toCutroom(onDisk))?.replace(/\/$/, "");
  if (!rel || !/^(account|projects\/[^/]+)(\/|$)/.test(rel))
    throw new Error(`not in a Cutroom project: ${arg} (run cutroom link <project> in its folder)`);
  return rel;
}

/** A video folder: projects/<project>/videos/<name>. */
function videoDir(arg) {
  const rel = folder(arg);
  if (!/^projects\/[^/]+\/videos\/[^/]+$/.test(rel))
    throw new Error(`not a video folder: ${rel} (expected projects/<project>/videos/<name>)`);
  return rel;
}

function link(slug, dir, videos) {
  if (!slug) {
    const linked = Object.entries(F.linked());
    if (!linked.length) return console.log("no project has a folder on this Mac yet");
    for (const [slug, f] of linked) console.log(`${slug}: ${f.path} (videos: ${f.videos})`);
    return;
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(slug)) throw new Error(`not a project slug: ${slug}`);
  const folder = dir ?? process.cwd();
  if (!existsSync(resolve(folder))) throw new Error(`${folder} does not exist`);
  F.link(slug, folder, videos);
  console.log(`${slug} lives in ${F.projectRoot(slug)}, videos in ${F.videosRoot(slug)}`);
}

function unlink(slug) {
  if (!slug) throw new Error("which project? cutroom unlink <project>");
  const was = F.unlink(slug);
  console.log(
    was ? `${slug} is no longer linked to ${was.path}` : `${slug} has no folder on this Mac`
  );
}

function readCredentials(file) {
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

function mb(bytes) {
  return `${(bytes / 1e6).toFixed(1)} MB`;
}
