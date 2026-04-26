#!/usr/bin/env bash
cd "$(dirname "$0")"
pip install --user yt-dlp -q

if [ "$1" = "server" ]; then
  python3 server.py
else
  python3 main.py
fi
