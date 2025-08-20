#!/usr/bin/env bash
set -euo pipefail

# XTREME IPTV PLAYER by MY-1 – Linux installer
# Usage: bash install.sh [--run] [--desktop]
RUN_AFTER=false
MAKE_DESKTOP=false

for arg in "$@"; do
  case "$arg" in
    --run) RUN_AFTER=true ;;
    --desktop) MAKE_DESKTOP=true ;;
    *) echo "Unknown arg: $arg" ;;
  esac
done

REPO_URL="https://github.com/Cyogenus/XTREME-IPTV-PLAYER-by-MY-1.git"
APP_DIR="$HOME/XTREME-IPTV-PLAYER-by-MY-1"
VENV_DIR="$APP_DIR/.venv"

echo "==> Detecting distro..."
source /etc/os-release || true
ID_LIKE_LOWER="$(echo "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')"
ID_LOWER="$(echo "${ID:-}" | tr '[:upper:]' '[:lower:]')"

install_pkgs_debian() {
  sudo apt update
  sudo apt install -y python3 python3-venv python3-pip git vlc ffmpeg                       python3-pyqt5 qtwayland5 || true
}
install_pkgs_fedora() {
  sudo dnf install -y python3 python3-venv python3-pip git vlc ffmpeg                       python3-qt5 qt5-qtwayland || true
}
install_pkgs_arch() {
  sudo pacman -Sy --noconfirm python python-pip git vlc ffmpeg                             python-pyqt5 qt5-wayland || true
}
install_pkgs_opensuse() {
  sudo zypper refresh
  sudo zypper install -y python3 python3-pip python3-virtualenv git vlc ffmpeg-4                          python3-qt5 libqt5-qtwayland || true
}

echo "==> Installing system packages..."
if [[ "$ID_LOWER" =~ (ubuntu|debian|linuxmint|pop) || "$ID_LIKE_LOWER" =~ debian ]]; then
  install_pkgs_debian
elif [[ "$ID_LOWER" =~ (fedora|rhel|centos|rocky|almalinux) || "$ID_LIKE_LOWER" =~ rhel ]]; then
  install_pkgs_fedora
elif [[ "$ID_LOWER" =~ (arch|manjaro|endeavouros|artix) || "$ID_LIKE_LOWER" =~ arch ]]; then
  install_pkgs_arch
elif [[ "$ID_LOWER" =~ (opensuse|suse) || "$ID_LIKE_LOWER" =~ suse ]]; then
  install_pkgs_opensuse
else
  echo "!! Unrecognized distro ($ID). Attempting Debian-like packages..."
  install_pkgs_debian || true
fi

echo "==> Cloning/updating repository..."
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Setting up Python virtual environment..."
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel

echo "==> Installing Python requirements (first try via pip)..."
if [[ -f "$APP_DIR/requirements.txt" ]]; then
  if ! pip install -r "$APP_DIR/requirements.txt"; then
    echo "!! pip install failed; retrying after ensuring PyQt5 is system-installed..."
    # Try re-installing minimal deps without PyQt5 if present in requirements
    # Extract non-PyQt lines and install
    TMP_REQ="$(mktemp)"
    grep -viE '^pyqt5(|==|>=|~=|<=)' "$APP_DIR/requirements.txt" > "$TMP_REQ" || true
    pip install -r "$TMP_REQ" || true
    rm -f "$TMP_REQ"
  fi
else
  echo "No requirements.txt found; continuing..."
fi

echo "==> Locating main app script..."
APP_PY=""
# Prefer a renamed app.py if already present
if [[ -f "$APP_DIR/app.py" ]]; then
  APP_PY="$APP_DIR/app.py"
else
  # Fallback: find the original spaced filename or any .py with XTREME in name
  CANDIDATE="$(ls "$APP_DIR"/*.py 2>/dev/null | grep -i 'XTREME' | head -n1 || true)"
  if [[ -n "$CANDIDATE" ]]; then
    # Create a stable launcher name without spaces
    cp -f "$CANDIDATE" "$APP_DIR/app.py"
    APP_PY="$APP_DIR/app.py"
  else
    # Last resort: pick the first .py
    ANY_PY="$(ls "$APP_DIR"/*.py 2>/dev/null | head -n1 || true)"
    if [[ -n "$ANY_PY" ]]; then
      cp -f "$ANY_PY" "$APP_DIR/app.py"
      APP_PY="$APP_DIR/app.py"
    fi
  fi
fi

if [[ -z "$APP_PY" || ! -f "$APP_PY" ]]; then
  echo "!! Could not find the main Python script in $APP_DIR"
  exit 1
fi

echo "==> Creating run wrapper (run_xtreme.sh)..."
cat > "$APP_DIR/run_xtreme.sh" << 'EOF'
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
EOF
chmod +x "$APP_DIR/run_xtreme.sh"

if $MAKE_DESKTOP; then
  echo "==> Adding desktop launcher..."
  mkdir -p "$HOME/.local/share/applications"
  cat > "$HOME/.local/share/applications/xtreme-iptv.desktop" << EOF
[Desktop Entry]
Type=Application
Name=XTREME IPTV PLAYER by MY-1
Exec=bash -lc 'cd "$APP_DIR" && ./run_xtreme.sh'
Icon=multimedia-video-player
Terminal=false
Categories=AudioVideo;Player;
EOF
  # Try to refresh desktop database (best-effort)
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

echo "==> Done!"
echo "Repo: $APP_DIR"
echo "Run:  $APP_DIR/run_xtreme.sh"
$RUN_AFTER && exec "$APP_DIR/run_xtreme.sh" || true
