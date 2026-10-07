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
- Large-image performance and sustained batches were not benchmarked.
- No release asset, tag, or stable-branch merge is part of this verification.

## Native launcher follow-up — 2026-10-07

- Built and locally ad-hoc signed the Swift/AppKit application using existing Command Line
  Tools. The local bundle occupies approximately 96 KB and uses the existing Python workflow.
- Through the native UI, saved 2x, reopened the application, and confirmed 2x remained selected.
  Chose a 192x108 image whose filename contains Chinese characters, quotes and `$(literal)`;
  the actual GPU result was 384x216 and wallpaper 2560x1664. Finder opened the output folder.
- Finder's **Open With > Anime Wallpaper Upscaler** sent a native document event, generated
  the same valid 2x outputs, and completed without a scale prompt. Document types include images
  and folders. Automated mouse drag attempts did not establish a successful physical drop;
  that gesture remains a manual acceptance check, distinct from the verified document handler.
- The launcher tests cover preferences, failed atomic writes, exact path forwarding, preserved
  conflicts, and a real native build/sign in a quoted project path. Full local suite: 119 passed.
- Restored the local scale to 4x after testing. CLI defaults are independent of preferences.
- The source app needs an existing compiler to build and the checkout's `.venv` to run.
  No compiler is installed automatically; the Terminal fallback remains available. No standalone
  release, notarization, or Intel GUI execution has been established.

## Cancellation follow-up — 2026-10-07

- Cancelled a real M5 4x batch of 20 repository-owned 192x108 inputs through the native
  **Cancel & Delete This Run's Outputs** button. The app and CLI/inference children exited;
  the run directory was removed, all 20 inputs survived, and a pre-existing result sentinel
  in the output root remained unchanged.
- After adding the standard Quit menu, Command-Q cancelled another real 4x batch: all 60
  test inputs and the previous result survived, the run directory disappeared, and no app,
  CLI or inference process remained. A normal one-image launch completed and opened its results.
- Automated SIGTERM/SIGINT integration checks start a CLI with both a completed output and
  a live inference child, then verify cancellation exit 130, stopped children, removal of the
  owned run directory, and preservation of original/previous files. Successful runs retain
  unique outputs and open only the final folder.
- Local full suite: 123 tests passed; native build/sign, Python compilation and whitespace
  checks passed.
- Only files inside the fresh owned run directory are disposable. Downloaded models/runtime
  remain installed. Cleanup failures report an error rather than claiming success; external
  SIGKILL/Force Quit or power loss cannot run the normal cleanup handler.
