#!/bin/bash
# Install VideoFlow as a desktop application (menu + icon + launcher).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$APP_DIR" "$ICON_DIR" "$BIN_DIR"

# Ensure venv exists so the menu entry actually launches.
if [ ! -x "$ROOT/venv/bin/python" ]; then
  echo "Creating virtual environment…"
  python3 -m venv "$ROOT/venv"
  "$ROOT/venv/bin/pip" install --upgrade pip
  "$ROOT/venv/bin/pip" install -r "$ROOT/requirements.txt"
fi

cp "$ROOT/assets/icon.png" "$ICON_DIR/videoflow.png"
cp "$ROOT/packaging/videoflow" "$BIN_DIR/videoflow"
chmod +x "$BIN_DIR/videoflow" "$ROOT/packaging/videoflow"

DESKTOP_OUT="$APP_DIR/videoflow.desktop"
sed \
  -e "s|PLACEHOLDER_EXEC|$BIN_DIR/videoflow|" \
  -e "s|PLACEHOLDER_ICON|$ICON_DIR/videoflow.png|" \
  "$ROOT/packaging/videoflow.desktop" > "$DESKTOP_OUT"
chmod +x "$DESKTOP_OUT"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed VideoFlow as a desktop app."
echo "  Menu entry : $DESKTOP_OUT"
echo "  Launcher   : $BIN_DIR/videoflow"
echo "  Icon       : $ICON_DIR/videoflow.png"
echo
echo "Find it in Applications → Sound & Video, or run:  videoflow"
