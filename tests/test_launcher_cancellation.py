import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from anime_wallpaper_upscaler import launcher_run
from anime_wallpaper_upscaler.discovery import InputJob


@pytest.mark.skipif(os.name == "nt", reason="macOS launcher uses POSIX process groups")
@pytest.mark.parametrize("cancel_signal", [signal.SIGTERM, signal.SIGINT])
def test_cancel_stops_grandchild_and_removes_only_owned_outputs(tmp_path: Path, cancel_signal: int) -> None:
    root = tmp_path / 'project "quoted"'
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    ready = tmp_path / "ready"
    # Fake CLI models a completed image plus an inference child still writing.
    (scripts / "upscale_wallpaper.py").write_text(
        "import pathlib, subprocess, sys, time\n"
        "p=pathlib.Path(sys.argv[sys.argv.index('--out-dir')+1]); p.mkdir(parents=True, exist_ok=True)\n"
        "(p/'completed.png').write_bytes(b'completed')\n"
        "child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(ready)!r}).write_text(str(child.pid)+'\\n'+str(p))\n"
        "time.sleep(60)\n")
    source = tmp_path / "source"
    source.mkdir()
    (source / "input.png").write_bytes(b"original")
    output = source / "Wallpaper Upscaler Output"
    output.mkdir()
    old = output / "previous.png"
    old.write_bytes(b"keep")
    code = (
        "from pathlib import Path; from anime_wallpaper_upscaler import launcher_run as m; "
        f"m.__file__={str(root / 'anime_wallpaper_upscaler/launcher_run.py')!r}; "
        f"raise SystemExit(m.run_cancellable([{str(source)!r}],4))"
    )
    process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "worker must have produced an output and started inference"
        grandchild, run_path = ready.read_text().splitlines()
        process.send_signal(cancel_signal)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 130, stderr.decode()
        assert "deleted" in stdout.decode()
        assert not Path(run_path).exists()
        assert list(output.iterdir()) == [old]
        assert old.read_bytes() == b"keep"
        assert (source / "input.png").read_bytes() == b"original"
        # A zombie is stopped and cannot write; allow OS adoption/reaping latency.
        state = subprocess.run(["ps", "-o", "stat=", "-p", grandchild], capture_output=True, text=True).stdout.strip()
        assert not state or state.startswith("Z")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


@pytest.mark.skipif(os.name == "nt", reason="macOS-only coordinator")
def test_success_retains_unique_results_and_opens_only_final_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.png"
    source.write_bytes(b"original")
    output = tmp_path / "Wallpaper Upscaler Output"
    monkeypatch.setattr(launcher_run, "discover_jobs", lambda *a, **kw: [InputJob(source, output, output)])
    commands = []
    class Child:
        returncode = 0
        def __init__(self, arguments, **kwargs):
            commands.append(arguments)
            assert kwargs["start_new_session"]
            destination = Path(arguments[arguments.index("--out-dir") + 1])
            (destination / "result.png").write_bytes(b"done")
        def poll(self):
            return 0
    opened = []
    monkeypatch.setattr(launcher_run.subprocess, "Popen", Child)
    monkeypatch.setattr(launcher_run.subprocess, "run", lambda args, **kw: opened.append(args))
    assert launcher_run.run_cancellable([str(source)], 3) == 0
    assert launcher_run.run_cancellable([str(source)], 3) == 0
    runs = list(output.iterdir())
    assert len(runs) == 2
    assert all((run / "result.png").read_bytes() == b"done" for run in runs)
    assert len(opened) == 2
    assert all("--no-open-output" in command for command in commands)


@pytest.mark.skipif(os.name == "nt", reason="macOS symlinks/signals")
def test_cancel_refuses_to_delete_replaced_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    output = tmp_path / "output"
    unrelated = tmp_path / "user-files"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("keep")
    monkeypatch.setattr(launcher_run, "discover_jobs", lambda *a, **kw: [InputJob(source, output, output)])
    class Child:
        def __init__(self, arguments, **kwargs):
            path = Path(arguments[arguments.index("--out-dir") + 1])
            path.rmdir()
            path.symlink_to(unrelated, target_is_directory=True)
            signal.raise_signal(signal.SIGTERM)
        def poll(self):
            return 0
    monkeypatch.setattr(launcher_run.subprocess, "Popen", Child)
    stopped = []
    monkeypatch.setattr(launcher_run, "stop_process_group", lambda child: stopped.append(child))
    with pytest.raises(OSError, match="Run directory changed"):
        launcher_run.run_cancellable([str(source)], 4)
    assert stopped
    assert (unrelated / "keep.txt").read_text() == "keep"
