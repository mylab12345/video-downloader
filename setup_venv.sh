#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Setting up virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -c "import flask, yt_dlp; print('Dependencies OK')"
if ./venv/bin/python -c "import tkinter" 2>/dev/null; then
  echo "Tkinter is available — desktop GUI can be used when a display is present."
else
  echo "Tkinter not available — use the web GUI: ./venv/bin/python main.py --web"
fi
echo "Setup complete. Start the GUI with:"
echo "    ./venv/bin/python main.py"
