"""GET /api/ping — stdlib only, proves the Python runtime is alive."""
from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(
            {
                "ok": True,
                "entry": "api/ping.py",
                "vercel": bool(os.getenv("VERCEL")),
                "has_openai": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
                "has_database": bool((os.getenv("DATABASE_URL") or "").strip()),
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return
