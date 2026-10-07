#!/usr/bin/env python3
"""Install the pinned upstream macOS runtime; no Homebrew or global Python changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.build_macos_app import build_app, register_desktop_app


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_archive(archive: Path, manifest: dict) -> None:
    if archive.stat().st_size != manifest["assetSize"] or digest(archive) != manifest["sha256"]:
        raise ValueError("Official runtime archive size/SHA-256 mismatch; rerun setup to download it again.")


def verify_runtime(directory: Path, manifest: dict) -> None:
    if directory.is_symlink():
        raise ValueError("Refusing a runtime directory symlink; use --tool-dir for an external runtime.")
    for name, expected in manifest["requiredFiles"].items():
        path = directory / name
        if any(parent.is_symlink() for parent in path.parents if parent != directory and directory in parent.parents):
            raise ValueError(f"Runtime file has a symlink parent: {name}")
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Missing or modified runtime file: {name}")


def install_runtime(archive: Path, tools: Path, manifest: dict) -> Path:
    verify_archive(archive, manifest)
    tools.mkdir(parents=True, exist_ok=True)
    destination = tools / manifest["installDirectory"]
    if destination.is_symlink():
        raise ValueError("Refusing to replace a runtime directory symlink.")
    with tempfile.TemporaryDirectory(prefix=".macos-stage-", dir=tools) as temporary:
        staging = Path(temporary) / "runtime"
        staging.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            # Only extract the pinned files. Ignore sample media and never follow ZIP links.
            for name in manifest["requiredFiles"]:
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe runtime path: {name}")
                info = bundle.getinfo(name)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f"Runtime archive contains a symlink: {name}")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        verify_runtime(staging, manifest)
        (staging / "realesrgan-ncnn-vulkan").chmod(0o755)
        backup = Path(temporary) / "previous"
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    return destination


def download_archive(manifest: dict, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / manifest["assetName"]
    if archive.exists():
        try:
            verify_archive(archive, manifest)
            return archive
        except ValueError:
            archive.unlink()
    partial = archive.with_suffix(".zip.partial")
    try:
        request = urllib.request.Request(manifest["assetUrl"], headers={"User-Agent": "AnimeWallpaperUpscaler"})
        with urllib.request.urlopen(request, timeout=30) as response, partial.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > manifest["assetSize"]:
                    raise ValueError("Runtime download exceeds its pinned size.")
                output.write(chunk)
        verify_archive(partial, manifest)
        os.replace(partial, archive)
        return archive
    finally:
        partial.unlink(missing_ok=True)


def register_skill(root: Path, home: Path) -> None:
    destination = home / ".codex" / "skills" / "anime-wallpaper-upscale"
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() and destination.resolve() == root.resolve():
            return
        print(f"Warning: existing skill preserved: {destination}", file=sys.stderr)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(root.resolve(), target_is_directory=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept-upstream-license", action="store_true")
    parser.add_argument("--skip-skill", action="store_true")
    parser.add_argument("--skip-shortcut", action="store_true", help="Build the app but omit its Desktop link.")
    parser.add_argument("--archive", type=Path, help="Advanced: use a local official ZIP, still verified.")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("This installer requires macOS; use install.cmd on Windows.")
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required.")
    manifest = json.loads((PROJECT_ROOT / "upstream" / "realesrgan-macos.json").read_text())
    print(f"Official upstream: {manifest['release']}\nTerms: {PROJECT_ROOT / 'THIRD_PARTY_NOTICES.md'}", flush=True)
    if not args.accept_upstream_license:
        if not sys.stdin.isatty() or input("Download and install under these upstream terms? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Setup cancelled. Use --accept-upstream-license after reviewing the terms.")
            return 1
    try:
        destination = PROJECT_ROOT / "tools" / manifest["installDirectory"]
        try:
            verify_runtime(destination, manifest)
            (destination / "realesrgan-ncnn-vulkan").chmod(0o755)
        except ValueError:
            archive = args.archive or download_archive(manifest, PROJECT_ROOT / "tools" / ".downloads")
            destination = install_runtime(archive, PROJECT_ROOT / "tools", manifest)
        python = PROJECT_ROOT / ".venv" / "bin" / "python"
        if not python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(PROJECT_ROOT / ".venv")], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")], check=True)
        subprocess.run([str(python), str(PROJECT_ROOT / "scripts" / "upscale_wallpaper.py"), "--help"], check=True, stdout=subprocess.DEVNULL)
        # Run the same GPU probe used by the CLI, with models in the correct working directory.
        subprocess.run([str(python), "-c", "from pathlib import Path; from anime_wallpaper_upscaler.system import probe_gpus; import sys; p=Path(sys.argv[1]); print(probe_gpus(p, p.parent))", str(destination / "realesrgan-ncnn-vulkan")], cwd=PROJECT_ROOT, check=True, timeout=90)
        if not args.skip_skill:
            try:
                register_skill(PROJECT_ROOT, Path.home())
            except OSError as exc:
                print(f"Warning: optional skill registration failed: {exc}", file=sys.stderr)
        try:
            app = build_app(PROJECT_ROOT)
            if not args.skip_shortcut and not register_desktop_app(app, Path.home() / "Desktop"):
                print("Warning: existing Desktop app preserved; use the app under tools/.", file=sys.stderr)
            print(f"Drop images or folders onto: {app}")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            print(f"Warning: optional Finder app could not be created: {exc}", file=sys.stderr)
        print("Setup complete. Use the Finder app, ./scripts/run-wallpaper.command, or the CLI.")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        print("If macOS blocks the verified executable, allow that app in System Settings > Privacy & Security. Keep Gatekeeper enabled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
