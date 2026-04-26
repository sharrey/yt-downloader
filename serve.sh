#!/usr/bin/env bash
cd "$(dirname "$0")"

if ! python3 -m venv --help &>/dev/null || ! python3 -c "import tkinter" &>/dev/null; then
  echo "Installing system dependencies (needs sudo)..."
  sudo apt-get install -y python3-venv python3-tk
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install yt-dlp -q
python3 server.py
