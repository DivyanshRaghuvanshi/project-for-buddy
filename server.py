#!/usr/bin/env python3
"""Tiny local server for Song Password.

Serves index.html and forwards /api/search to LRCLIB, so the page works even
when a browser or preview window blocks direct requests to lrclib.net.

Run:   python server.py        (or: python3 server.py)
Open:  http://localhost:8000
Only Python 3 is needed. No packages to install.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.environ.get("UPSTREAM", "https://lrclib.net").rstrip("/")
PORT = int(os.environ.get("PORT", "8000"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if parsed.path == "/api/search":
            qs = urllib.parse.parse_qs(parsed.query)
            q = (qs.get("q") or [""])[0].strip()
            if not q:
                return self._send(400, b'{"error":"missing q"}', "application/json")
            url = UPSTREAM + "/api/search?" + urllib.parse.urlencode({"q": q})
            req = urllib.request.Request(url, headers={"User-Agent": "SongPassword/1.0 (local proxy)"})
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return self._send(r.status, r.read(), "application/json")
            except urllib.error.HTTPError as e:
                return self._send(e.code, e.read() or b"{}", "application/json")
            except Exception as e:  # network down, DNS, timeout
                body = json.dumps({"error": "could not reach lrclib.net", "detail": str(e)}).encode()
                return self._send(502, body, "application/json")
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Song Password is running at http://localhost:{PORT}  (press Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
