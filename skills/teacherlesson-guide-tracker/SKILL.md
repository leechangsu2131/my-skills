---
name: teacher-guide-notion-tracker
description: 지도서 분할기의 groups.json을 읽어 노션 진도표 DB를 자동 생성
---

# teacher-guide-notion-tracker

교사용 지도서 PDF 분할기(`teacher-guide-subunit-splitter`)가 생성한 `groups.json` 파일을
읽어 Notion 데이터베이스 형태의 과목별 진도표를 자동으로 만들어주는 도구입니다.

## 실행 방법

```bash
cd skills/teacher-guide-notion-tracker
pip install -r requirements.txt
python app.py
```

## 사전 조건

- Notion Integration 생성 및 시크릿 키 발급
- 대상 노션 페이지에 Integration 연결(Connections 추가)
- `teacher-guide-subunit-splitter`로 생성한 `groups.json` 파일

자세한 안내는 [README.md](README.md)를 참고하세요.
