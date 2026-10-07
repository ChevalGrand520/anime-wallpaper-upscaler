#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Use install.cmd on Windows." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Install Python 3.10 or newer from https://www.python.org/downloads/macos/ and rerun this installer." >&2
    exit 1
fi
exec python3 "$root/scripts/setup_macos.py" "$@"
