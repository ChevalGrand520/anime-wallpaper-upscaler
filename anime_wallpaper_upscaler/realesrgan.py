from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .errors import DependencyError, VulkanError
from .system import gpu_repair, runtime_executable_name, runtime_repair

SUPPORTED_SCALES = frozenset({2, 3, 4})
FIXED_4X_MODELS = frozenset(
    {
        "realesrgan-x4plus-anime",
        "realesrgan-x4plus",
        "realesrnet-x4plus",
    }
)
ANIME_VIDEO_MODEL = "realesr-animevideov3"


@dataclass(frozen=True, slots=True)
class RuntimeFiles:
    executable: Path
    model_param: Path
    model_bin: Path


def resolve_model(model: str | None, scale: int) -> str:
    if scale not in SUPPORTED_SCALES:
        raise DependencyError("Scale must be 2, 3, or 4.")

    if model is None:
        return "realesrgan-x4plus-anime" if scale == 4 else ANIME_VIDEO_MODEL

    if model in FIXED_4X_MODELS and scale != 4:
        raise DependencyError(
            f"Model '{model}' supports only scale 4; omit --model to select the "
            f"scale-aware default, or select {ANIME_VIDEO_MODEL}."
        )
    return model


def _model_file_stem(model: str, scale: int) -> str:
    if model == ANIME_VIDEO_MODEL:
        return f"{model}-x{scale}"
    return model


def validate_runtime(tool_dir: Path, model: str, scale: int) -> RuntimeFiles:
    resolved_model = resolve_model(model, scale)
    resolved_tool_dir = tool_dir.expanduser().resolve()
    model_stem = _model_file_stem(resolved_model, scale)
    runtime = RuntimeFiles(
        executable=resolved_tool_dir / runtime_executable_name(),
        model_param=resolved_tool_dir / "models" / f"{model_stem}.param",
        model_bin=resolved_tool_dir / "models" / f"{model_stem}.bin",
    )
    missing = [
        path
        for path in (runtime.executable, runtime.model_param, runtime.model_bin)
        if not path.is_file()
    ]
    if missing:
        details = "\n".join(f"- {path}" for path in missing)
        raise DependencyError(
            "Missing official Real-ESRGAN runtime file(s):\n"
            f"{details}\n"
            f"{runtime_repair()}"
        )
    return runtime


def build_command(
    runtime: RuntimeFiles,
    input_path: Path,
    output_path: Path,
    model: str,
    scale: int,
    gpu: int | None,
) -> list[str]:
    resolved_model = resolve_model(model, scale)
    command = [
        str(runtime.executable.expanduser().resolve()),
        "-i",
        str(input_path.expanduser().resolve()),
        "-o",
        str(output_path.expanduser().resolve()),
        "-m",
        str(runtime.model_param.expanduser().resolve().parent),
        "-n",
        resolved_model,
        "-s",
        str(scale),
        "-t",
        "0",
        "-f",
        "png",
    ]
    if gpu is not None:
        command.extend(("-g", str(gpu)))
    return command


def _output_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _combined_diagnostics(result: subprocess.CompletedProcess[object]) -> str:
    return "\n".join(
        part
        for part in (_output_text(result.stdout), _output_text(result.stderr))
        if part
    )


def _last_diagnostic_line(diagnostics: str) -> str:
    lines = [line.strip() for line in diagnostics.splitlines() if line.strip()]
    return lines[-1] if lines else "No diagnostic output was produced."


def run_upscale(
    runtime: RuntimeFiles,
    input_path: Path,
    output_path: Path,
    model: str,
    scale: int,
    gpu: int | None,
    runner: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
) -> None:
    command = build_command(runtime, input_path, output_path, model, scale, gpu)
    runtime_dir = runtime.executable.expanduser().resolve().parent
    try:
        result = runner(
            command,
            cwd=runtime_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise DependencyError(
            f"Could not start realesrgan-ncnn-vulkan: {exc}. {runtime_repair()}"
        ) from exc

    if result.returncode == 0:
        return

    diagnostics = _combined_diagnostics(result)
    final_line = _last_diagnostic_line(diagnostics)
    normalized = diagnostics.lower()
    if any(
        marker in normalized
        for marker in ("vkcreate", "vulkan", "failed to create gpu")
    ):
        raise VulkanError(
            "Real-ESRGAN could not initialize Vulkan "
            f"(exit code {result.returncode}): {final_line}\n{gpu_repair()}"
        )

    raise DependencyError(
        "Real-ESRGAN failed "
        f"(exit code {result.returncode}): {final_line}\n{runtime_repair()}"
    )
