#!/bin/bash
# =============================================================================
# build-deb.sh — Build the video-downloader .deb from the current source tree.
#
# Run this AFTER any code change so the packaged app always matches the repo:
#     bash packaging/build-deb.sh            # builds version 1.0.2 (or $VERSION)
#     VERSION=1.1.0 bash packaging/build-deb.sh
#
# What it guarantees:
#   * The venv is built from a Tkinter-capable Python (so the desktop GUI works)
#   * ALL runtime packages (yt-dlp, flask, requests, pillow, imageio-ffmpeg)
#     are installed by postinst, so the app loads with no missing modules
#   * The current source (main.py, gui.py, web.py, ...) is bundled
#   * The launcher forces the native desktop window (--gui), falling back to
#     the web UI only when no display is available
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-${1:-1.0.2}}"
OUT="$ROOT/video-downloader_${VERSION}_all.deb"
BUILD="$(mktemp -d)"
APP_DEST="$BUILD/usr/share/video-downloader"

echo "Building $OUT from $ROOT"

mkdir -p "$BUILD/DEBIAN"
mkdir -p "$BUILD/usr/bin"
mkdir -p "$APP_DEST"
mkdir -p "$BUILD/usr/share/applications"
mkdir -p "$BUILD/usr/share/pixmaps"

# ---- App source (current repo versions) -------------------------------------
cp "$ROOT/main.py" "$ROOT/gui.py" "$ROOT/cli.py" "$ROOT/downloader.py" \
   "$ROOT/web.py" "$ROOT/requirements.txt" "$APP_DEST/"
cp -r "$ROOT/assets" "$APP_DEST/assets"
cp -r "$ROOT/static" "$ROOT/templates" "$APP_DEST/"

# ---- Launchers --------------------------------------------------------------
cat > "$BUILD/usr/bin/video-downloader" <<'EOF'
#!/usr/bin/env python3
"""Video Downloader GUI Launcher (installed via .deb).

Opens the native desktop (tkinter) window. If no display / tkinter is
available it gracefully falls back to the web UI (handled inside main.py).
"""
import sys
import os

VENV_PYTHON = "/usr/share/video-downloader/venv/bin/python"
APP_DIR = "/usr/share/video-downloader"

if __name__ == "__main__":
    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)
    os.execvp(VENV_PYTHON, [VENV_PYTHON, "main.py", "--gui"] + sys.argv[1:])
EOF

cat > "$BUILD/usr/bin/video-downloader-cli" <<'EOF'
#!/usr/bin/env python3
"""Video Downloader CLI Launcher (installed via .deb)."""
import sys
import os

VENV_PYTHON = "/usr/share/video-downloader/venv/bin/python"
APP_DIR = "/usr/share/video-downloader"

if __name__ == "__main__":
    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)
    os.execvp(VENV_PYTHON, [VENV_PYTHON, "cli.py"] + sys.argv[1:])
EOF

# ---- Desktop entry + icon ---------------------------------------------------
cat > "$BUILD/usr/share/applications/video-downloader.desktop" <<'EOF'
[Desktop Entry]
Name=Video Downloader
Comment=Modern Video Downloader with Glassmorphism UI
Exec=/usr/bin/video-downloader
Icon=video-downloader
Terminal=false
Type=Application
Categories=AudioVideo;Utility;
Keywords=video;downloader;youtube;tiktok;instagram;
EOF

# Use the repo icon if present, else fall back to the existing xpm.
if [ -f "$ROOT/assets/icon.png" ]; then
    cp "$ROOT/assets/icon.png" "$BUILD/usr/share/pixmaps/video-downloader.png"
    sed -i 's/^Icon=.*/Icon=video-downloader.png/' "$BUILD/usr/share/applications/video-downloader.desktop"
fi
if [ -f "$ROOT/assets/icon.xpm" ]; then
    cp "$ROOT/assets/icon.xpm" "$BUILD/usr/share/pixmaps/video-downloader.xpm"
fi

# ---- Control file -----------------------------------------------------------
cat > "$BUILD/DEBIAN/control" <<EOF
Package: video-downloader
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-tk, python3-venv, ffmpeg, aria2
Maintainer: VideoFlow Team <support@videoflow.local>
Description: Modern Video Downloader with Glassmorphism UI
 A beautiful, modern desktop video downloader supporting 4K, 8K, HDR, 1080p
 and audio-only from YouTube, TikTok, Instagram, Twitter/X, Vimeo, and 1000+ sites.
 Features include:
 - Glassmorphism + minimalist design
 - Native desktop (tkinter) window
 - Concurrent fragment downloads for fast speeds
 - aria2c integration for maximum throughput
 - Smart retry logic with exponential backoff
 .
 This package includes:
 - GUI application (video-downloader)
 - CLI tool (video-downloader-cli)
 - Automatic virtual environment setup (built from a Tkinter-capable Python)
EOF

# ---- postinst (builds venv from a Tkinter-capable Python) -------------------
cat > "$BUILD/DEBIAN/postinst" <<'EOF'
#!/bin/bash
# Post-installation script for video-downloader package
set -e

echo "📦 Setting up video-downloader..."

APP_DIR="/usr/share/video-downloader"
VENV_PATH="$APP_DIR/venv"

# Pick a Python 3 that actually has Tkinter bindings. The default `python3`
# on some boxes (e.g. a custom-built /usr/local/python3) lacks the _tkinter
# module, which breaks the desktop GUI. Prefer the system Python (typically
# /usr/bin/python3, i.e. 3.12 on Mint) and fall back to any python3 that can
# import tkinter, then build the virtualenv from it.
PYTHON_BIN=""
for candidate in /usr/bin/python3 "$(command -v python3)"; do
    [ -z "$candidate" ] && continue
    if "$candidate" -c "import tkinter" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ No Python 3 with Tkinter support was found." >&2
    echo "   Install it with:  sudo apt-get install -y python3-tk" >&2
    exit 1
fi

echo "Using Python with Tkinter: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

echo "Creating isolated Python environment..."
rm -rf "$VENV_PATH"
"$PYTHON_BIN" -m venv "$VENV_PATH"

echo "Installing Python packages (yt-dlp, flask, pillow, requests, imageio-ffmpeg)..."
"$VENV_PATH/bin/pip" install --upgrade pip -q
"$VENV_PATH/bin/pip" install -r "$APP_DIR/requirements.txt" -q

chmod +x /usr/bin/video-downloader
chmod +x /usr/bin/video-downloader-cli

update-desktop-database 2>/dev/null || true

echo ""
echo "✅ Installation complete!"
echo ""
echo "  To launch the GUI (native desktop window):"
echo "    • From terminal: video-downloader"
echo "    • From menu: Applications > Audio & Video > Video Downloader"
echo ""
echo "  To use the CLI:  video-downloader-cli <URL>"
EOF

# ---- prerm ------------------------------------------------------------------
cat > "$BUILD/DEBIAN/prerm" <<'EOF'
#!/bin/bash
# Pre-removal script for video-downloader package
echo "Removing video-downloader..."
if [ -d "/usr/share/video-downloader/venv" ]; then
    rm -rf /usr/share/video-downloader/venv
fi
echo "Cleanup complete."
EOF

chmod +x "$BUILD/DEBIAN/postinst" "$BUILD/DEBIAN/prerm"
chmod +x "$BUILD/usr/bin/video-downloader" "$BUILD/usr/bin/video-downloader-cli"

# ---- Build ------------------------------------------------------------------
fakeroot dpkg-deb --build "$BUILD" "$OUT"
rm -rf "$BUILD"
echo "✅ Built $OUT"
