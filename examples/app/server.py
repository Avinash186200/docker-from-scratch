"""A tiny HTTP service used in the labs. Standard library only.

Endpoints:
    GET /         -> greeting and hit counter (stored in DATA_DIR, so you can see volumes work)
    GET /health   -> 200 "ok"

It handles SIGTERM, so 'docker stop' shuts it down at once instead of waiting
for the stop timeout and SIGKILL (see chapter 14).
"""

from __future__ import annotations

import os
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PORT", "8080"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/app-data"))
GREETING = os.environ.get("GREETING", "hello from a container")


def bump_counter() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    counter = DATA_DIR / "hits.txt"
    hits = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(hits))
    return hits


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/health":
            body = b"ok\n"
        elif self.path == "/":
            body = f"{GREETING} (hit {bump_counter()})\n".encode()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Log to stdout: Docker collects stdout/stderr as the container log.
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    def stop(signum, _frame):
        print(f"got signal {signum}, shutting down", flush=True)
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"listening on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
