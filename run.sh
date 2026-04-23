#!/usr/bin/env bash
cd "$(dirname "$0")"
pip install --user yt-dlp -q
python3 main.py
