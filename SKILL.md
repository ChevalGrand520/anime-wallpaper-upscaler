---
name: anime-wallpaper-upscale
description: Use when the user wants an anime, illustration, game, or wallpaper image to become clearer, sharper, higher resolution, AI-upscaled, Real-ESRGAN-enhanced, or adapted to a screen while preserving the original composition unless cropping is explicitly requested.
---

# Anime Wallpaper Upscale

This is the Agent-facing entry point for the Windows and macOS wallpaper workflow. Translate a user's
plain-language request into an explicit local wrapper command, then turn one or more
low-resolution anime-style images into screen-ready wallpapers. Files and whole folders are
supported.

The Skill is lightweight orchestration, not an inference engine. The verified official
Real-ESRGAN NCNN/Vulkan runtime and models are downloaded during first setup and perform the
actual super-resolution through ncnn and Vulkan.

Prefer faithful local Real-ESRGAN upscaling over ordinary resizing when the source is small,
blurred, compressed, or intended for a high-DPI screen.

Do not use Stable Diffusion, img2img, or other generative redraw workflows unless the user
explicitly asks for a redraw or accepts altering the original art style and details.

## Setup

On macOS with Python 3.10+, run `./install.command`. It installs a verified official universal
macOS runtime, a project `.venv`, and an optional skill symlink (preserving existing conflicts).
Read `THIRD_PARTY_NOTICES.md` before unattended setup with `--accept-upstream-license`.
Use `.venv/bin/python scripts/upscale_wallpaper.py --input "/path/to/image.png" --scale 4`.
The macOS runtime executable is `realesrgan-ncnn-vulkan` (without `.exe`), with the same model
paths. It uses bundled MoltenVK/Metal. Do not install Windows GPU drivers or disable Gatekeeper.
The Terminal launcher is `./scripts/run-wallpaper.command "/path/to/image or folder"`.
On macOS, repair missing runtime files by rerunning `./install.command`.

For ordinary Windows users, double-click `install.cmd`. The equivalent PowerShell command is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

The setup creates a project-local `.venv`, downloads and verifies the pinned official
Real-ESRGAN NCNN/Vulkan Windows release under `tools/`, registers this repository as a Codex
skill junction, and creates an optional desktop shortcut. The upstream executable and models
are downloaded automatically from their official release and are not committed to this
repository. Do not ask ordinary users to install or move upstream model files themselves.

This project is a workflow integration around Real-ESRGAN, `realesrgan-ncnn-vulkan`, and ncnn.
It does not provide an original super-resolution algorithm or model. Preserve the upstream
credits, source links, notices, and licenses when describing or redistributing the workflow.

## Workflow

1. Accept an image, several images, or one or more folders from the user.
2. Run `scripts/upscale_wallpaper.py` for deterministic official Real-ESRGAN processing.
3. Let the CLI detect the primary screen resolution and Vulkan GPU unless the user asks for
   explicit values.
4. Use scale 4 by default; preserve an explicit scale 2, 3, or 4 selection.
5. Generate an upscaled PNG, a target-size wallpaper, and a comparison image.
6. Preserve the full original composition by default. Use crop mode only when requested.
7. Keep per-input results beside their source under `Wallpaper Upscaler Output`, or use
   `--out-dir` when the user requests one shared destination.
8. Copy the recommended wallpaper to the desktop only when the user asks for easy access.

If a redraw attempt looks less faithful than the Real-ESRGAN result, prefer the non-redraw
version and say so.

## Intent Mapping

Resolve natural-language requests to explicit options before running the wrapper:

| User intent | Wrapper option |
| --- | --- |
| No scale stated | `--scale 4` |
| "2x", "3x", or "4x" | Preserve the requested `--scale` |
| No screen size stated | `--target auto` |
| A resolution such as "2560x1440" | `--target 2560x1440` |
| No GPU stated | `--gpu auto` |
| A specific Vulkan GPU ID | `--gpu ID` |
| Keep everything / no crop / preserve composition | `--mode preserve` |
| Crop to fill / cover the screen | `--mode cover`, only when cropping is explicit |
| A folder including subfolders | Repeat `--input` as needed and add `--recursive` |
| One shared destination | `--out-dir PATH` |

Do not infer `cover` merely from "fit my screen" or "make a wallpaper". Those requests keep
the default `preserve` mode and use the blurred backdrop to fill the target aspect ratio.

## Script

```powershell
.\.venv\Scripts\python.exe .\scripts\upscale_wallpaper.py `
  --input "C:\path\to\image.jpg" `
  --input "C:\path\to\wallpaper folder" `
  --scale 4
```

Use `--recursive` when folder subdirectories should also be scanned. The compatible CLI uses
`--target auto` and `--gpu auto` by default. Manual values such as `--target 2560x1600` and
`--gpu 0` remain available.

Windows users can also drag files or folders onto `scripts\run-wallpaper.cmd` or the desktop
shortcut. With no dropped paths, the launcher opens a native multi-file picker and then asks
once for scale 2, 3, or 4.

Important options:

- `--input PATH`: accepts a supported image or folder; repeat it for multiple inputs.
- `--recursive`: includes supported images in subfolders.
- `--scale 2|3|4`: selects a compatible upstream scale; the default is 4.
- `--target auto`: detects the physical primary-display resolution; pass `WIDTHxHEIGHT` to
  override it.
- `--gpu auto`: lets the official ncnn runtime choose the Vulkan GPU; pass a numeric ID to
  override it.
- `--mode preserve`: keeps the full composition and fills extra space with a blurred backdrop.
- `--mode cover`: crops to fill the target exactly; use only when cropping is accepted.
- `--out-dir PATH`: puts all batch results under one output directory.
- `--compare-full-input`: use the whole input image for the comparison without a second crop.
- `--x-bias` and `--y-bias`: adjust the crop position in cover mode.
- `--model NAME`: overrides the scale-aware upstream model selection.

## Tool Expectations

The script expects the verified official Real-ESRGAN NCNN/Vulkan runtime installed by
`install.cmd`/`setup.ps1` on Windows or `install.command` on macOS. The launcher starts setup if Python, the
executable, or any pinned model is missing. An advanced user may instead pass an existing
runtime directory with `--tool-dir` or set `REALESRGAN_TOOL_DIR`.

Required files:

- `realesrgan-ncnn-vulkan.exe`
- `models\realesrgan-x4plus-anime.param`
- `models\realesrgan-x4plus-anime.bin`

If these files are missing, rerun `install.cmd`; the installer restores them automatically.
Do not tell ordinary users to download models manually, do not silently fall back to ordinary
resizing, and do not commit downloaded binaries or model files to the repository.

## Quality Notes

- Tell the user when the original is too low-resolution for perfect recovery.
- Upscale first, then downscale to the target wallpaper size for cleaner line art.
- Avoid heavy final sharpening because it creates halos around anime line art and text.
- Use a blurred backdrop or letterbox-style composition instead of cropping unless the user asks.
