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

missing=""
command -v ffmpeg >/dev/null 2>&1 || missing="$missing ffmpeg"
[ -x "$venv/bin/python3" ] || missing="$missing python-env"
[ -f "$credentials" ] || missing="$missing sign-in"
if [ -n "$missing" ]; then
  echo "Cutroom is installed but not set up yet (missing:$missing). If the user wants to edit a video, run the cutroom:setup skill first."
fi
exit 0
