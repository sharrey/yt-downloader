from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import tempfile


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        self._handle(
            url=qs.get('url', [''])[0].strip(),
            fmt=qs.get('format', ['mp4'])[0],
            quality=qs.get('quality', ['best'])[0],
            cookies='',
        )

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self._handle(
            url=body.get('url', '').strip(),
            fmt=body.get('format', 'mp4'),
            quality=body.get('quality', 'best'),
            cookies=body.get('cookies', '').strip(),
        )

    def _handle(self, url, fmt, quality, cookies):
        if not url:
            return self._json(400, {'error': 'url parameter is required'})

        cookie_path = None
        try:
            import yt_dlp

            if fmt == 'mp3':
                fmt_str = 'bestaudio/best'
            elif quality == 'best':
                fmt_str = 'best'
            else:
                fmt_str = f'best[height<={quality}]/best'

            ydl_opts = {
                'format':      fmt_str,
                'quiet':       True,
                'no_warnings': True,
                'extractor_args': {'youtube': {'player_client': ['ios', 'web']}},
            }

            # Write cookies to a temp file if provided
            if cookies:
                fd, cookie_path = tempfile.mkstemp(suffix='.txt', dir='/tmp')
                os.write(fd, cookies.encode())
                os.close(fd)
                ydl_opts['cookiefile'] = cookie_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            title     = info.get('title', 'video')
            thumbnail = info.get('thumbnail', '')
            ext       = info.get('ext', 'mp4' if fmt == 'mp4' else 'm4a')

            dl_url = info.get('url', '')
            if not dl_url:
                req = info.get('requested_formats') or []
                if req:
                    dl_url = req[0].get('url', '')
                elif info.get('formats'):
                    dl_url = info['formats'][-1].get('url', '')

            self._json(200, {
                'title':     title,
                'thumbnail': thumbnail,
                'url':       dl_url,
                'ext':       ext,
                'format':    fmt,
            })

        except Exception as exc:
            self._json(500, {'error': str(exc)})

        finally:
            if cookie_path and os.path.exists(cookie_path):
                os.unlink(cookie_path)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',   'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
