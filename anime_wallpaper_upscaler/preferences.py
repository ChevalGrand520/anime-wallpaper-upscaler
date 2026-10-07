"""Small, local launcher preferences. The deterministic CLI keeps its own defaults."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

DEFAULT_SCALE = 4


def preferences_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "Anime Wallpaper Upscaler" / "preferences.json"


def load_scale(path: Path | None = None) -> int:
    selected = path if path is not None else preferences_path()
    try:
        settings = json.loads(selected.read_text(encoding="utf-8"))
        scale = settings.get("scale") if isinstance(settings, dict) else None
        if type(scale) is not int or scale not in (2, 3, 4):
            raise ValueError("scale must be 2, 3, or 4")
        return scale
    except FileNotFoundError:
        return DEFAULT_SCALE
    except (OSError, ValueError) as exc:
        print(f"Warning: could not read saved scale ({exc}); using {DEFAULT_SCALE}x.", file=sys.stderr)
        return DEFAULT_SCALE


def save_scale(scale: int, path: Path | None = None) -> None:
    if type(scale) is not int or scale not in (2, 3, 4):
        raise ValueError("Scale must be 2, 3, or 4.")
    selected = path if path is not None else preferences_path()
    selected.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=selected.parent,
                                         prefix=".preferences-", delete=False) as output:
            temporary = Path(output.name)
            json.dump({"scale": scale}, output)
            output.write("\n")
        os.replace(temporary, selected)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
