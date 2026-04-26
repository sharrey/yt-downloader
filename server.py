#!/usr/bin/env python3
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import uuid
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.download import handler as DL
from api.proxy import handler as Proxy

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

# Temp files waiting to be served: id -> (filepath, tmpdir)
_pending = {}


class Router(DL):
    """Extends DL so self._handle/_json/_cors all exist.
    POST /api/download is overridden to download+merge with ffmpeg locally.
    GET  /api/file/<id> serves the merged temp file then deletes it."""

    def do_OPTIONS(self):
        if urlparse(self.path).path.startswith('/api/proxy'):
            Proxy.do_OPTIONS(self)
        else:
            DL.do_OPTIONS(self)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            with open(INDEX, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path.startswith('/api/file/'):
            self._serve_file(path[len('/api/file/'):])
        elif path.startswith('/api/proxy'):
            Proxy.do_GET(self)
        else:
            DL.do_GET(self)

    def do_POST(self):
        if urlparse(self.path).path == '/api/download':
            self._local_download()
        else:
            DL.do_POST(self)

    # ── local download (ffmpeg merge) ────────────────────────────────────────

    def _local_download(self):
        import yt_dlp

        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        url     = body.get('url', '').strip()
        fmt     = body.get('format', 'mp4')
        quality = body.get('quality', 'best')
        cookies = body.get('cookies', '').strip()

        if not url:
            return self._json(400, {'error': 'url required'})

        cookie_path = None
        tmpdir = tempfile.mkdtemp()
        try:
            if fmt == 'mp3':
                fmt_str = 'bestaudio/best'
            elif quality == 'best':
                fmt_str = 'bestvideo+bestaudio/best'
            else:
                fmt_str = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'

            ydl_opts = {
                'format':               fmt_str,
                'outtmpl':              os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'quiet':                True,
                'no_warnings':          True,
                'merge_output_format':  'mp4',
                'extractor_args':       {'youtube': {'player_client': ['android', 'mweb', 'ios', 'web']}},
            }
            if fmt == 'mp3':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            auto_cookies = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
            if cookies:
                fd, cookie_path = tempfile.mkstemp(suffix='.txt', dir='/tmp')
                os.write(fd, cookies.encode())
                os.close(fd)
                ydl_opts['cookiefile'] = cookie_path
            elif os.path.exists(auto_cookies):
                ydl_opts['cookiefile'] = auto_cookies

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            files = [f for f in os.listdir(tmpdir)
                     if not f.endswith('.part') and not f.endswith('.ytdl')]
            if not files:
                raise Exception('No file downloaded')

            filename = files[0]
            ext      = os.path.splitext(filename)[1].lstrip('.')
            fid      = str(uuid.uuid4())[:8]
            _pending[fid] = (os.path.join(tmpdir, filename), tmpdir)

            self._json(200, {
                'title':      info.get('title', 'video'),
                'thumbnail':  info.get('thumbnail', ''),
                'ext':        ext,
                'format':     fmt,
                'direct_url': f'/api/file/{fid}',
                'filename':   filename,
            })

        except Exception as exc:
            shutil.rmtree(tmpdir, ignore_errors=True)
            self._json(500, {'error': str(exc)})
        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.unlink(cookie_path)

    # ── serve temp file ───────────────────────────────────────────────────────

    def _serve_file(self, fid):
        entry = _pending.pop(fid, None)
        if not entry:
            self.send_response(404)
            self.end_headers()
            return

        filepath, tmpdir = entry
        try:
            size = os.path.getsize(filepath)
            ext  = os.path.splitext(filepath)[1].lstrip('.')
            name = re.sub(r'[^\w\-. ]', '_', os.path.basename(filepath))[:200]
            ct   = ('video/mp4'   if ext in ('mp4', 'mkv', 'webm') else
                    'audio/mpeg'  if ext == 'mp3' else
                    'audio/mp4'   if ext == 'm4a' else
                    'application/octet-stream')

            self.send_response(200)
            self.send_header('Content-Type',        ct)
            self.send_header('Content-Length',      str(size))
            self.send_header('Content-Disposition', f'attachment; filename="{name}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')


# ── startup ───────────────────────────────────────────────────────────────────

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 8080))
    httpd = ThreadingHTTPServer(('0.0.0.0', port), Router)
    ip    = local_ip()
    print(f'\n  YXTR running')
    print(f'  Local:   http://localhost:{port}')
    print(f'  Network: http://{ip}:{port}')
    print(f'\n  Ctrl+C to stop\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  Stopped.')
