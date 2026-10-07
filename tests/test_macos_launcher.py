import json
import os
from pathlib import Path
import plistlib
import sys

import pytest

from anime_wallpaper_upscaler import preferences
from scripts import macos_launcher
from scripts.build_macos_app import APP_NAME, BUNDLE_ID, build_app, register_desktop_app


def test_missing_preferences_keep_four_without_creating_a_file(tmp_path: Path) -> None:
    settings = tmp_path / "preferences.json"
    assert preferences.load_scale(settings) == 4
    assert not settings.exists()


@pytest.mark.parametrize("content", ['broken', '[]', '{"scale": true}', '{"scale": "3"}', '{"scale": 5}'])
def test_invalid_preferences_fall_back_without_destroying_file(tmp_path: Path, content: str,
                                                             capsys: pytest.CaptureFixture[str]) -> None:
    settings = tmp_path / "preferences.json"
    settings.write_text(content)
    assert preferences.load_scale(settings) == 4
    assert settings.read_text() == content
    assert "using 4x" in capsys.readouterr().err


@pytest.mark.parametrize("scale", (2, 3, 4))
def test_scale_persists_across_reads_and_replaces_cleanly(tmp_path: Path, scale: int) -> None:
    settings = tmp_path / "nested/preferences.json"
    preferences.save_scale(4, settings)
    preferences.save_scale(scale, settings)
    assert preferences.load_scale(settings) == scale
    assert json.loads(settings.read_text()) == {"scale": scale}
    assert not list(settings.parent.glob(".preferences-*"))


def test_failed_atomic_save_preserves_previous_choice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "preferences.json"
    preferences.save_scale(2, settings)
    def fail(*args: object) -> None:
        raise OSError("disk unavailable")
    monkeypatch.setattr(preferences.os, "replace", fail)
    with pytest.raises(OSError, match="disk unavailable"):
        preferences.save_scale(3, settings)
    assert preferences.load_scale(settings) == 2
    assert not list(tmp_path.glob(".preferences-*"))


def test_launcher_preserves_paths_and_saved_scale_without_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "preferences.json"
    monkeypatch.setattr(preferences, "preferences_path", lambda: settings)
    preferences.save_scale(3)
    calls = []
    monkeypatch.setattr(macos_launcher, "run_cancellable", lambda paths, scale: calls.append((paths, scale)) or 1)
    paths = ["/tmp/中文 image $(literal)'\".png", "/tmp/a folder"]
    assert macos_launcher.main(["--", *paths]) == 1
    assert calls == [(paths, 3)]


def test_explicit_scale_is_remembered_and_settings_do_not_process_images(tmp_path: Path,
                                                                      monkeypatch: pytest.MonkeyPatch,
                                                                      capsys: pytest.CaptureFixture[str]) -> None:
    settings = tmp_path / "preferences.json"
    monkeypatch.setattr(preferences, "preferences_path", lambda: settings)
    scales = []
    monkeypatch.setattr(macos_launcher, "run_cancellable", lambda paths, scale: scales.append(str(scale)) or 0)
    assert macos_launcher.main(["--set-scale", "2"]) == 0
    assert macos_launcher.main(["--get-scale"]) == 0
    assert scales == []
    assert capsys.readouterr().out.endswith("2\n")
    assert macos_launcher.main(["--scale", "3", "/tmp/image.png"]) == 0
    assert macos_launcher.main(["/tmp/next.png"]) == 0
    assert scales == ["3", "3"]


def test_failed_preference_write_is_reported_without_processing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                              capsys: pytest.CaptureFixture[str]) -> None:
    def fail(scale: int) -> None:
        raise OSError("permission denied")
    monkeypatch.setattr(macos_launcher, "save_scale", fail)
    monkeypatch.setattr(macos_launcher, "run_cancellable", lambda *a: pytest.fail("must not process"))
    assert macos_launcher.main(["--set-scale", "2"]) == 2
    assert "could not save scale" in capsys.readouterr().err


@pytest.mark.skipif(os.name == "nt", reason="Desktop links use macOS symlinks")
def test_desktop_link_registration_preserves_unrelated_app(tmp_path: Path) -> None:
    app = tmp_path / "tools" / APP_NAME
    app.mkdir(parents=True)
    desktop = tmp_path / "Desktop"
    assert register_desktop_app(app, desktop)
    assert register_desktop_app(app, desktop)
    existing = desktop / APP_NAME
    existing.unlink()
    existing.mkdir()
    (existing / "user-note").write_text("preserve me")
    assert not register_desktop_app(app, desktop)
    assert (existing / "user-note").read_text() == "preserve me"


def test_builder_preserves_unrelated_app_without_calling_compiler(tmp_path: Path) -> None:
    app = tmp_path / "tools" / APP_NAME
    app.mkdir(parents=True)
    with pytest.raises(ValueError, match="Existing app preserved"):
        build_app(tmp_path)
    assert app.exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS Command Line Tools")
def test_actual_native_app_compiles_and_signs_with_quotes_in_project_path(tmp_path: Path) -> None:
    root = tmp_path / 'project "quoted" 中文'
    scripts = root / "scripts/macos"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "scripts/macos/Launcher.swift"
    (scripts / "Launcher.swift").write_bytes(source.read_bytes())
    app = build_app(root)
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleIdentifier"] == BUNDLE_ID
    assert info["AnimeWallpaperUpscalerProject"] == str(root.resolve())
    assert info["CFBundleDocumentTypes"], "Drop handler must register document opening"
    assert (app / "Contents/MacOS/WallpaperLauncher").is_file()
    # Rebuilding a known app is idempotent and leaves the old app intact until compilation succeeds.
    assert build_app(root) == app
