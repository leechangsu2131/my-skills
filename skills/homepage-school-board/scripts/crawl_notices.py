#!/usr/bin/env python3
"""
화천초등학교 게시판 크롤러
GitHub Actions에서 매일 1회 실행 -> data/notices.json 갱신
"""
import json
import re
import urllib.request
import ssl
import os
import sys
from datetime import datetime, timezone, timedelta

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── 설정 ──────────────────────────────────────────────────────────────────
DOMAIN = "https://school.gyo6.net"
SYS_ID = "hc"
MAX_POSTS = 30  # 게시판당 최대 보관 건수

BOARD_CONFIGS = [
    {
        "board_id": "notice",
        "board_name": "공지사항",
        "mi": "10219054",
        "bbs_id": "20006608",
    },
    {
        "board_id": "letter",
        "board_name": "가정통신문",
        "mi": "10219055",
        "bbs_id": "20006609",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": f"{DOMAIN}/{SYS_ID}/main.do?sysId={SYS_ID}",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

KST = timezone(timedelta(hours=9))

# ─── 크롤링 ────────────────────────────────────────────────────────────────
def fetch_html(url: str) -> str:
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        raw = r.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("euc-kr")
        except Exception:
            return raw.decode("utf-8", errors="replace")


def parse_posts(html: str, board: dict) -> list[dict]:
    posts = []
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)

    for row in rows:
        if 'bbs_tit' not in row:
            continue

        tit_m = re.search(r'data-id="(\d+)"[^>]*class="nttInfoBtn[^"]*"[^>]*>(.*?)</a>', row, re.S)
        if not tit_m:
            continue

        ntt_sn, raw_tit = tit_m.groups()
        title = re.sub(r'<[^>]+>', '', raw_tit).strip()
        title = re.sub(r'\s+', ' ', title)
        if not title:
            continue

        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        clean_tds = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', td)).strip() for td in tds]

        category = clean_tds[0] if len(clean_tds) > 0 else ""
        author = clean_tds[2].replace('작성자', '').strip() if len(clean_tds) > 2 else ""
        date_raw = clean_tds[3].replace('등록일', '').strip() if len(clean_tds) > 3 else ""
        views = clean_tds[4].replace('조회수', '').strip() if len(clean_tds) > 4 else ""

        posted_at = date_raw.replace('.', '-') if date_raw else ""

        url = (
            f"{DOMAIN}/{SYS_ID}/na/ntt/selectNttInfo.do"
            f"?mi={board['mi']}&bbsId={board['bbs_id']}&nttSn={ntt_sn}"
        )

        posts.append({
            "post_id": f"{board['board_id']}:{ntt_sn}",
            "ntt_sn": ntt_sn,
            "category": category,
            "title": title,
            "url": url,
            "posted_at": posted_at,
            "author": author,
            "views": views,
        })

    return posts


def crawl_board(board: dict) -> dict:
    url = (
        f"{DOMAIN}/{SYS_ID}/na/ntt/selectNttList.do"
        f"?mi={board['mi']}&bbsId={board['bbs_id']}"
    )
    print(f"  -> 크롤링: {board['board_name']} ({url})")
    html = fetch_html(url)
    posts = parse_posts(html, board)
    posts = posts[:MAX_POSTS]
    print(f"     게시글 {len(posts)}건 수집")
    return {
        "board_id": board["board_id"],
        "board_name": board["board_name"],
        "source_url": url,
        "posts": posts,
    }


def main():
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"[{now_kst}] 크롤링 시작")

    boards = []
    for board in BOARD_CONFIGS:
        try:
            result = crawl_board(board)
            boards.append(result)
        except Exception as e:
            print(f"  ! {board['board_name']} 오류: {e}")
            boards.append({
                "board_id": board["board_id"],
                "board_name": board["board_name"],
                "error": str(e),
                "posts": [],
            })

    output = {
        "school": "화천초등학교",
        "school_url": f"{DOMAIN}/{SYS_ID}/main.do?sysId={SYS_ID}",
        "updated_at": now_kst,
        "boards": boards,
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base_dir, "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "notices.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(b["posts"]) for b in boards)
    print(f"[완료] 총 {total}건 저장 -> {out_path}")
    return output


if __name__ == "__main__":
    main()
