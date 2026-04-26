#!/usr/bin/env bash
cd "$(dirname "$0")"

# Load nvm so node v20+ is in PATH
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
# Fallback: add nvm node bin directly if nvm didn't set PATH
NVM_NODE=$(ls "$NVM_DIR/versions/node" 2>/dev/null | sort -V | tail -1)
[ -n "$NVM_NODE" ] && export PATH="$NVM_DIR/versions/node/$NVM_NODE/bin:$PATH"

NODE_OK=false
if command -v node &>/dev/null; then
  NODE_VER=$(node -e "process.stdout.write(process.version.slice(1).split('.')[0])" 2>/dev/null)
  [ "${NODE_VER:-0}" -ge 20 ] 2>/dev/null && NODE_OK=true
fi

if ! python3 -m venv --help &>/dev/null || ! python3 -c "import tkinter" &>/dev/null || ! command -v ffmpeg &>/dev/null; then
  echo "Installing system dependencies (needs sudo)..."
  sudo apt-get install -y python3-venv python3-tk ffmpeg
fi

if [ "$NODE_OK" = false ]; then
  echo "Installing Node.js v20+ (needs sudo)..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

if [ ! -f ".venv/bin/pip" ]; then
  echo "Creating virtual environment..."
  rm -rf .venv
  python3 -m venv .venv --copies
fi

source .venv/bin/activate
.venv/bin/pip install -U yt-dlp -q

# Download missing yt-dlp EJS lib script if needed
EJS_LIB=$(.venv/bin/python3 -c "import yt_dlp.extractor.youtube.jsc._builtin.vendor as v, os; print(os.path.dirname(v.__file__))" 2>/dev/null)
if [ -n "$EJS_LIB" ] && [ ! -f "$EJS_LIB/yt.solver.lib.js" ]; then
  EJS_VER=$(.venv/bin/python3 -c "from yt_dlp.extractor.youtube.jsc._builtin.vendor._info import VERSION; print(VERSION)" 2>/dev/null)
  echo "Downloading EJS solver script v$EJS_VER..."
  curl -fsSL "https://github.com/yt-dlp/ejs/releases/download/$EJS_VER/yt.solver.lib.js" -o "$EJS_LIB/yt.solver.lib.js" 2>/dev/null || true
fi

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
