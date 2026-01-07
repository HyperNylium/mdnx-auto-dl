import os
import time
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from appdata.modules.Globals import log_manager

CONTROL_HOST = "0.0.0.0"
CONTROL_PORT = int(os.getenv("CONTROL_API_PORT", "8090"))


def _trigger_restart():
    time.sleep(0.2)
    os.kill(os.getpid(), signal.SIGTERM)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found\n")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK\n")
        return

    def do_POST(self):
        if self.path != "/restart":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found\n")
            return

        log_manager.info("Restart requested via Control API.")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Restarting\n")

        threading.Thread(target=_trigger_restart, daemon=True).start()


def start_control_api():
    server = ThreadingHTTPServer((CONTROL_HOST, CONTROL_PORT), Handler)

    def run():
        log_manager.info(f"Control API listening on {CONTROL_HOST}:{CONTROL_PORT}.")
        server.serve_forever(poll_interval=1)

    threading.Thread(target=run, daemon=True).start()
    return server
