#!/usr/bin/env bash
cd "$(dirname "$0")"

# Ensure system packages needed for venv and tkinter are present
if ! python3 -m venv --help &>/dev/null || ! python3 -c "import tkinter" &>/dev/null; then
  echo "Installing system dependencies (needs sudo)..."
  sudo apt-get install -y python3-venv python3-tk
fi

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
elif [ "$1" = "tunnel" ]; then
  # Start server in background, then tunnel
  python3 server.py &
  SERVER_PID=$!
  trap "kill $SERVER_PID 2>/dev/null" EXIT
  sleep 1
  ./cloudflared tunnel --url http://localhost:8080
else
  python3 main.py
fi
