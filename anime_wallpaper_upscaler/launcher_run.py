"""Cancellable macOS launches with outputs owned by exactly one run."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

from .discovery import discover_jobs
from .errors import UpscalerError


def stop_process_group(child: subprocess.Popen[bytes]) -> None:
    # The CLI and its inference children share this dedicated session. Stop all
    # writers before deleting outputs, even if the CLI has already exited.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def run_cancellable(paths: list[str], scale: int) -> int:
    cancelled = False

    def request_cancel(signum: int, frame: object) -> None:
        nonlocal cancelled
        cancelled = True

    previous = {sig: signal.signal(sig, request_cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    run_dir: Path | None = None
    parent: Path | None = None
    parent_created = False
    identity: tuple[int, int] | None = None
    child: subprocess.Popen[bytes] | None = None
    try:
        jobs = discover_jobs([Path(p) for p in paths], recursive=False, explicit_out_dir=None)
        if cancelled:
            return 130
        parent = jobs[0].output_root
        parent_created = not parent.exists()
        parent.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        stat = run_dir.stat()
        identity = (stat.st_dev, stat.st_ino)
        print(f"This run's outputs: {run_dir}", flush=True)
        result = 0
        script = Path(__file__).resolve().parents[1] / "scripts/upscale_wallpaper.py"
        # Separate input locations prevent equally named files from overwriting
        # each other. All of them still belong to this one disposable run.
        for index, path in enumerate(paths, 1):
            if cancelled:
                break
            destination = run_dir if len(paths) == 1 else run_dir / f"input-{index}"
            arguments = [sys.executable, str(script), "--input", path, "--scale", str(scale),
                         "--target", "auto", "--gpu", "auto", "--mode", "preserve",
                         "--out-dir", str(destination), "--no-open-output"]
            child = subprocess.Popen(arguments, start_new_session=True)
            while child.poll() is None and not cancelled:
                try:
                    child.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
            if cancelled:
                stop_process_group(child)
                child = None
                break
            code = child.returncode or 0
            if code < 0:
                stop_process_group(child)
            result = max(result, code if code >= 0 else 1)
            child = None
        if not cancelled:
            subprocess.run(["/usr/bin/open", str(run_dir)], check=True)
        return 130 if cancelled else result
    except (OSError, UpscalerError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        cancelled = True
        return 2
    finally:
        try:
            if child is not None:
                stop_process_group(child)
            if cancelled and run_dir is not None:
                # Never follow a replaced directory or delete an existing output
                # root: only the directory whose inode we created belongs to us.
                stat = run_dir.lstat()
                if run_dir.is_symlink() or (stat.st_dev, stat.st_ino) != identity:
                    raise OSError(f"Run directory changed; preserved for manual review: {run_dir}")
                shutil.rmtree(run_dir)
                print("Cancelled. This run's outputs and temporary files were deleted.", flush=True)
            if cancelled and parent_created and parent is not None:
                try:
                    parent.rmdir()
                except OSError:
                    pass  # Other runs/user files must survive.
        except OSError as exc:
            print(f"Error: cancellation cleanup failed: {exc}", file=sys.stderr)
            raise
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
