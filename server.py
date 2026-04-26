#!/usr/bin/env python3
import os
import socket
import sys
from http.server import HTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.download import handler as DL
from api.proxy import handler as Proxy

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')


class Router(DL):
    """Extends the download handler so self._handle, self._json etc. exist,
    then routes proxy paths to Proxy methods and serves index.html at /."""

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
        elif path.startswith('/api/proxy'):
            Proxy.do_GET(self)
        else:
            DL.do_GET(self)

    def do_POST(self):
        DL.do_POST(self)

    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')


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
    port = int(os.environ.get('PORT', 8080))
    httpd = HTTPServer(('0.0.0.0', port), Router)
    ip = local_ip()
    print(f'\n  YXTR running')
    print(f'  Local:   http://localhost:{port}')
    print(f'  Network: http://{ip}:{port}')
    print(f'\n  Ctrl+C to stop\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  Stopped.')
