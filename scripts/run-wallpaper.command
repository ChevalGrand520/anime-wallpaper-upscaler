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
scale=4
if [[ -t 0 ]]; then
    read -r -p "Scale 2/3/4 [4]: " scale
    scale="${scale:-4}"
fi
case "$scale" in
    2|3|4) ;;
    *) echo "Scale must be 2, 3, or 4." >&2; exit 2 ;;
esac
inputs=()
for source in "$@"; do
    inputs+=(--input "$source")
done
exec "$root/.venv/bin/python" "$root/scripts/upscale_wallpaper.py" "${inputs[@]}" --scale "$scale" --target auto --gpu auto --mode preserve
