"""Local preview server: static files from out/, and POST /shot/<name> saves a canvas capture."""
import http.server, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1] / "out"
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=str(ROOT), **k)
    def do_POST(self):
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        m = re.fullmatch(r"/shot/([A-Za-z0-9_-]+)", self.path)
        f = re.fullmatch(r"/frame/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)/(\d+)", self.path)
        if m:
            ext = "jpg" if data[:2] == bytes([255, 216]) else "png"
            (ROOT / "shots").mkdir(exist_ok=True); (ROOT / "shots" / f"{m.group(1)}.{ext}").write_bytes(data)
        elif f:
            d = ROOT / "video" / f.group(1) / f.group(2); d.mkdir(parents=True, exist_ok=True)
            (d / f"f_{int(f.group(3)):05d}.jpg").write_bytes(data)
        else:
            self.send_error(404); return
        self.send_response(204); self.end_headers()
    def do_GET(self):
        name = self.path.split("?")[0].lstrip("/")
        if name in ("director.js", "sheet.js", "app.js"):  # the sheet scripts live in sheet/, outside out/
            body = (ROOT.parent / "sheet" / name).read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/javascript"); self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body); return
        super().do_GET()
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
