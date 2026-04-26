#!/usr/bin/env bash
cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install/update dependencies
pip install yt-dlp -q

if [ "$1" = "server" ]; then
  python3 server.py
else
  python3 main.py
fi
