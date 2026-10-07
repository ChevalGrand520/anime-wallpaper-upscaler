#!/usr/bin/env python3
"""Map Finder/Terminal inputs and a saved scale to the existing wallpaper CLI."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anime_wallpaper_upscaler.launcher_run import run_cancellable
from anime_wallpaper_upscaler.preferences import load_scale, save_scale


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    settings = parser.add_mutually_exclusive_group()
    settings.add_argument("--get-scale", action="store_true", help="Show the saved scale (default: 4).")
    settings.add_argument("--set-scale", type=int, choices=(2, 3, 4), help="Save a scale for future launches.")
    settings.add_argument("--scale", type=int, choices=(2, 3, 4), help="Save this scale and process the inputs.")
    parser.add_argument("paths", nargs="*", help="Images or folders; use -- before paths beginning with '-'.")
    args = parser.parse_args(argv)
    if args.get_scale or args.set_scale is not None:
        if args.paths:
            parser.error("Do not combine settings-only options with input paths.")
        if args.get_scale:
            print(load_scale())
            return 0
        try:
            save_scale(args.set_scale)
        except OSError as exc:
            print(f"Error: could not save scale: {exc}", file=sys.stderr)
            return 2
        print(f"Saved scale: {args.set_scale}x")
        return 0
    if not args.paths:
        parser.error("Supply an image or folder path.")
    scale = args.scale if args.scale is not None else load_scale()
    if args.scale is not None:
        try:
            save_scale(scale)
        except OSError as exc:
            print(f"Error: could not save scale: {exc}", file=sys.stderr)
            return 2
    return run_cancellable(args.paths, scale)


if __name__ == "__main__":
    raise SystemExit(main())
