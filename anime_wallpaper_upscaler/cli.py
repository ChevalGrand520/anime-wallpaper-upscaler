from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from .discovery import InputJob, discover_jobs
from .errors import UpscalerError
from .realesrgan import resolve_model, validate_runtime
from .system import probe_gpus, resolve_gpu, resolve_target, runtime_repair
from .workflow import BatchSummary, ProcessingOptions, process_batch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOL_DIR = (
    PROJECT_ROOT / "tools" / (
        "realesrgan-ncnn-vulkan-20220424-macos" if sys.platform == "darwin"
        else "realesrgan-ncnn-vulkan-20220424-windows"
    )
)


def _unit_interval(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number from 0 to 1") from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("must be a number from 0 to 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upscale anime-style images into wallpapers. Uses the official "
            "Real-ESRGAN NCNN/Vulkan runtime."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        metavar="PATH",
        help="Image or folder to process; repeat for multiple inputs.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include images in subfolders.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        choices=(2, 3, 4),
        default=4,
        help="Real-ESRGAN upscale factor (default: 4).",
    )
    parser.add_argument(
        "--target",
        default="auto",
        metavar="auto|WIDTHxHEIGHT",
        help="Wallpaper size; auto detects the primary display (default: auto).",
    )
    parser.add_argument(
        "--gpu",
        default="auto",
        metavar="auto|ID",
        help="Vulkan GPU ID, or let ncnn choose automatically (default: auto).",
    )
    parser.add_argument(
        "--model",
        help="Upstream model name; omitted selects a scale-aware default.",
    )
    parser.add_argument(
        "--mode",
        choices=("preserve", "cover"),
        default="preserve",
        help="Preserve the full composition or crop to cover (default: preserve).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Put every result under one output directory.",
    )
    parser.add_argument(
        "--tool-dir",
        type=Path,
        help="Directory containing the official Real-ESRGAN executable and models.",
    )
    parser.add_argument(
        "--copy-desktop",
        action="store_true",
        help="Copy each finished wallpaper to the current user's Desktop.",
    )
    parser.add_argument(
        "--compare-full-input",
        action="store_true",
        help="Use the full source image in the before/after comparison.",
    )
    parser.add_argument(
        "--x-bias",
        type=_unit_interval,
        default=0.5,
        metavar="0..1",
        help="Horizontal crop position in cover mode (default: 0.5).",
    )
    parser.add_argument(
        "--y-bias",
        type=_unit_interval,
        default=0.5,
        metavar="0..1",
        help="Vertical crop position in cover mode (default: 0.5).",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Do not generate before/after comparison images.",
    )
    parser.add_argument(
        "--no-upscaled-source",
        action="store_true",
        help="Remove the source-resolution upscale after creating the wallpaper.",
    )
    parser.add_argument(
        "--no-open-output",
        action="store_true",
        help="Do not open successful output folders when processing finishes.",
    )
    return parser


def resolve_tool_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        selected = explicit
    else:
        configured = os.environ.get("REALESRGAN_TOOL_DIR", "").strip()
        selected = Path(configured) if configured else DEFAULT_TOOL_DIR
    return selected.expanduser().resolve()


def _print_progress(
    current: int,
    total: int,
    job: InputJob,
    target: tuple[int, int],
    scale: int,
) -> None:
    width, height = target
    print(
        f"[{current}/{total}] {job.source.name} | "
        f"target {width}x{height} | scale {scale}x"
    )


def _report_summary(summary: BatchSummary) -> None:
    for result in summary.results:
        print(f"SUCCESS {result.source}")
        print(f"  wallpaper: {result.wallpaper}")
        if result.comparison is not None:
            print(f"  comparison: {result.comparison}")
        if result.desktop is not None:
            print(f"  desktop: {result.desktop}")
    for source, message in summary.failures:
        print(f"FAILED {source}: {message}", file=sys.stderr)
    for log_path in summary.log_paths:
        print(f"Log: {log_path}")
    print(f"Succeeded: {summary.succeeded}")
    print(f"Failed: {summary.failed}")


def _open_successful_roots(summary: BatchSummary) -> None:
    roots = tuple(dict.fromkeys(result.output_root for result in summary.results))
    startfile = getattr(os, "startfile", None)
    if startfile is None and sys.platform != "darwin" and roots:
        print(
            "Warning: output folders can only be opened automatically on Windows or macOS.",
            file=sys.stderr,
        )
        return

    for root in roots:
        try:
            if startfile is not None:
                startfile(str(root))
            else:
                subprocess.run(["/usr/bin/open", str(root)], check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Warning: could not open output folder {root}: {exc}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        # Discover inputs first so a bad path has deterministic diagnostics even
        # when the optional upstream runtime has not been installed yet.
        jobs = discover_jobs(
            [Path(value) for value in args.input],
            recursive=args.recursive,
            explicit_out_dir=args.out_dir,
        )
        target, target_warning = resolve_target(args.target)
        model = resolve_model(args.model, args.scale)
        tool_dir = resolve_tool_dir(args.tool_dir)
        runtime = validate_runtime(tool_dir, model, args.scale)
        devices = probe_gpus(runtime.executable, runtime.executable.parent)
        gpu = resolve_gpu(args.gpu, devices)
    except UpscalerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(
            "Error: Could not start the Real-ESRGAN GPU probe: "
            f"{exc}. {runtime_repair()}",
            file=sys.stderr,
        )
        return 2

    width, height = target
    print(f"Target: {width}x{height}")
    if target_warning is not None:
        print(f"Warning: {target_warning}", file=sys.stderr)
    for device in devices:
        print(f"GPU {device.id}: {device.name}")
    print("GPU selection: automatic" if gpu is None else f"GPU selection: {gpu}")

    options = ProcessingOptions(
        runtime=runtime,
        model=model,
        scale=args.scale,
        target=target,
        mode=args.mode,
        gpu=gpu,
        compare=not args.no_compare,
        keep_upscaled=not args.no_upscaled_source,
        compare_full_input=args.compare_full_input,
        x_bias=args.x_bias,
        y_bias=args.y_bias,
        copy_desktop=args.copy_desktop,
    )
    summary = process_batch(
        jobs,
        options,
        progress=lambda current, total, job: _print_progress(
            current, total, job, target, args.scale
        ),
    )
    _report_summary(summary)
    if not args.no_open_output:
        _open_successful_roots(summary)
    return summary.exit_code
