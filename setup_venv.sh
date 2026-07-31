#!/bin/bash
set -e
echo "Setting up Virtual Environment using system Python 3.12 with Tkinter..."
rm -rf venv
/usr/bin/python3.12 -m venv --system-site-packages venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -c "import tkinter; print('🎉 Tkinter is working perfectly in venv!')"
echo "Setup complete! You can now run: ./venv/bin/python main.py"
