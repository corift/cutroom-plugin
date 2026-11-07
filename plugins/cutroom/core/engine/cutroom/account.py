import json
import os


def _saved():
    home = os.environ.get("CUTROOM_HOME") or os.path.join(os.path.expanduser("~"), "Cutroom")
    try:
        with open(os.path.join(home, ".cutroom", "credentials.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def key():
    return os.environ.get("CUTROOM_KEY") or _saved().get("key", "")


def site():
    url = os.environ.get("CONVEX_URL") or _saved().get("convexUrl", "")
    return url.replace(".convex.cloud", ".convex.site").rstrip("/") if url else ""
