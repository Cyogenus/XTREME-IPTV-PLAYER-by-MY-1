#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
# Wayland fallback if needed:
export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-wayland}
python "$SCRIPT_DIR/app.py" || {
  echo "App failed with QT on Wayland; retrying with XCB..."
  export QT_QPA_PLATFORM=xcb
  python "$SCRIPT_DIR/app.py"
}
