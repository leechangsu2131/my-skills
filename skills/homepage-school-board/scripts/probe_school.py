"""
학교 홈페이지(나이스 gyo6.net) 구조 사전 탐색 스크립트.
새 학교 연동 시 bbsId·mi·셀렉터를 파악하기 위해 1회 실행한다.
"""
import urllib.request
import ssl
import re
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://school.gyo6.net/hc/main.do?sysId=hc"
DOMAIN = BASE_URL.split("/hc/")[0]

ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    BASE_URL,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
)
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    html = r.read().decode("utf-8", errors="replace")

print(f"페이지 크기: {len(html):,} bytes\n")

# 1) selectNttList 패턴 (공지/가정통신문 목록)
combos = re.findall(r'selectNttList\.do\?mi=(\d+)&(?:amp;)?bbsId=(\d+)', html)
print("=== 게시판 목록 mi+bbsId ===")
seen = set()
for mi, bbs in combos:
    key = (mi, bbs)
    if key in seen:
        continue
    seen.add(key)
    url = f"{DOMAIN}/hc/na/ntt/selectNttList.do?mi={mi}&bbsId={bbs}"
    print(f"  mi={mi}  bbsId={bbs}")
    print(f"  → {url}")

# 2) 메뉴 섹션 heading 텍스트 추출 (위젯 제목)
headings = re.findall(r'class="heading"[^>]*>([^<]{2,30})<', html)
print("\n=== 위젯 제목 ===")
for h in headings:
    h = h.strip()
    if h:
        print(f"  {h}")

# 3) 갤러리/게시판 more 링크
more_links = re.findall(r'''href=["'](/hc/na/ntt/selectNttList\.do[^"']+)["']''', html)
print("\n=== 더보기 링크 ===")
for l in sorted(set(more_links)):
    print(f"  {DOMAIN}{l}")
