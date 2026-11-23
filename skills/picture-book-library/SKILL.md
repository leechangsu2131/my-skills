---
name: picture-book-library
description: 초등 그림책 수업 자료와 개인 보유 서재(도서 165권, 수업 자료 209건)를 통합 관리한다. 수업 연계 도서 추천, 도서 카드(.md) 작성, 검색 색인 및 HTML 목록을 동기화한다.
metadata:
  category: 수업·교사 도구
  status: 운영
  summary: 초등 그림책 수업 자료와 개인 서재를 연계하여 도서 추천, 카드 작성, 검색 색인 및 HTML 목록을 관리한다.
---

# 📚 picture-book-library

초등 그림책 수업 자료(PPTX, PDF, 활동지)와 개인 보유 서재(마크다운 카드 165권)를 통합 관리하고 수업에 맞게 추천·활용하는 스킬입니다.

## 저장소 위치
- **실제 데이터 폴더**: `C:\Users\lee21\OneDrive - gyo6.net\8. 그림책과 서재`

## 핵심 구성
- `서재/books/`: 도서별 마크다운 카드 (`책제목.md`, 총 165권)
- `서재/covers/`: 고화질 책 표지 이미지 (.jpg)
- `그림책/`: 수업용 PPTX, PDF, HWPX 원본 자료
- `PDF변환/`: PPTX의 PDF 변환본 (인쇄 및 LLM 업로드용)
- `그림책_색인.md`: LLM 검색/추천용 압축 색인 (총 209건)
- `그림책_목록.html`: 인터랙티브 검색 및 필터 웹 화면
- `_archive/`: 레거시 및 임시 파일 안전 보관함

## 주요 작업
1. **수업 연계 그림책 추천**: `그림책_색인.md`를 바탕으로 학년, 교과(국어, 도덕 등), 주제별 도서 및 수업 슬라이드 추천
2. **새 그림책/도서 카드 작성**: `서재/_template.md` 규격에 맞춰 `서재/books/책제목.md` 생성
3. **독서 메모 정리**: `서재/Inbox.md`에 빠른 한 줄 메모 기록
4. **목록 동기화**: `scripts/sync_library.py`를 실행하여 색인 및 HTML 목록 최신화

## 동기화 도구
```bash
python skills/picture-book-library/scripts/sync_library.py
```

## 문서
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 진행 중인 일
