import os
from pathlib import Path

import pytest

from anime_wallpaper_upscaler.discovery import InputJob
from anime_wallpaper_upscaler.errors import VulkanError
from anime_wallpaper_upscaler.realesrgan import RuntimeFiles
from anime_wallpaper_upscaler.system import GpuDevice
from anime_wallpaper_upscaler.workflow import BatchSummary, ImageResult


def test_cli_accepts_repeated_inputs_scale_gpu_and_auto_target() -> None:
    from anime_wallpaper_upscaler.cli import build_parser

    args = build_parser().parse_args(
        [
            "--input",
            "one.png",
            "--input",
            "folder",
            "--scale",
            "2",
            "--gpu",
            "1",
            "--target",
            "auto",
            "--recursive",
        ]
    )

    assert args.input == ["one.png", "folder"]
    assert args.scale == 2
    assert args.gpu == "1"
    assert args.target == "auto"
    assert args.recursive is True


def test_cli_defaults_preserve_four_and_auto() -> None:
    from anime_wallpaper_upscaler.cli import build_parser

    args = build_parser().parse_args(["--input", "one.png"])

    assert (args.mode, args.scale, args.target, args.gpu) == (
        "preserve",
        4,
        "auto",
        "auto",
    )
    assert args.model is None
    assert args.no_compare is False
    assert args.no_upscaled_source is False
    assert args.no_open_output is False


@pytest.mark.parametrize("option", ("--x-bias", "--y-bias"))
@pytest.mark.parametrize("value", ("-0.01", "1.01", "not-a-number"))
def test_cli_rejects_invalid_biases(option: str, value: str) -> None:
    from anime_wallpaper_upscaler.cli import build_parser

    with pytest.raises(SystemExit) as caught:
        build_parser().parse_args(["--input", "one.png", option, value])

    assert caught.value.code == 2


def test_tool_directory_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    from anime_wallpaper_upscaler.cli import DEFAULT_TOOL_DIR, resolve_tool_dir

    monkeypatch.delenv("REALESRGAN_TOOL_DIR", raising=False)
    assert resolve_tool_dir(None) == DEFAULT_TOOL_DIR.resolve()

    monkeypatch.setenv("REALESRGAN_TOOL_DIR", "environment-runtime")
    assert resolve_tool_dir(None) == Path("environment-runtime").resolve()
    assert resolve_tool_dir(Path("explicit-runtime")) == Path(
        "explicit-runtime"
    ).resolve()


def test_missing_input_is_reported_before_runtime_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from anime_wallpaper_upscaler import cli

    runtime_checked = False

    def unexpected_runtime_check(*args: object, **kwargs: object) -> RuntimeFiles:
        nonlocal runtime_checked
        runtime_checked = True
        raise AssertionError("runtime validation must follow input discovery")

    monkeypatch.setattr(cli, "validate_runtime", unexpected_runtime_check)
    missing = tmp_path / "definitely-missing.png"

    exit_code = cli.main(["--input", str(missing), "--no-open-output"])

    assert exit_code == 2
    assert runtime_checked is False
    error = capsys.readouterr().err
    assert "Input path does not exist" in error
    assert str(missing) in error


