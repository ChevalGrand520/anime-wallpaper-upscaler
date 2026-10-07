#!/usr/bin/env python3
"""Bounded real-inference smoke test; outputs and machine receipts stay ignored."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from anime_wallpaper_upscaler.system import resolve_target


def main() -> int:
    if sys.platform != "darwin":
        raise SystemExit("This smoke test requires macOS.")
    output_root = ROOT / "outputs" / "macos-verification"
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="run-", dir=output_root))
    source = output / "small owned demo.png"
    with Image.open(ROOT / "docs/assets/demo-source-original.png") as image:
        image.convert("RGB").resize((192, 108)).save(source)
    target, warning = resolve_target("auto")
    if warning is not None:
        print(f"Display fallback: {warning}", flush=True)
    receipt = {"platform": platform.platform(), "architecture": platform.machine(),
               "target": target, "target_warning": warning, "source_size": [192, 108],
               "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "runs": []}
    for scale in (2, 3, 4):
        directory = output / f"scale-{scale}"
        start = time.monotonic()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/upscale_wallpaper.py"),
            "--input", str(source), "--scale", str(scale), "--target", "auto", "--gpu", "auto",
            "--out-dir", str(directory), "--no-open-output"],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "cli.log").write_text(result.stdout + result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"Scale {scale} failed: {result.stdout}\n{result.stderr}")
        files = list(directory.glob("*.png")) + list(directory.glob("*.jpg"))
        dimensions = {}
        for path in files:
            with Image.open(path) as image:
                image.load()
                dimensions[path.name] = image.size
                if path.suffix == ".png":
                    assert image.size == (192 * scale, 108 * scale)
                if "wallpaper_AI" in path.name:
                    assert image.size == target
                    assert any(high > low for low, high in image.convert("RGB").getextrema())
        assert len(files) == 3, f"Expected upscale, wallpaper and comparison: {files}"
        receipt["runs"].append({"scale": scale, "exit_code": result.returncode,
            "seconds": round(time.monotonic() - start, 3), "dimensions": dimensions,
            "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
            "gpu_report": [line for line in result.stdout.splitlines() if line.startswith("GPU ")]})
        print(f"Real {scale}x passed; target {target[0]}x{target[1]}", flush=True)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Receipt: {output / 'receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
