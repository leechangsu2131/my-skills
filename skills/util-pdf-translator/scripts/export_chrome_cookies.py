#!/usr/bin/env python3
"""
export_chrome_cookies.py - browser-cookie3로 Google 쿠키 추출
DPAPI 복호화 포함. Chrome 실행 중에도 동작.
"""
import json
from pathlib import Path

try:
    import browser_cookie3
except ImportError:
    print("❌ browser-cookie3가 없습니다: pip install browser-cookie3")
    import sys; sys.exit(1)

OUTPUT_PATH = Path(__file__).parent / "auth" / "google_session.json"

print("🍪 Chrome Google 쿠키 추출 중...")

jar = browser_cookie3.chrome(domain_name=".google.com")
cookies = []
for c in jar:
    cookies.append({
        "name": c.name,
        "value": c.value,
        "domain": c.domain,
        "path": c.path,
        "expires": c.expires if c.expires else -1,
        "httpOnly": False,
        "secure": c.secure,
        "sameSite": "Lax"
    })

if not cookies:
    print("⚠️  Google 쿠키가 없습니다. Chrome에서 Google 계정에 로그인 되어있어야 합니다.")
    import sys; sys.exit(1)

state = {"cookies": cookies, "origins": []}
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(f"✅ {len(cookies)}개 쿠키 추출 완료! → {OUTPUT_PATH}")
