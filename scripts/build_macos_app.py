#!/usr/bin/env python3
"""Build a small AppKit Finder launcher using existing Xcode Command Line Tools."""
from __future__ import annotations

from pathlib import Path
import plistlib
import subprocess
import tempfile

APP_NAME = "Anime Wallpaper Upscaler.app"
BUNDLE_ID = "com.chevalgrand.anime-wallpaper-upscaler"


def build_app(root: Path) -> Path:
    root = root.resolve()
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    destination = tools / APP_NAME
    if destination.is_symlink():
        raise ValueError(f"Existing app symlink preserved: {destination}")
    if destination.exists():
        try:
            info = plistlib.loads((destination / "Contents/Info.plist").read_bytes())
        except (OSError, ValueError) as exc:
            raise ValueError(f"Existing app preserved: {destination}") from exc
        if info.get("CFBundleIdentifier") != BUNDLE_ID or not info.get("AnimeWallpaperUpscalerProject"):
            raise ValueError(f"Existing unrelated app preserved: {destination}")
    compiler = subprocess.run(["/usr/bin/xcode-select", "-p"], capture_output=True, text=True)
    if compiler.returncode != 0:
        raise ValueError("The optional native app needs existing Xcode Command Line Tools. No tools were installed; use the Terminal launcher instead.")
    with tempfile.TemporaryDirectory(prefix=".app-stage-", dir=tools) as temporary:
        staging = Path(temporary) / APP_NAME
        executable = staging / "Contents/MacOS/WallpaperLauncher"
        executable.parent.mkdir(parents=True)
        try:
            subprocess.run(["/usr/bin/xcrun", "swiftc", "-O", "-swift-version", "5",
                            str(root / "scripts/macos/Launcher.swift"), "-o", str(executable)],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"Could not compile the native launcher: {exc.stderr}") from exc
        info_path = staging / "Contents/Info.plist"
        info = {"CFBundleIdentifier": BUNDLE_ID, "CFBundleDisplayName": "Anime Wallpaper Upscaler",
                "CFBundleName": "Anime Wallpaper Upscaler", "CFBundlePackageType": "APPL",
                "CFBundleExecutable": "WallpaperLauncher", "CFBundleVersion": "1",
                "CFBundleDocumentTypes": [{"CFBundleTypeRole": "Viewer",
                    "LSItemContentTypes": ["public.image", "public.folder"]}],
                "AnimeWallpaperUpscalerProject": str(root)}
        info_path.write_bytes(plistlib.dumps(info))
        # Sign locally. Source builds are not notarized release packages.
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(staging)],
                       check=True, capture_output=True, text=True)
        backup = Path(temporary) / "previous.app"
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    return destination


def register_desktop_app(app: Path, desktop: Path) -> bool:
    destination = desktop / APP_NAME
    if destination.exists() or destination.is_symlink():
        return destination.is_symlink() and destination.resolve() == app.resolve()
    desktop.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(app.resolve(), target_is_directory=True)
    return True


if __name__ == "__main__":
    print(build_app(Path(__file__).resolve().parents[1]))
