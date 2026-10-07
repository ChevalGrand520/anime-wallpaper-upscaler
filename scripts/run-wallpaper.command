#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -x "$root/.venv/bin/python" || ! -x "$root/tools/realesrgan-ncnn-vulkan-20220424-macos/realesrgan-ncnn-vulkan" ]]; then
    "$root/install.command"
fi
if [[ "$#" -eq 0 ]]; then
    if [[ ! -t 0 ]]; then
        echo "Usage: ./scripts/run-wallpaper.command IMAGE_OR_FOLDER [...]" >&2
        exit 2
    fi
    read -r -p "Image or folder path (without quotes): " source
    set -- "$source"
fi
exec "$root/.venv/bin/python" "$root/scripts/macos_launcher.py" "$@"
