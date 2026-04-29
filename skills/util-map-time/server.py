"""
Mini proxy server for app.html
- Reads KAKAO_API_KEY from .env
- Serves app.html at /
- Proxies Kakao API calls (hides key + avoids CORS)

Usage:
    python server.py
    -> open http://localhost:8080
"""
import os, json, urllib.parse, urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8080
ROOT = Path(__file__).parent

# ── load .env ──
env_path = ROOT / ".env"

def load_env(path):
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values

ENV = load_env(env_path)
KAKAO_API_KEY = ENV.get("KAKAO_API_KEY", "")
APP_CONFIG = {
    "home": ENV.get("DEFAULT_HOME", ""),
    "work": ENV.get("DEFAULT_WORK", ""),
    "regionCity": ENV.get("DEFAULT_REGION_CITY", ""),
    "regionProvince": ENV.get("DEFAULT_REGION_PROVINCE", ""),
    "defaultScope": ENV.get("DEFAULT_SCOPE", "city"),
}

if not KAKAO_API_KEY:
    print("[WARNING] KAKAO_API_KEY not found in .env")
else:
    print(f"[OK] Loaded KAKAO_API_KEY from .env ({KAKAO_API_KEY[:6]}...)")


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == "/":
            return str(ROOT / "app.html")
        return str(ROOT / path.lstrip("/"))

    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/config":
            self._json(200, {"apiKey": KAKAO_API_KEY, "port": PORT, "app": APP_CONFIG})
            return

        # ── Kakao proxy ──
        if parsed.path.startswith("/api/proxy/kakao/"):
            if not KAKAO_API_KEY:
                self._json(500, {"error": "KAKAO_API_KEY not configured"})
                return

            endpoint = parsed.path.replace("/api/proxy/kakao/", "")
            if endpoint == "keyword":
                target = "https://dapi.kakao.com/v2/local/search/keyword.json"
            elif endpoint == "directions":
                target = "https://apis-navi.kakaomobility.com/v1/directions"
            else:
                self._json(404, {"error": "unknown endpoint"})
                return

            target += parsed.query and ("?" + parsed.query) or ""
            req = urllib.request.Request(target)
            req.add_header("Authorization", f"KakaoAK {KAKAO_API_KEY}")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read()
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() not in ("transfer-encoding", "content-encoding"):
                            self.send_header(k, v)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body)
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(e.read())
            return

        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")


if __name__ == "__main__":
    httpd = HTTPServer(("", PORT), Handler)
    print(f"\nServer running at http://localhost:{PORT}")
    print(f"   .env loaded: {bool(KAKAO_API_KEY)}")
    print("   Press Ctrl+C to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
