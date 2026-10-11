#!/usr/bin/env python3
"""Small range-capable HTTP server for the MP4 preview."""
from __future__ import annotations

import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PORT", "3000"))


class VideoHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def translate_path(self, path: str) -> str:
        clean_path = urlsplit(path).path
        if clean_path in ("", "/"):
            clean_path = "/media/index.html"
        return super().translate_path(clean_path)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()

        try:
            file_handle = open(path, "rb")
            stat = os.fstat(file_handle.fileno())
        except OSError:
            self.send_error(404, "File not found")
            return None

        file_size = stat.st_size
        start, end = 0, file_size - 1
        range_header = self.headers.get("Range")
        status = 200

        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match or file_size == 0:
                file_handle.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return None

            first, last = match.groups()
            if not first:
                suffix_length = int(last or "0")
                if suffix_length <= 0:
                    file_handle.close()
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    return None
                start = max(0, file_size - suffix_length)
            else:
                start = int(first)
                if last:
                    end = min(int(last), file_size - 1)
            if start >= file_size or end < start:
                file_handle.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return None
            status = 206

        content_length = max(0, end - start + 1)
        file_handle.seek(start)
        self.send_response(status)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()
        self._range_remaining = content_length
        return file_handle

    def copyfile(self, source, outputfile) -> None:
        remaining = getattr(self, "_range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining > 0:
            chunk = source.read(min(128 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main() -> None:
    handler = partial(VideoHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("0.0.0.0", PORT), handler)
    print(f"Video preview listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
