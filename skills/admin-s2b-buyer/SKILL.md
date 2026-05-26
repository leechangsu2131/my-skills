---
name: S2B 학교장터 자동 구매 시스템
description: S2B(학교장터)에서 개인이용자로 로그인하여 물품을 검색하고 견적서(장바구니)에 담는 과정을 자동화합니다
---

# S2B 학교장터 자동 구매 시스템

이 스킬은 **S2B 학교장터(s2b.kr)**에서 개인이용자로 로그인하여:

1. **물품 검색** — 필요한 물품을 키워드로 검색합니다
2. **견적서 담기** — 검색된 물품을 견적서(장바구니)에 담습니다
3. **결과 확인** — 담긴 견적서 목록을 확인하고 스크린샷을 저장합니다

> ⚠ 실제 계약/구매까지는 자동화하지 않습니다. 품의 자료 준비(견적서 담기)까지만 수행합니다.

## 필요 조건

- Python 3.8 이상
- `playwright` (브라우저 자동화)
- `requests`, `beautifulsoup4` (선택)
- S2B 개인이용자 계정

## 사용 방법

### 1. 초기 설정

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 환경 변수 세팅

`.env.example`을 `.env`로 복사 후 실제 값 입력:

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `S2B_USER_ID` | S2B 개인이용자 아이디 |
| `S2B_USER_PW` | S2B 개인이용자 비밀번호 |

### 3. 로그인 테스트

```bash
python s2b_login.py
```

### 4. 물품 검색

```bash
python s2b_buyer.py --search "A4용지"
```

### 5. 물품 구매 (견적서 담기)

```bash
# 먼저 테스트 (실제 담기 안 함)
python s2b_buyer.py --dry-run --items items.csv

# 실제 견적서 담기
python s2b_buyer.py --items items.csv
```

## 물품 목록 파일 (CSV)

`items.csv` 형식:

```csv
물품명,수량,비고
A4 복사용지 80g,10,
화이트보드 마커,20,검정
```

## 주의 사항

- S2B는 공공 전자조달 시스템이므로, 과도한 자동 접근은 삼가주세요
- `--dry-run`으로 먼저 테스트를 권장합니다
- 로그인 실패 시 `login_failed.png` 스크린샷을 확인하세요
- 보안 키보드 등 추가 인증이 있는 경우 수동 로그인이 필요할 수 있습니다

## When to Use
이 스킬은 S2B 학교장터에서 물품을 구매(품의 준비)할 때 사용합니다.
