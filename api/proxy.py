from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import urllib.request
import re

# Only proxy known video CDN hosts to prevent SSRF abuse
_ALLOWED = {
    'googlevideo.com', 'youtube.com', 'ytimg.com',
    'video.twimg.com', 'twimg.com',
    'v.redd.it', 'redd.it', 'redditmedia.com', 'redditstatic.com',
    'cdninstagram.com', 'fbcdn.net',
    'tiktokcdn.com', 'tiktok.com', 'muscdn.com', 'tiktokv.com',
    'vimeocdn.com', 'vimeo.com',
    'dailymotioncdn.com', 'dailymotion.com',
    'twitch.tv', 'twitchsvc.net', 'jtvnw.net',
}


def _host_ok(url):
    try:
        h = urlparse(url).hostname or ''
    except Exception:
        return False
    return any(h == d or h.endswith('.' + d) for d in _ALLOWED)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        url = unquote(qs.get('url', [''])[0])
        raw_name = qs.get('filename', ['video.mp4'])[0]
        filename = re.sub(r'[^\w\-. ]', '_', unquote(raw_name))[:200] or 'video.mp4'

        if not url or not _host_ok(url):
            self.send_response(400)
            self.end_headers()
            return

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
            })
            with urllib.request.urlopen(req, timeout=55) as resp:
                ct = resp.headers.get('Content-Type', 'video/mp4')
                cl = resp.headers.get('Content-Length', '')
                self.send_response(200)
                self.send_header('Content-Type', ct)
                self.send_header('Content-Disposition',
                                 f'attachment; filename="{filename}"')
                if cl:
                    self.send_header('Content-Length', cl)
                self._cors()
                self.end_headers()
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except Exception:
            self.send_response(502)
            self._cors()
            self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def log_message(self, *_):
        pass
