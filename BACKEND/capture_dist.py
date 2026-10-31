# -*- coding: utf-8 -*-
import subprocess
import time
import os
import urllib.request
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import functools

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FRONTEND", "dist"))
OUT_DIR = r"C:\Users\HP\.gemini\antigravity-cli\brain\2a9b66f0-ffcc-4a0a-9ae8-8f421207a8a8\scratch"
os.makedirs(OUT_DIR, exist_ok=True)

# Start simple python http server on thread
handler = functools.partial(SimpleHTTPRequestHandler, directory=DIST_DIR)
httpd = HTTPServer(("127.0.0.1", 4173), handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
print("Python HTTP server serving FRONTEND/dist on port 4173...")

try:
    sizes = [
        (375, 800, "view_375px.png"),
        (760, 900, "view_760px.png"),
        (768, 900, "view_768px.png"),
        (770, 900, "view_770px.png"),
        (800, 900, "view_800px.png"),
        (1024, 900, "view_1024px.png")
    ]
    for w, h, fname in sizes:
        out_file = os.path.join(OUT_DIR, fname)
        cmd = [
            EDGE_PATH,
            "--headless",
            "--disable-gpu",
            f"--window-size={w},{h}",
            f"--screenshot={out_file}",
            "http://127.0.0.1:4173/"
        ]
        res = subprocess.run(cmd, timeout=15)
        print(f"Captured {fname} ({w}x{h}): {os.path.exists(out_file)}, size={os.path.getsize(out_file) if os.path.exists(out_file) else 0}")
finally:
    httpd.shutdown()
    print("Server stopped.")
