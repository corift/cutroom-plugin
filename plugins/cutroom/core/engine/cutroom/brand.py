"""The brand kit: the colours and fonts a project's edits use.

A brand kit is a small JSON file in the user's account (account/brand-kits/<slug>.json), picked
per project. The agent points CUTROOM_BRAND_KIT at it; without one every value falls back to
the house default the templates were built with, so old render scripts look the same.

    {
      "name": "Default",
      "colors": {"accent": "#D62222", "marker": "#FFD65C", "highlight": "#E07A58"},
      "fonts": {"caption": "/Library/Fonts/Inter-Bold.otf", "serif_italic": "...", "mono": "...", "display": "..."}
    }

Modules read it once at import: `RED = brand.color("accent", (214, 34, 34))`.
"""
import json, os

_KIT = {}
_path = os.environ.get("CUTROOM_BRAND_KIT")
if _path and os.path.exists(_path):
    with open(_path) as fh:
        _KIT = json.load(fh)


def _rgb(value):
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def color(name, default):
    """An (r, g, b) colour from the kit's "colors", or `default`."""
    value = _KIT.get("colors", {}).get(name)
    return _rgb(value) if isinstance(value, str) and len(value.lstrip("#")) == 6 else default


def font(name, default):
    """A font file path from the kit's "fonts", or `default` (missing files fall back too)."""
    path = _KIT.get("fonts", {}).get(name)
    return path if path and os.path.exists(path) else default


def get(key, default=None):
    """Any other kit setting, e.g. brand.get("captions", {}).get("style", "kallaway")."""
    return _KIT.get(key, default)
