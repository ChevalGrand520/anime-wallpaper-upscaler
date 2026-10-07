from pathlib import Path
from subprocess import CompletedProcess

import pytest

from anime_wallpaper_upscaler.errors import DependencyError, VulkanError
from anime_wallpaper_upscaler.system import gpu_repair, runtime_executable_name, runtime_repair
from anime_wallpaper_upscaler.realesrgan import (
    RuntimeFiles,
    build_command,
    resolve_model,
    run_upscale,
    validate_runtime,
)


def _create_runtime_files(tool_dir: Path, model_file_stem: str) -> RuntimeFiles:
    models_dir = tool_dir / "models"
    models_dir.mkdir(parents=True)
    executable = tool_dir / runtime_executable_name()
    model_param = models_dir / f"{model_file_stem}.param"
    model_bin = models_dir / f"{model_file_stem}.bin"
    for path in (executable, model_param, model_bin):
        path.write_bytes(b"test")
    return RuntimeFiles(executable, model_param, model_bin)


def test_missing_runtime_lists_missing_files_and_repair_command(
    tmp_path: Path,
) -> None:
    with pytest.raises(DependencyError) as caught:
        validate_runtime(tmp_path, "realesrgan-x4plus-anime", 4)

    message = str(caught.value)
    assert runtime_executable_name() in message
    assert "realesrgan-x4plus-anime.param" in message
    assert "realesrgan-x4plus-anime.bin" in message
    assert runtime_repair() in message
    assert "--tool-dir" in message


def test_automatic_model_keeps_legacy_4x_and_supports_2x_3x() -> None:
    assert resolve_model(None, 4) == "realesrgan-x4plus-anime"
    assert resolve_model(None, 2) == "realesr-animevideov3"
    assert resolve_model(None, 3) == "realesr-animevideov3"


@pytest.mark.parametrize(
    "model",
    ("realesrgan-x4plus-anime", "realesrgan-x4plus", "realesrnet-x4plus"),
)
@pytest.mark.parametrize("scale", (2, 3))
def test_fixed_4x_models_are_rejected_before_runtime_validation(
    model: str,
    scale: int,
) -> None:
    with pytest.raises(DependencyError, match="supports only scale 4") as caught:
        resolve_model(model, scale)

    message = str(caught.value)
    assert "omit --model" in message
    assert "realesr-animevideov3" in message


@pytest.mark.parametrize("scale", (2, 3, 4))
def test_animevideov3_resolves_scale_specific_model_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scale: int,
) -> None:
    expected = _create_runtime_files(
        tmp_path / "tool", f"realesr-animevideov3-x{scale}"
    )
    monkeypatch.chdir(tmp_path)

    runtime = validate_runtime(Path("tool"), "realesr-animevideov3", scale)

    assert runtime == RuntimeFiles(
        expected.executable.resolve(),
        expected.model_param.resolve(),
        expected.model_bin.resolve(),
    )
    assert all(
        path.is_absolute()
        for path in (runtime.executable, runtime.model_param, runtime.model_bin)
    )


def test_fixed_4x_model_uses_unsuffixed_model_files(tmp_path: Path) -> None:
    expected = _create_runtime_files(tmp_path, "realesrgan-x4plus-anime")

    runtime = validate_runtime(tmp_path, "realesrgan-x4plus-anime", 4)

    assert runtime == RuntimeFiles(
        expected.executable.resolve(),
        expected.model_param.resolve(),
        expected.model_bin.resolve(),
    )


def test_command_preserves_manual_gpu_scale_and_explicit_runtime_paths(
    tmp_path: Path,
) -> None:
    runtime = _create_runtime_files(tmp_path, "realesr-animevideov3-x3")

    command = build_command(
        runtime,
        Path("in.png"),
        Path("out.png"),
        "realesr-animevideov3",
        3,
        1,
    )

    assert command == [
        str(runtime.executable.resolve()),
        "-i",
        str(Path("in.png").resolve()),
        "-o",
        str(Path("out.png").resolve()),
        "-m",
        str((tmp_path / "models").resolve()),
        "-n",
        "realesr-animevideov3",
        "-s",
        "3",
        "-t",
        "0",
        "-f",
        "png",
        "-g",
        "1",
    ]


def test_command_omits_gpu_flag_for_automatic_selection(tmp_path: Path) -> None:
    runtime = _create_runtime_files(tmp_path, "realesrgan-x4plus-anime")

    command = build_command(
        runtime,
        tmp_path / "in.png",
        tmp_path / "out.png",
        "realesrgan-x4plus-anime",
        4,
        None,
    )

    assert "-g" not in command


def test_run_upscale_executes_in_runtime_directory_and_captures_output(
    tmp_path: Path,
) -> None:
    runtime = _create_runtime_files(tmp_path, "realesrgan-x4plus-anime")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, "done\n", "")

    run_upscale(
        runtime=runtime,
        input_path=tmp_path / "input.png",
        output_path=tmp_path / "output.png",
        model="realesrgan-x4plus-anime",
        scale=4,
        gpu=None,
        runner=runner,
    )

    assert len(calls) == 1
    assert calls[0][1] == {
        "cwd": runtime.executable.resolve().parent,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }


@pytest.mark.parametrize(
    "diagnostic",
    (
        "vkCreateInstance failed",
        "no VULKAN device found",
        "failed to create gpu instance",
    ),
)
def test_run_upscale_maps_vulkan_failures_to_driver_repairs(
    tmp_path: Path,
    diagnostic: str,
) -> None:
    runtime = _create_runtime_files(tmp_path, "realesrgan-x4plus-anime")

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(command, 1, "", diagnostic)

    with pytest.raises(VulkanError) as caught:
        run_upscale(
            runtime,
            tmp_path / "input.png",
            tmp_path / "output.png",
            "realesrgan-x4plus-anime",
            4,
            None,
            runner,
        )

    message = str(caught.value)
    assert diagnostic in message
    assert gpu_repair() in message


def test_run_upscale_maps_other_failures_to_last_diagnostic_and_repair(
    tmp_path: Path,
) -> None:
    runtime = _create_runtime_files(tmp_path, "realesrgan-x4plus-anime")

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(
            command,
            7,
            "first detail\n\n",
            "second detail\nfinal useful line\n",
        )

    with pytest.raises(DependencyError) as caught:
        run_upscale(
            runtime,
            tmp_path / "input.png",
            tmp_path / "output.png",
            "realesrgan-x4plus-anime",
            4,
            0,
            runner,
        )

    message = str(caught.value)
    assert "exit code 7" in message
    assert "final useful line" in message
    assert "first detail" not in message
    assert runtime_repair() in message
