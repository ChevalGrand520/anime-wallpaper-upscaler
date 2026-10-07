# Third-Party Notices

Anime Wallpaper Upscaler is an independent Windows and macOS workflow wrapper. It does not contain or
claim an original super-resolution algorithm or model. Super-resolution inference is provided
by the official Real-ESRGAN NCNN/Vulkan release, which is built on upstream projects including
Real-ESRGAN, Real-ESRGAN-ncnn-vulkan, ncnn, and realsr-ncnn-vulkan.

`setup.ps1` downloads the following official release asset without modification. The executable
and model files are installed under the ignored `tools/` directory and are not distributed in
this repository:

- Release: https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0
- Asset: https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip
- SHA-256: `abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d`

`install.command` / `scripts/setup_macos.py` installs the official macOS asset from the same
release, with archive and per-file checks pinned in `upstream/realesrgan-macos.json`:

- Asset: https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip
- Size: 51,817,124 bytes
- SHA-256: `e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a`

The macOS universal executable contains arm64 and x86_64 slices and statically bundled
MoltenVK, which maps Vulkan calls to the system Metal frameworks.
[MoltenVK](https://github.com/KhronosGroup/MoltenVK) is licensed under Apache 2.0;
see its [license](https://github.com/KhronosGroup/MoltenVK/blob/main/LICENSE).
The ZIP contains `README_macos.md` but no separate LICENSE/COPYING/NOTICE file. We extract
only the pinned executable, model files, and README; sample images and video are omitted.
The legacy README suggests disabling Gatekeeper; this wrapper does not do that. Allow only
the specific verified executable through macOS Privacy & Security if needed.

The official ZIP contains `README_windows.md`, but it does not bundle a `LICENSE`, `LICENSE.txt`,
`COPYING`, or `NOTICE` file. The authoritative source and license texts are therefore linked
below; this notice does not claim that those files are present in the ZIP.

| Upstream project | Role | License and pinned text |
| --- | --- | --- |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Model/research project and official release host | BSD 3-Clause: [pinned LICENSE](https://github.com/xinntao/Real-ESRGAN/blob/685d429c81888252bdb10f56c7754baededc3823/LICENSE) |
| [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan) | Portable NCNN/Vulkan executable | MIT: [pinned LICENSE](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/blob/37026f49824c5cf84062e7c6a5dd71445dcf610f/LICENSE) |
| [ncnn](https://github.com/Tencent/ncnn) | Neural-network inference framework | BSD 3-Clause plus bundled third-party terms: [pinned full LICENSE.txt](https://github.com/Tencent/ncnn/blob/6125c9f47cd14b589de0521350668cf9d3d37e3c/LICENSE.txt) |
| [realsr-ncnn-vulkan](https://github.com/nihui/realsr-ncnn-vulkan) | Upstream NCNN/Vulkan implementation lineage | MIT: [pinned LICENSE](https://github.com/nihui/realsr-ncnn-vulkan/blob/b7f890ee2704ccea76c73d9fd4d5b3298dd1beca/LICENSE) |

The ZIP does not bundle `vulkan-1.dll`. Vulkan loader/runtime support is supplied by the user's
GPU driver. Environment information is available from the
[Khronos Vulkan Loader](https://github.com/KhronosGroup/Vulkan-Loader); it is not a bundled
component of this download.

This project's MIT license applies only to this repository's own wrapper code and documentation.
Downloaded upstream software and models remain subject to their upstream terms.
