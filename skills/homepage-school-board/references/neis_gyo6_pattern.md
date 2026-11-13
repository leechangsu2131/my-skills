# 나이스 gyo6.net 학교 홈페이지 URL/셀렉터 패턴

## URL 구조

나이스 표준 스킨(T0029 등)은 아래 패턴을 공유한다.

```
# 게시판 목록
https://<도메인>/hc/na/ntt/selectNttList.do?mi=<mi>&bbsId=<bbsId>

# 게시글 상세
https://<도메인>/hc/na/ntt/selectNttInfo.do?mi=<mi>&nttSn=<nttSn>
```

- `sysId` : 학교마다 고유 (보통 2~4자리 영문, 예: `hc`)
- `mi` : 메뉴 ID — 게시판마다 다름, 메인 HTML에서 추출
- `bbsId` : 게시판 ID (숫자 8자리 내외)
- `nttSn` : 게시글 일련번호

## 목록 HTML 셀렉터

```python
# 행 (게시글 1건)
ROW_SEL    = "table.board-list tbody tr"
# 또는 (ul 타입)
ROW_SEL    = "ul.board-list li"

TITLE_SEL  = "td.td-title a"      # 제목 + href
DATE_SEL   = "td.td-date"         # 등록일
AUTHOR_SEL = "td.td-writer"       # 작성자

# a[href] 에서 nttSn 추출
import re
m = re.search(r'nttSn=(\d+)', href)
ntt_sn = m.group(1) if m else None
```

## API 직접 호출 (일부 학교)

일부 학교는 JSON API 제공:
```
GET /hc/na/ntt/selectNttList.do?mi=<mi>&bbsId=<bbsId>&pageIndex=1&pageUnit=20
응답: HTML (일부는 JSON 없음 — HTML 파싱 필요)
```

## 학교별 차이점

| 학교 유형 | 목록 태그 | 비고 |
|---|---|---|
| gyo6.net T0029 | `table.board-list tbody tr` | 가장 일반적 |
| gyo6.net 갤러리형 | `ul.gallery-list li` | 사진 게시판 |
| 기타 나이스 | `div.board-list ul li` | 커스텀 스킨 |

## 로봇 차단 대응

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://<도메인>/hc/main.do?sysId=hc",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
```

Referer 헤더 없으면 403/에러 페이지 반환하는 경우 있음.
