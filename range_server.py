#!/usr/bin/env python3
"""Static server with Range support (needed for <video>) — serves the repo dir."""
import os, sys, socketserver, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class H(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/haya.html"          # preview root -> the player page
        return SimpleHTTPRequestHandler.do_GET(self)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.exists(path):
            return super().send_head()
        size = os.path.getsize(path)
        rng = self.headers.get("Range")
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404); return None
        if rng and rng.startswith("bytes="):
            s, _, e = rng[6:].partition("-")
            start = int(s or 0); end = int(e) if e else size - 1
            end = min(end, size - 1)
            if start > end:
                self.send_error(416); f.close(); return None
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            f.seek(start)
            self._remain = end - start + 1
        else:
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self._remain = size
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_remain", None) or 0
        while left > 0:
            chunk = source.read(min(64 * 1024, left))
            if not chunk:
                break
            try:
                self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return
            left -= len(chunk)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    root = os.path.dirname(os.path.abspath(__file__))
    H.extensions_map.update({".mp4": "video/mp4", ".webm": "video/webm", ".gif": "image/gif",
                             ".jpg": "image/jpeg", ".png": "image/png", ".js": "text/javascript",
                             ".css": "text/css", ".html": "text/html", ".srt": "text/plain"})
    class S(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True
    S(("0.0.0.0", port), H).serve_forever()
