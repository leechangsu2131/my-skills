# -*- coding: utf-8 -*-
"""
방금 등록된 14권에 대해 개선된 지점 감지 로직으로 도서관 재검색 후 노션 업데이트
"""
import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import os

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
COL_LIBRARY = "도서관"

# 방금 등록된 14권의 제목, 저자, 노션 페이지 ID
BOOKS = [
    ("가장 사업처럼 하는 투자", "",               "330ddde1-e1df-818a-81d8-c3c78075c258"),
    ("주주 행동주의",            "",               "330ddde1-e1df-8145-a53b-e1881340c6b2"),
    ("할말하는 주주",            "",               "330ddde1-e1df-8158-84d2-d1f51f212add"),
    ("수레바퀴 아래서",          "헤르만 헤세",     "330ddde1-e1df-8184-8a9f-cf8861e9055b"),
    ("한반도 슈퍼사이클",        "",               "330ddde1-e1df-819c-9efd-fa21e17787f5"),
    ("나의 조용한 전쟁",         "",               "330ddde1-e1df-81b4-913b-f62b596acc86"),
    ("아틀라스",                 "",               "330ddde1-e1df-81e6-add1-c93c83d091bf"),
    ("생각하라 그리고 부자가 되어라", "나폴레온 힐","330ddde1-e1df-8142-9f43-d7d1dead2df9"),
    ("Fluent Forever",           "Gabriel Wyner",  "330ddde1-e1df-8137-9e80-ebdc03eb2971"),
    ("부자는 자본주의를 어떻게 읽고 있는가", "",   "330ddde1-e1df-81b0-9d13-cd3e3459d0f5"),
    ("물질의 세계",              "",               "330ddde1-e1df-8103-809a-d69d7edc1f70"),
    ("사할린 섬",                "안톤 체호프",     "330ddde1-e1df-8123-8162-ee1e1fce4497"),
    ("세컨드 브레인 전쟁",       "",               "330ddde1-e1df-8172-8ea7-f530cabd5597"),
    ("투자의 새로운 규칙",       "",               "330ddde1-e1df-8156-a5f1-e5ed452c409a"),
]

def search_kyobo(title, author):
    keyword = f"{title} {author}".strip()
    url = f"https://search.kyobobook.co.kr/search?keyword={urllib.parse.quote(keyword)}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        isbns = re.findall(r'(97[89]\d{10})', r.text)
        return isbns[0] if isbns else None
    except Exception as e:
        print(f"  교보 통신 오류: {e}")
        return None

def check_gyeongju_library(isbn):
    url = f"https://library.gyeongju.go.kr/?page_id=search_booklist&mode=tBookList&search_txt={isbn}&display=50"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.select('div.bif')
        if not items:
            return None

        found_tags = set()
        for item in items:
            text = item.get_text(separator=' ', strip=True)
            if '전자책' in text or '홈페이지' in text:
                found_tags.add('전자')
            elif '송화' in text:
                found_tags.add('송화')
            elif '단석' in text:
                found_tags.add('단석')
            elif '칠평' in text:
                found_tags.add('칠평')
            else:
                found_tags.add('시립')
        return [{'name': t} for t in found_tags] if found_tags else None
    except Exception as e:
        print(f"  도서관 통신 오류: {e}")
        return None

def update_notion(page_id, tags):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {"properties": {COL_LIBRARY: {"multi_select": tags}}}
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json=payload)
    if r.status_code != 200:
        print(f"  [노션 오류] {r.status_code}: {r.text[:100]}")

print("=" * 55)
print("▶ 14권 도서관 소장처 재검색 시작")
print("=" * 55)

for title, author, page_id in BOOKS:
    label = f"{title}" + (f" / {author}" if author else "")
    print(f"\n[{label}]")

    isbn = search_kyobo(title, author)
    if not isbn:
        print("  -> ISBN 파싱 실패")
        continue
    print(f"  ISBN: {isbn}")

    tags = check_gyeongju_library(isbn)
    if tags:
        names = [t['name'] for t in tags]
        print(f"  소장처: {names}")
        update_notion(page_id, tags)
    else:
        print("  -> 경주시립도서관 미소장")

print("\n✅ 재검색 완료!")
