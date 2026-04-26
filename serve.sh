#!/usr/bin/env bash
cd "$(dirname "$0")"

if ! python3 -m venv --help &>/dev/null || ! python3 -c "import tkinter" &>/dev/null; then
  echo "Installing system dependencies (needs sudo)..."
  sudo apt-get install -y python3-venv python3-tk
fi

if [ ! -f ".venv/bin/pip" ]; then
  echo "Creating virtual environment..."
  rm -rf .venv
  python3 -m venv .venv --copies
fi

source .venv/bin/activate
.venv/bin/pip install yt-dlp -q

if [ "$1" = "tunnel" ]; then
  .venv/bin/python3 server.py &
  SERVER_PID=$!
  trap "kill $SERVER_PID 2>/dev/null; exit" INT TERM
  echo "  Server started (pid $SERVER_PID)"
  echo "  Starting Cloudflare tunnel..."
  sleep 1
  ./cloudflared tunnel --url http://localhost:8080
  kill $SERVER_PID 2>/dev/null
else
  .venv/bin/python3 server.py
fi
