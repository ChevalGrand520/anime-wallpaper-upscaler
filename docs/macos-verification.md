# macOS verification

Verified locally on 2026-10-07: MacBook Air, Apple M5 (8-core GPU), 16 GB unified memory,
macOS 27.0, native arm64 Python 3.13.15, Pillow 12.3.0.

## Installation and platform behavior

- Downloaded the official `realesrgan-ncnn-vulkan-20220424-macos.zip` from Real-ESRGAN
  v0.2.5.0. Size: 51,817,124 bytes; SHA-256:
  `e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a`.
- Confirmed the executable has arm64 and x86_64 Mach-O slices. Executed the arm64 slice on M5.
- Ran `install.command --accept-upstream-license --archive <official ZIP>` successfully,
  verifying every extracted model and executable, CLI help, and actual GPU enumeration.
- Separately exercised `download_archive` over HTTPS into the ignored local cache. It
  completed the same size and SHA-256 checks. Repeated setup accepted the existing verified
  runtime; the existing Codex skill link was preserved.
- GPU probe reported `GPU 0: Apple M5`; inference used automatic selection through the
  runtime's bundled MoltenVK/Metal path.
- Automatic main-display detection returned physical **2560x1664**, rather than logical
  1470x956 points or the scaled 2940x1912 backing surface reported on this machine.
- Ran the Terminal launcher with a space-containing source path and noninteractive default
  4x selection. Processing exited 0 and opened the output directory in Finder.
- Inspected the 4x wallpaper visually: non-black image, complete source composition,
  blurred fill above/below, correct target dimensions.

The legacy upstream executable can crash if launched without its model directory. Both the
installer's probe and the CLI execute with the runtime directory as their working directory;
the CLI also passes explicit model paths. No Gatekeeper setting was changed.

## Real inference

`scripts/verify_macos.py` uses a 192x108 version of the repository-owned deterministic demo,
then invokes the normal CLI with `--target auto --gpu auto --no-open-output` at each scale.

| Scale | Default model | Upscaled PNG | Wallpaper | Result |
| --- | --- | --- | --- | --- |
| 2x | realesr-animevideov3 | 384x216 | 2560x1664 | exit 0, comparison generated |
| 3x | realesr-animevideov3 | 576x324 | 2560x1664 | exit 0, comparison generated |
| 4x | realesrgan-x4plus-anime | 768x432 | 2560x1664 | exit 0, comparison generated |

All outputs decoded successfully, matched expected dimensions, and wallpapers had nonconstant
pixel values. The first recorded warm runs took about 0.65 / 0.64 / 1.05 seconds respectively,
including the wrapper and wallpaper composition. These small-input timings are smoke-test
observations, not representative benchmarks or image-quality evidence.

Each verification run writes a separate ignored `outputs/macos-verification/run-*/` directory
containing CLI logs, outputs, and `receipt.json` with dimensions, GPU report, times, and hashes.
Run `.venv/bin/python scripts/verify_macos.py` after setup to reproduce the checks.

## Boundaries

- Local automated suite: 103 tests passed; Python compilation, shell syntax and whitespace
  checks passed. Existing Windows test fakes were made portable without changing the Windows
  installer or launcher.
- This local run proves M5/macOS 27 execution. The official binary includes Intel support,
  but an Intel Mac and other macOS versions were not tested locally.
- CI adds a macOS job with the same real 2x/3x/4x checks, alongside the existing Windows job.
  A headless cloud runner has no main display; the smoke script records the CLI's warning
  and 2560x1600 fallback explicitly. This does not establish physical-display detection there.
  Consult the PR checks for their actual remote results.
- macOS currently offers CLI and an interactive Terminal launcher, not a native Finder
  drag/drop application. Large-image performance and sustained batches were not benchmarked.
- No release asset, tag, or stable-branch merge is part of this verification.
