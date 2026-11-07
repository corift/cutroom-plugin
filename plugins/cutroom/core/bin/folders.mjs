import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

export const MARKER = ".cutroom/project.json";

const readJson = (file) => {
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch {
    return null;
  }
};

const writeJson = (file, value) => {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(value, null, 2) + "\n");
};

const inside = (base, abs) => {
  const rel = relative(base, abs);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel)) ? rel : null;
};

const posix = (p) => p.split(sep).filter(Boolean).join("/");

const lstatOrNull = (path) => {
  try {
    return lstatSync(path);
  } catch {
    return null;
  }
};

const folderName = (name) =>
  String(name)
    .replace(/[/\\:\0]/g, " ")
    .replace(/^\.+/, "")
    .trim() || "Project";

export async function workspaceOf({ convexUrl, key }) {
  if (!convexUrl || !key) return null;
  try {
    const response = await fetch(`${convexUrl.replace(/\/$/, "")}/api/query`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ path: "users:me", args: { key }, format: "json" })
    });
    const body = await response.json();
    return body.status === "success" ? (body.value?.workspaceId ?? null) : null;
  } catch {
    return null;
  }
}

export function cutroomFolders({
  root = process.env.CUTROOM_HOME ?? join(homedir(), "Cutroom"),
  workspace = null
} = {}) {
  const indexFile = join(root, ".cutroom/projects.json");
  const accountsDir = join(root, ".cutroom/accounts");
  const home = workspace ? join(accountsDir, workspace) : root;
  const accountRoot = join(home, "account");
  const managedProjects = join(home, "projects");

  const readIndex = () => {
    const saved = readJson(indexFile) ?? {};
    const legacy = Object.values(saved).some((v) => typeof v?.path === "string");
    return legacy ? { legacy: saved, accounts: {} } : { ...saved, accounts: saved.accounts ?? {} };
  };

  let index = readIndex();
  const markers = new Map();

  const ownMarker = (marker) =>
    !!marker?.project && (workspace ? marker.workspace === workspace : !marker.workspace);

  const markerAt = (dir) => {
    if (!markers.has(dir)) {
      const marker = dir === root ? null : readJson(join(dir, MARKER));
      markers.set(dir, ownMarker(marker) ? marker : null);
    }
    return markers.get(dir);
  };

  const findMarker = (abs) => {
    for (let dir = abs; ; dir = dirname(dir)) {
      const marker = markerAt(dir);
      if (marker) return { dir, slug: marker.project, videos: marker.videos ?? "videos" };
      if (dirname(dir) === dir) return null;
    }
  };

  const mine = () => {
    if (!workspace) return (index.legacy ??= {});
    return (index.accounts[workspace] ??= {});
  };

  const save = () => writeJson(indexFile, workspace ? { ...index, legacy: undefined } : index);

  const remember = (slug, path) => {
    if (mine()[slug]?.path === path) return;
    for (const [other, entry] of Object.entries(mine()))
      if (other !== slug && entry.path === path) delete mine()[other];
    mine()[slug] = { path };
    save();
  };

  const linkedFolder = (slug) => {
    const path = mine()[slug]?.path;
    const marker = path && markerAt(path);
    return marker?.project === slug ? { path, videos: marker.videos ?? "videos" } : null;
  };

  const linked = () =>
    Object.fromEntries(
      Object.keys(mine())
        .map((slug) => [slug, linkedFolder(slug)])
        .filter(([, folder]) => folder)
    );

  const projectRoot = (slug) => linkedFolder(slug)?.path ?? join(managedProjects, slug);
  const videosRoot = (slug) => join(projectRoot(slug), linkedFolder(slug)?.videos ?? "videos");

  const toLocal = (rel) => {
    const parts = rel.split("/").filter(Boolean);
    if (parts[0] === "account") return join(accountRoot, ...parts.slice(1));
    if (parts[0] !== "projects" || !parts[1]) return join(home, ...parts);
    if (!linkedFolder(parts[1])) return join(managedProjects, ...parts.slice(1));
    if (parts[2] === "videos") return join(videosRoot(parts[1]), ...parts.slice(3));
    return join(projectRoot(parts[1]), ...parts.slice(2));
  };

  const toCutroom = (abs) => {
    const found = findMarker(abs);
    if (found) {
      remember(found.slug, found.dir);
      const inVideos = inside(join(found.dir, found.videos), abs);
      if (inVideos !== null)
        return [`projects/${found.slug}/videos`, posix(inVideos)].filter(Boolean).join("/");
      return [`projects/${found.slug}`, posix(relative(found.dir, abs))].filter(Boolean).join("/");
    }
    const inAccount = inside(accountRoot, abs);
    if (inAccount !== null) return ["account", posix(inAccount)].filter(Boolean).join("/");
    const inProjects = inside(managedProjects, abs);
    if (inProjects !== null) return ["projects", posix(inProjects)].filter(Boolean).join("/");
    return null;
  };

  const link = (slug, folder, videos) => {
    const path = resolve(folder);
    const existing = readJson(join(path, MARKER));
    if (existing?.project && !ownMarker(existing))
      throw new Error(`${path} belongs to another Cutroom account`);
    const before = linkedFolder(slug);
    if (before && before.path !== path) rmSync(join(before.path, MARKER), { force: true });
    const marker = {
      project: slug,
      ...(workspace ? { workspace } : {}),
      ...(videos && videos !== "videos" ? { videos } : {})
    };
    writeJson(join(path, MARKER), marker);
    markers.clear();
    remember(slug, path);
  };

  const unlink = (slug) => {
    const folder = linkedFolder(slug);
    if (folder) rmSync(join(folder.path, MARKER), { force: true });
    markers.clear();
    delete mine()[slug];
    save();
    return folder;
  };

  const ensureFolder = (slug, name = slug) => {
    const current = linkedFolder(slug);
    if (current) return current.path;
    const base = join(root, folderName(name));
    for (let n = 1; ; n++) {
      const path = n === 1 ? base : `${base} ${n}`;
      const marker = readJson(join(path, MARKER));
      const stat = lstatOrNull(path);
      const empty =
        !stat || (stat.isDirectory() && !readdirSync(path).filter((f) => f !== ".DS_Store").length);
      if (ownMarker(marker) && marker.project === slug) {
        remember(slug, path);
        return path;
      }
      if (marker?.project || !empty) continue;
      mkdirSync(path, { recursive: true });
      link(slug, path);
      return path;
    }
  };

  const adoptLegacy = () => {
    if (!workspace) return;
    if (index.legacyOwner && index.legacyOwner !== workspace) return;
    const legacyAccount = join(root, "account");
    const legacyProjects = join(root, "projects");
    const pending =
      index.legacy || existsSync(legacyAccount) || lstatOrNull(legacyProjects)?.isDirectory();
    if (!pending) return;
    index.legacyOwner = workspace;
    mkdirSync(home, { recursive: true });
    for (const file of readdirSync(join(root, ".cutroom")))
      if (/^sync-.+\.json$/.test(file) && !existsSync(join(home, file)))
        renameSync(join(root, ".cutroom", file), join(home, file));
    if (existsSync(legacyAccount) && !existsSync(accountRoot))
      renameSync(legacyAccount, accountRoot);
    const claim = (slug, path) => {
      const marker = readJson(join(path, MARKER));
      if (marker?.project && marker.project !== slug) return;
      if (marker?.workspace && marker.workspace !== workspace) return;
      writeJson(join(path, MARKER), { ...marker, project: slug, workspace });
      mine()[slug] = { path };
    };
    for (const [slug, entry] of Object.entries(index.legacy ?? {}))
      if (existsSync(entry.path)) claim(slug, entry.path);
    if (lstatOrNull(legacyProjects)?.isDirectory())
      for (const slug of readdirSync(legacyProjects)) {
        const path = join(legacyProjects, slug);
        if (mine()[slug] || !/^[a-z0-9][a-z0-9-]*$/.test(slug)) continue;
        const stat = lstatOrNull(path);
        if (stat?.isSymbolicLink()) {
          try {
            claim(slug, realpathSync(path));
            rmSync(path);
          } catch {}
        } else if (stat?.isDirectory()) claim(slug, path);
      }
    delete index.legacy;
    markers.clear();
    save();
  };

  adoptLegacy();

  return {
    root,
    workspace,
    accountRoot,
    linked,
    isLinked: (slug) => !!linkedFolder(slug),
    projectRoot,
    videosRoot,
    toLocal,
    toCutroom,
    link,
    unlink,
    ensureFolder,
    exists: (rel) => existsSync(toLocal(rel))
  };
}
