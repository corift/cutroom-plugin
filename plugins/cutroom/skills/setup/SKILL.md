---
name: setup
description: Set up Cutroom on this machine so Claude Code can edit videos - installs ffmpeg and a Python environment for the edit engine, signs in to cutroom.so, and creates the ~/Cutroom folder. Use when the user first installs Cutroom, when the session-start note says Cutroom is not set up, or when an edit fails because ffmpeg, Python packages or Cutroom credentials are missing.
---

# Set up Cutroom

Work through these in order. Check each one first and skip what is already done. Tell the user what you are about to install before you install it, keep the summary short, and never print the Cutroom key.

## 1. ffmpeg

`command -v ffmpeg`. If it is missing:
- macOS with Homebrew (`command -v brew`): `brew install ffmpeg`.
- macOS without Homebrew: ask the user whether to install Homebrew (https://brew.sh) or to download a static ffmpeg build themselves. Don't install Homebrew without a yes.
- Linux: the system package manager (`sudo apt-get install -y ffmpeg` or similar), after asking.

## 2. Python environment

The engine needs Python 3.10+ with numpy and Pillow. Use a venv in the plugin's data folder so it survives plugin updates:

```bash
VENV="${CLAUDE_PLUGIN_DATA:-$HOME/Cutroom/.cutroom}/venv"
python3 -c 'import sys; assert sys.version_info >= (3, 10)' && python3 -m venv "$VENV" && "$VENV/bin/pip" install -q --upgrade pip numpy Pillow
```

If `python3` is missing or older than 3.10: macOS `brew install python@3.12` (then use `python3.12`), Linux the package manager. If `uv` is installed, `uv venv "$VENV" --python 3.12 && uv pip install --python "$VENV/bin/python" numpy Pillow` is faster.

For this session, put the venv first on PATH in each command that runs the engine: `PATH="$VENV/bin:$PATH"`. New sessions do this automatically.

## 3. Sign in

Call the `connect_cli` tool on the Cutroom MCP server. If it isn't available or says the user isn't signed in, ask the user to run `/mcp`, pick **cutroom**, and sign in in the browser, then try again.

Write what it returns to the path it gives (`~/Cutroom/.cutroom/credentials.json`) without echoing the key into the conversation:

```bash
mkdir -p ~/Cutroom/.cutroom && umask 077 && cat > ~/Cutroom/.cutroom/credentials.json <<'JSON'
{"key": "<key>", "convexUrl": "<convexUrl>"}
JSON
```

## 4. Folders

```bash
mkdir -p ~/Cutroom/account ~/Cutroom/projects
```

Call `list_projects`. A project is best kept in the folder the user already works in: the one Claude Code is open in, with their CLAUDE.md, skills and videos. If the current folder (or another they name) is a project's home, link it so nothing gets moved. It writes `.cutroom/project.json` there, so the link survives moving the folder and cloning it on another machine; suggest committing it if the folder is a git repo. `--videos` is the subfolder holding one folder per video (default `videos`):

```bash
node "$CLAUDE_PLUGIN_ROOT/core/bin/cutroom.mjs" link <slug> ["<folder>"] --videos "<subfolder>"
```

Run inside a folder that has `.cutroom/project.json` already (a clone, or a moved folder), the CLI picks it up by itself; nothing to link.

Otherwise the project lives in `~/Cutroom/projects/<slug>`. Either way, give the project folder its videos folder and skills (see "Project skills" in the `cutroom` skill). `P` is the project folder (`cutroom.mjs link` prints it), `V` its videos folder:

```bash
mkdir -p "$V" "$P/.agents/skills" "$P/.claude"
cp -Rn "$CLAUDE_PLUGIN_ROOT/core/starters/<kind>/skills/." "$P/.agents/skills/"
[ -e "$P/.claude/skills" ] || ln -s ../.agents/skills "$P/.claude/skills"
[ -e "$P/skills" ] || ln -s .agents/skills "$P/skills"
```

`<kind>` is the project's `kind` (shorts or ugc). `cp -n` never overwrites a skill the user already has. `skills/` is how the project's skills sync to Cutroom.

## 5. Optional: on-device person masking (macOS)

Cutouts (face over graphics) use Apple Vision when the Swift compiler is present (`xcrun --find swiftc`), otherwise Cutroom's hosted GPU matte. Nothing to install; if the user wants the on-device path, `xcode-select --install`.

## 6. Check

```bash
ffmpeg -version | head -1
"$VENV/bin/python3" -c "import numpy, PIL; print('python ok')"
PYTHONPATH="$CLAUDE_PLUGIN_ROOT/core/engine" "$VENV/bin/python3" -c "from cutroom import account; print('signed in' if account.key() else 'NOT signed in')"
node "$CLAUDE_PLUGIN_ROOT/core/bin/cutroom.mjs" help >/dev/null && echo "cli ok"
```

Then tell the user how to start: put a recording in a new `<YYYY-MM-DD-slug>/` folder in the project's videos folder (or just give Claude the file path) and ask Claude to edit it. Reviews show up at https://cutroom.so/app.
