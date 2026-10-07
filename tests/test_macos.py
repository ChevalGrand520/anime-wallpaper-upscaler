import hashlib
import json
import os
from pathlib import Path
from subprocess import CompletedProcess, CalledProcessError
import zipfile

import pytest

from anime_wallpaper_upscaler import cli, system
from anime_wallpaper_upscaler.realesrgan import validate_runtime
from anime_wallpaper_upscaler.workflow import BatchSummary, ImageResult
from scripts.setup_macos import install_runtime, register_skill, verify_runtime


def test_retina_detection_uses_primary_physical_panel_not_points_or_backing_pixels() -> None:
    data = {"SPDisplaysDataType": [{"spdisplays_ndrvs": [
        {"spdisplays_pixelresolution": "1920 x 1080"},
        {"spdisplays_main": "spdisplays_yes", "spdisplays_pixelresolution": "spdisplays_2560x1664Retina",
         "_spdisplays_resolution": "1470 x 956 @ 60.00Hz", "_spdisplays_pixels": "2940 x 1912"},
    ]}]}

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        assert command == ["/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"]
        assert kwargs["timeout"] == 20
        return CompletedProcess(command, 0, json.dumps(data))

    assert system.get_macos_display_resolution(runner) == (2560, 1664)


@pytest.mark.parametrize("report", ["broken json", '{}', '{"SPDisplaysDataType": []}',
    '{"SPDisplaysDataType": [{"spdisplays_ndrvs": [{"spdisplays_main": "spdisplays_yes", "spdisplays_pixelresolution": "0 x 0"}]}]}'])
def test_bad_macos_display_report_has_a_manual_target_repair(report: str) -> None:
    def detector() -> tuple[int, int]:
        return system.get_macos_display_resolution(lambda *a, **kw: CompletedProcess([], 0, report))

    target, warning = system.resolve_target("auto", detector)
    assert target == system.FALLBACK_TARGET
    assert warning is not None and "--target WIDTHxHEIGHT" in warning


@pytest.mark.parametrize("platform,executable", [("darwin", "realesrgan-ncnn-vulkan"), ("win32", "realesrgan-ncnn-vulkan.exe")])
def test_runtime_validation_selects_platform_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                   platform: str, executable: str) -> None:
    monkeypatch.setattr(system.sys, "platform", platform)
    (tmp_path / "models").mkdir()
    for name in [executable, "models/realesrgan-x4plus-anime.param", "models/realesrgan-x4plus-anime.bin"]:
        (tmp_path / name).write_bytes(b"fixture")
    assert validate_runtime(tmp_path, "realesrgan-x4plus-anime", 4).executable.name == executable
    if platform == "darwin":
        assert "MoltenVK" in system.gpu_repair()
        assert "install.command" in system.runtime_repair()
    else:
        assert "nvidia.com" in system.gpu_repair()
        assert "setup.ps1" in system.runtime_repair()


def test_macos_opens_each_output_root_once_without_shell_interpolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.delattr(cli.os, "startfile", raising=False)
    root = tmp_path / "space and $(literal)"
    result = ImageResult(tmp_path / "in.png", root, None, root / "wallpaper.jpg", None, None)
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    cli._open_successful_roots(BatchSummary((result, result), (), ()))
    assert calls == [(["/usr/bin/open", str(root)], {"check": True})]


def test_finder_open_failure_does_not_fail_completed_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                        capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.delattr(cli.os, "startfile", raising=False)
    result = ImageResult(tmp_path / "in.png", tmp_path, None, tmp_path / "wallpaper.jpg", None, None)
    def fail(*args: object, **kwargs: object) -> None:
        raise CalledProcessError(1, "open")
    monkeypatch.setattr(cli.subprocess, "run", fail)
    cli._open_successful_roots(BatchSummary((result,), (), ()))
    assert "could not open output folder" in capsys.readouterr().err


def fixture_archive(tmp_path: Path) -> tuple[Path, dict]:
    archive = tmp_path / "runtime.zip"
    files = {"realesrgan-ncnn-vulkan": b"test executable", "models/test.bin": b"model"}
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
        bundle.writestr("../../outside.txt", b"not extracted")
    manifest = {"assetSize": archive.stat().st_size,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "installDirectory": "runtime",
                "requiredFiles": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
    return archive, manifest


def test_setup_extracts_only_verified_files_and_sets_executable_permission(tmp_path: Path) -> None:
    archive, manifest = fixture_archive(tmp_path)
    destination = install_runtime(archive, tmp_path / "tools", manifest)
    verify_runtime(destination, manifest)
    if os.name != "nt":
        assert (destination / "realesrgan-ncnn-vulkan").stat().st_mode & 0o111
    assert not (tmp_path / "outside.txt").exists()


def test_corrupt_archive_preserves_existing_runtime(tmp_path: Path) -> None:
    archive, manifest = fixture_archive(tmp_path)
    destination = install_runtime(archive, tmp_path / "tools", manifest)
    archive.write_bytes(b"truncated")
    with pytest.raises(ValueError, match="SHA-256"):
        install_runtime(archive, tmp_path / "tools", manifest)
    verify_runtime(destination, manifest)


def test_bad_model_digest_preserves_existing_runtime(tmp_path: Path) -> None:
    archive, manifest = fixture_archive(tmp_path)
    destination = install_runtime(archive, tmp_path / "tools", manifest)
    changed = {**manifest, "requiredFiles": {**manifest["requiredFiles"], "models/test.bin": "0" * 64}}
    with pytest.raises(ValueError, match="modified runtime"):
        install_runtime(archive, tmp_path / "tools", changed)
    verify_runtime(destination, manifest)


@pytest.mark.skipif(os.name == "nt", reason="macOS skill symlinks; Windows uses its PowerShell harness")
def test_optional_skill_registration_preserves_conflicts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = tmp_path / "project"
    root.mkdir()
    register_skill(root, home)
    link = home / ".codex/skills/anime-wallpaper-upscale"
    assert link.resolve() == root
    other = tmp_path / "other"
    other.mkdir()
    register_skill(other, home)
    assert link.resolve() == root
