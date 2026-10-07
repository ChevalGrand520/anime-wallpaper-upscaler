from pathlib import Path
from subprocess import CompletedProcess

import pytest

from anime_wallpaper_upscaler.errors import UserInputError, VulkanError
from anime_wallpaper_upscaler.system import (
    GpuDevice,
    get_primary_display_resolution,
    gpu_repair,
    parse_gpu_devices,
    parse_target,
    probe_gpus,
    resolve_gpu,
    resolve_target,
)


def test_target_supports_auto_and_explicit_dimensions() -> None:
    assert parse_target("auto") is None
    assert parse_target("2560x1600") == (2560, 1600)


def test_invalid_target_has_repair() -> None:
    with pytest.raises(UserInputError, match="WIDTHxHEIGHT"):
        parse_target("wide")


def test_auto_target_falls_back_with_warning() -> None:
    def fail() -> tuple[int, int]:
        raise OSError("display unavailable")

    target, warning = resolve_target("auto", fail)
    assert target == (2560, 1600)
    assert warning is not None
    assert "--target" in warning
    assert "display unavailable" in warning


def test_explicit_target_does_not_call_detector() -> None:
    def fail_if_called() -> tuple[int, int]:
        raise AssertionError("detector should not run")

    assert resolve_target("1920x1080", fail_if_called) == ((1920, 1080), None)


class _FakeUser32:
    def __init__(self, width: int = 3840, height: int = 2160) -> None:
        self.width = width
        self.height = height
        self.calls: list[object] = []

    def SetProcessDpiAwarenessContext(self, context: object) -> bool:
        self.calls.append(context)
        return True

    def SetProcessDPIAware(self) -> bool:
        raise AssertionError(
            "legacy DPI API should not run when the modern API succeeds"
        )

    def GetSystemMetrics(self, metric: int) -> int:
        return self.width if metric == 0 else self.height


def test_display_detection_enables_physical_dpi_context() -> None:
    user32 = _FakeUser32()
    assert get_primary_display_resolution(user32=user32) == (3840, 2160)
    assert len(user32.calls) == 1


def test_display_detection_rejects_implausible_dimensions() -> None:
    with pytest.raises(OSError, match="320x200"):
        get_primary_display_resolution(user32=_FakeUser32(0, 0))


def test_parses_each_gpu_once() -> None:
    output = (
        "[0 NVIDIA GeForce RTX 5070 Ti Laptop GPU] queueC=2[8]\n"
        "[0 NVIDIA GeForce RTX 5070 Ti Laptop GPU] fp16-p/s/a=1/1/1\n"
        "[1 Intel(R) Graphics] queueC=1[4]\n"
        "[0 NVIDIA GeForce RTX 5070 Ti Laptop GPU] queueC=2[8]\n"
    )
    devices = parse_gpu_devices(output)
    assert [(device.id, device.name) for device in devices] == [
        (0, "NVIDIA GeForce RTX 5070 Ti Laptop GPU"),
        (1, "Intel(R) Graphics"),
    ]


def test_manual_gpu_must_exist_in_probe() -> None:
    devices = [GpuDevice(0, "Test GPU")]
    assert resolve_gpu("auto", devices) is None
    assert resolve_gpu("0", devices) == 0
    with pytest.raises(UserInputError, match=r"Available GPU IDs: 0 \(Test GPU\)"):
        resolve_gpu("2", devices)
    with pytest.raises(UserInputError, match="auto or a numeric GPU ID"):
        resolve_gpu("fast", devices)


def test_probe_uses_parsed_verbose_output_even_after_nonzero_exit(
    tmp_path: Path,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        calls.append((command, kwargs))
        return CompletedProcess(
            command,
            1,
            "probe input was deliberately missing",
            "[0 Test Vulkan GPU] queueC=1[1]\n",
        )

    executable = tmp_path / "tool.exe"
    devices = probe_gpus(executable, tmp_path, runner)

    assert devices == [GpuDevice(0, "Test Vulkan GPU")]
    assert calls[0][0] == [
        str(executable),
        "-i",
        str(tmp_path / "__aups_probe_missing__.png"),
        "-o",
        str(tmp_path / "__aups_probe_output__.png"),
        "-v",
    ]
    assert calls[0][1]["cwd"] == tmp_path


def test_probe_failure_lists_official_driver_repairs(tmp_path: Path) -> None:
    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(command, 1, "", "no Vulkan device\n")

    with pytest.raises(VulkanError) as caught:
        probe_gpus(tmp_path / "tool.exe", tmp_path, runner)

    message = str(caught.value)
    assert gpu_repair() in message
