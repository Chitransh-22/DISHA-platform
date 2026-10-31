# -*- coding: utf-8 -*-
import subprocess
import time
import os
import urllib.request

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FRONTEND"))
OUT_DIR = r"C:\Users\HP\.gemini\antigravity-cli\brain\2a9b66f0-ffcc-4a0a-9ae8-8f421207a8a8\scratch"
os.makedirs(OUT_DIR, exist_ok=True)

# Start vite preview server
print("Starting vite preview...")
proc = subprocess.Popen(
    ["cmd.exe", "/c", "npm run preview -- --port 4173"],
    cwd=FRONTEND_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    # Wait for server ready
    ready = False
    for i in range(15):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://localhost:4173/") as res:
                if res.status == 200:
                    ready = True
                    break
        except Exception as e:
            pass

    if not ready:
        print("Preview server failed to start in time.")
    else:
        print("Server ready! Taking screenshots...")
        sizes = [
            (375, 800, "view_375px.png"),
            (760, 900, "view_760px.png"),
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
                "http://localhost:4173/"
            ]
            subprocess.run(cmd, timeout=15)
            print(f"Captured {fname} ({w}x{h}): {os.path.exists(out_file)}, size={os.path.getsize(out_file) if os.path.exists(out_file) else 0}")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    print("Preview server stopped.")
