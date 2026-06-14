#!/usr/bin/env python3
"""
Local server for the Vector Search Research Radar dashboard.

Serves vsr_dashboard.html and exposes POST /refresh, which the dashboard's
Refresh button calls. Refresh runs:  vsr_radar.py -> generate_topic_map.py
-> build_combined.py  (re-pull from arXiv, re-cluster, re-project, rebuild).

A browser cannot run a local process on its own, so the button needs this
server running. Start it, then use the page it opens.

    python serve.py            # serves on http://localhost:8800 and opens it

If your network blocks the arXiv API host (export.arxiv.org), change the first
step below from "vsr_radar.py" to "arxiv_scrape.py" (the arxiv.org fallback).
"""
import http.server, socketserver, subprocess, sys, os, json, threading, webbrowser

PORT = 8800
PAGE = "vsr_dashboard.html"
STEPS = [["vsr_radar.py"], ["generate_topic_map.py"], ["build_combined.py"]]
_lock = threading.Lock()


def run_refresh():
    log = []
    for step in STEPS:
        cmd = [sys.executable] + step
        log.append("$ " + " ".join(step))
        p = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)) or ".",
                           capture_output=True, text=True)
        log.append(p.stdout.strip())
        if p.returncode != 0:
            log.append("ERROR:\n" + p.stderr.strip())
            return False, "\n".join(log)
    return True, "\n".join(log)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/" + PAGE
        return super().do_GET()

    def do_POST(self):
        if self.path != "/refresh":
            self.send_error(404); return
        if not _lock.acquire(blocking=False):
            self._json({"ok": False, "log": "A refresh is already running."}); return
        try:
            print("[refresh] running\u2026", flush=True)
            ok, log = run_refresh()
            print(log, flush=True)
            print("[refresh]", "done" if ok else "FAILED", flush=True)
            self._json({"ok": ok, "log": log})
        finally:
            _lock.release()

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # quiet default access logs
        pass


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/{PAGE}"
        print(f"Vector Search Research Radar -> {url}")
        print("Refresh button re-pulls arXiv and rebuilds the dashboard. Ctrl+C to stop.")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
