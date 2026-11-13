#!/bin/sh
core="$CLAUDE_PLUGIN_ROOT/core"
home="${CUTROOM_HOME:-$HOME/Cutroom}"
data="${CLAUDE_PLUGIN_DATA:-$home/.cutroom}"
venv="$data/venv"
credentials="$home/.cutroom/credentials.json"

field() {
  [ -f "$credentials" ] && node -e 'try{process.stdout.write(String(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"))[process.argv[2]]??""))}catch{}' "$credentials" "$1" 2>/dev/null
}

if [ -n "$CLAUDE_ENV_FILE" ]; then
  {
    echo "export CUTROOM_CORE=\"$core\""
    echo "export CUTROOM_ENGINE=\"$core/engine\""
    echo "export CUTROOM_ASSETS=\"$core/assets\""
    echo "export CUTROOM_HOME=\"$home\""
    echo "export CUTROOM_ACCOUNT=\"$home/account\""
    echo "export CUTROOM_VENV=\"$venv\""
    echo "export PYTHONPATH=\"$core/engine\${PYTHONPATH:+:\$PYTHONPATH}\""
    [ -x "$venv/bin/python3" ] && echo "export PATH=\"$venv/bin:\$PATH\""
    key="$(field key)"
    url="$(field convexUrl)"
    [ -n "$key" ] && echo "export CUTROOM_KEY=\"$key\""
    [ -n "$url" ] && echo "export CONVEX_URL=\"$url\""
  } >> "$CLAUDE_ENV_FILE"
fi

installed="$(basename "$CLAUDE_PLUGIN_ROOT")"
checked="$data/update-checked"
updated="$data/updated-to"

update() {
  latest="$(git ls-remote https://github.com/corift/cutroom-plugin.git HEAD 2>/dev/null | cut -c1-12)"
  [ -n "$latest" ] && [ "$latest" != "$installed" ] || return 0
  claude plugin marketplace update cutroom && claude plugin update cutroom@cutroom && echo "$latest" > "$updated"
}

if [ "${CUTROOM_AUTO_UPDATE:-1}" != "0" ] && echo "$installed" | grep -Eq '^[0-9a-f]{12}$' &&
  command -v git >/dev/null 2>&1 && command -v claude >/dev/null 2>&1 &&
  [ -z "$(find "$checked" -mmin -360 2>/dev/null)" ]; then
  mkdir -p "$data" && : > "$checked"
  (update &) >/dev/null 2>&1 </dev/null
fi

if [ -f "$updated" ] && [ "$(cat "$updated")" != "$installed" ]; then
  echo "A newer Cutroom is already installed and applies after a restart. Tell the user once to restart Claude Code to get it, then carry on."
fi

missing=""
command -v ffmpeg >/dev/null 2>&1 || missing="$missing ffmpeg"
[ -x "$venv/bin/python3" ] || missing="$missing python-env"
[ -f "$credentials" ] || missing="$missing sign-in"
if [ -n "$missing" ]; then
  echo "Cutroom is installed but not set up yet (missing:$missing). If the user wants to edit a video, run the cutroom:setup skill first."
fi
exit 0