def test_main_builds_options_reports_devices_and_opens_each_root_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from anime_wallpaper_upscaler import cli

    source = tmp_path / "source.png"
    source.write_bytes(b"discovery only checks the file path")
    tool_dir = tmp_path / "runtime"
    output_root = tmp_path / "output"
    runtime = RuntimeFiles(
        tool_dir / "realesrgan-ncnn-vulkan.exe",
        tool_dir / "models" / "model.param",
        tool_dir / "models" / "model.bin",
    )
    runtime_calls: list[tuple[Path, str, int]] = []
    observed_options: list[object] = []
    opened: list[Path] = []

    def fake_validate_runtime(
        selected_tool_dir: Path, model: str, scale: int
    ) -> RuntimeFiles:
        runtime_calls.append((selected_tool_dir, model, scale))
        return runtime

    def fake_process_batch(
        jobs: list[InputJob], options: object, progress: object
    ) -> BatchSummary:
        observed_options.append(options)
        progress(1, 1, jobs[0])
        first = ImageResult(
            source=source,
            output_root=output_root,
            upscaled=output_root / "source_realesrgan_3x.png",
            wallpaper=output_root / "source_wallpaper.jpg",
            comparison=None,
            desktop=None,
        )
        second = ImageResult(
            source=source,
            output_root=output_root,
            upscaled=output_root / "source_realesrgan_3x.png",
            wallpaper=output_root / "source_wallpaper-2.jpg",
            comparison=None,
            desktop=None,
        )
        return BatchSummary((first, second), (), (output_root / "batch.log",))

    monkeypatch.setattr(cli, "validate_runtime", fake_validate_runtime)
    monkeypatch.setattr(
        cli,
        "probe_gpus",
        lambda executable, cwd: [
            GpuDevice(0, "RTX 5070 Ti"),
            GpuDevice(1, "Integrated GPU"),
        ],
    )
    monkeypatch.setattr(
        cli, "resolve_target", lambda value: ((3840, 2160), None)
    )
    monkeypatch.setattr(cli, "process_batch", fake_process_batch)
    monkeypatch.setattr(os, "startfile", lambda path: opened.append(Path(path)), raising=False)

    exit_code = cli.main(
        [
            "--input",
            str(source),
            "--tool-dir",
            str(tool_dir),
            "--out-dir",
            str(output_root),
            "--scale",
            "3",
            "--gpu",
            "0",
            "--no-compare",
            "--no-upscaled-source",
            "--x-bias",
            "0.25",
            "--y-bias",
            "0.75",
        ]
    )

    assert exit_code == 0
    assert runtime_calls == [(tool_dir.resolve(), "realesr-animevideov3", 3)]
    assert len(observed_options) == 1
    options = observed_options[0]
    assert options.runtime == runtime
    assert options.model == "realesr-animevideov3"
    assert options.scale == 3
    assert options.target == (3840, 2160)
    assert options.gpu == 0
    assert options.compare is False
    assert options.keep_upscaled is False
    assert options.x_bias == 0.25
    assert options.y_bias == 0.75
    assert opened == [output_root]

    output = capsys.readouterr().out
    assert "Target: 3840x2160" in output
    assert "GPU 0: RTX 5070 Ti" in output
    assert "GPU 1: Integrated GPU" in output
    assert "[1/1] source.png" in output
    assert "Succeeded: 2" in output
    assert "Failed: 0" in output


def test_vulkan_preflight_error_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from anime_wallpaper_upscaler import cli

    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    runtime = RuntimeFiles(
        tmp_path / "tool.exe",
        tmp_path / "model.param",
        tmp_path / "model.bin",
    )
    monkeypatch.setattr(cli, "validate_runtime", lambda *args: runtime)
    monkeypatch.setattr(
        cli,
        "probe_gpus",
        lambda *args: (_ for _ in ()).throw(VulkanError("Install a Vulkan driver")),
    )

    assert cli.main(["--input", str(source), "--no-open-output"]) == 2
    assert "Install a Vulkan driver" in capsys.readouterr().err


def test_partial_batch_failure_returns_one_without_opening_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from anime_wallpaper_upscaler import cli

    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    runtime = RuntimeFiles(
        tmp_path / "tool.exe",
        tmp_path / "model.param",
        tmp_path / "model.bin",
    )
    monkeypatch.setattr(cli, "validate_runtime", lambda *args: runtime)
    monkeypatch.setattr(cli, "probe_gpus", lambda *args: [GpuDevice(0, "GPU")])
    monkeypatch.setattr(cli, "resolve_target", lambda value: ((1920, 1080), None))
    monkeypatch.setattr(
        cli,
        "process_batch",
        lambda jobs, options, progress: BatchSummary(
            (), ((source, "decode failed"),), (tmp_path / "batch.log",)
        ),
    )
    monkeypatch.setattr(
        os,
        "startfile",
        lambda path: pytest.fail("--no-open-output must suppress startfile"),
        raising=False,
    )

    exit_code = cli.main(["--input", str(source), "--no-open-output"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Succeeded: 0" in captured.out
    assert "Failed: 1" in captured.out
    assert f"FAILED {source}: decode failed" in captured.err
