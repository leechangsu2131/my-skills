---
name: personal-vba-book
description: 과거 Excel VBA/Selenium 기반 도서 크롤러 원본과 현대적 Python 마크다운 서재 마이그레이션 아카이브를 보관한다.
metadata:
  category: 개인·생활
  status: 보관
  summary: 과거 Excel VBA 도서 크롤러 원본과 Python 마크다운 서재 마이그레이션 아카이브를 보관한다 (실운영은 picture-book-library).
---

# personal-vba-book

과거 Excel VBA + Selenium Basic 기반의 도서 크롤러 원본 데이터와, 이를 현대적인 Python 마크다운 서재 시스템으로 마이그레이션한 작업 아카이브입니다.

> 💡 **현재 실운영 안내**:  
> 마이그레이션 완료 후 실제 서재 및 그림책 수업자료 운영은 [`picture-book-library`](../picture-book-library/SKILL.md) 및 `C:\Users\lee21\OneDrive - gyo6.net\8. 그림책과 서재`에서 이루어집니다.

## 주요 포함 파일
- `yes24 isbn 검색 3 .xlsm`: 크롤링 원본 엑셀 시트 (165권 유효 데이터)
- `migrate_bookshelf.py`: Excel → Markdown 최초 마이그레이션 스크립트
- `apply_card_template.py`: 초등 수업 연계 카드 템플릿(type, topics, subjects, pptx) 일괄 변환 스크립트
- `build_library.py`: 마크다운 갤러리 및 검색 HTML 초기 생성 스크립트
- `감상문2.txt.txt.pia` / `감상문2.md.md`: 블로그 독서 후기 원본 데이터 (48건)

## 문서
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 마이그레이션 내역
- [감상문2.csv.md](감상문2.csv.md)
- [감상문2.md.md](감상문2.md.md)
