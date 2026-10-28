---
name: doc-indexer
description: ODT/PDF 공문서를 파싱하여 ChromaDB에 벡터 인덱싱하고 자연어로 검색하는 스킬
---
# 문서 인덱싱 스킬 (doc-indexer)

이 스킬은 지정 폴더의 ODT/PDF 공문서를 자동으로 읽어 벡터 DB에 저장하고, 자연어 검색을 가능하게 합니다.

## 빠른 시작

```bash
cd projects/school-agent/skills/doc-indexer/scripts
pip install -r requirements.txt
cp .env.example .env    # .env 열어서 WATCH_FOLDER 경로 설정
python3 indexer.py --once   # 인덱싱
python3 search.py "수영실기교육 예산"   # 검색 테스트
```

---

## 환경 변수 (.env 설정)

| 변수 | 설명 | 예시 |
|------|------|------|
| `WATCH_FOLDER` | 인덱싱할 공문 폴더 | `/Users/.../OneDrive/51. 체육업무` |
| `CHROMA_PATH` | ChromaDB 저장 경로 | `./chroma-db` 또는 OneDrive 경로 |
| `EMBED_MODEL` | 임베딩 모델 | `jhgan/ko-sroberta-multitask` |
| `CHUNK_SIZE` | 청크 크기 (글자) | `500` |
| `CHUNK_OVERLAP` | 청크 오버랩 | `50` |

### 💡 다른 PC에서 재인덱싱 없이 쓰는 법

`CHROMA_PATH`를 OneDrive 안 경로로 바꾸면 어느 PC에서나 재인덱싱 없이 검색이 됩니다:

```env
# .env
WATCH_FOLDER=/Users/이름/Library/CloudStorage/OneDrive-gyo6.net/51. 체육업무
CHROMA_PATH=/Users/이름/Library/CloudStorage/OneDrive-gyo6.net/ai-tools/chroma-db
```

→ 처음 한 번만 `indexer.py --once` 실행 후, 다른 PC에서는 OneDrive가 동기화되면 바로 `search.py` 사용 가능.

> ⚠️ `chroma-db/` 폴더는 개인 문서 벡터를 포함하므로 `.gitignore`에 등록되어 GitHub에 올라가지 않습니다.

---

## 실행 모드

### 모드 1: 기존 파일 1회 인덱싱
```bash
python3 indexer.py --once
```
- `WATCH_FOLDER` 안의 `.odt`, `.pdf`를 모두 스캔
- 이미 인덱싱된 파일(MD5 해시 기준)은 자동 스킵
- 완료 후 총 청크 수 출력

### 모드 2: 실시간 폴더 감시
```bash
python3 indexer.py
```
- 기존 파일 인덱싱 후, 폴더 감시 모드로 전환
- 새 파일이 복사/이동되면 자동 인덱싱
- `Ctrl+C`로 종료

### 모드 3: 자연어 검색
```bash
python3 search.py "검색어"
python3 search.py "검색어" --top 10          # 결과 수 조정
python3 search.py "검색어" --hybrid          # BM25 + Dense 하이브리드 검색
python3 search.py "검색어" --year 2026       # 연도 필터
python3 search.py "검색어" --dept 체육       # 부서 필터
python3 search.py "검색어" --year 2025 --hybrid --top 10  # 조합 사용
```

---

## 검색 예시

```bash
# 기본 검색
python3 search.py "수영실기교육 예산"

# 올해 체육 관련 스포츠클럽 대회 공문
python3 search.py "학교스포츠클럽 대회" --year 2026 --hybrid

# PAPS(건강체력평가) 관련 - 하이브리드로 키워드+의미 둘 다
python3 search.py "PAPS 건강체력평가" --hybrid --top 5

# 우리 학교 문서만 검색 (파일명에 학교명 포함 기준)
python3 search.py "육상대회 참가" --year 2025
```

---

## 참고 자료 vs 내 자료 문제

타 학교 참고 자료와 내가 최종 만든 문서가 섞여서 검색될 수 있습니다.

**해결 방법:**
1. **필터 사용**: `--year 연도` 또는 학교명 포함 파일만 보기
2. **제외 폴더 설정**: `.env`에 `EXCLUDE_PATTERNS=서울,2021 건강체력` 추가 (Cursor가 제외 로직 추가 가능)
3. **가중치 부여**: 파일명에 내 학교명(효자초/화천초) 포함 시 `is_mine=true` 메타데이터 부여

---

## 지원 파일 형식

| 형식 | 파서 | 비고 |
|------|------|------|
| `.odt` | `odfpy` | 한국 공문 주 형식 ✅ |
| `.pdf` | `pdfminer.six` | 텍스트 PDF ✅, 이미지 스캔 PDF ❌ |
| `.hwpx` | 미지원 | Phase 2에서 추가 예정 |

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `[경고] 텍스트 비어있음` | 이미지 스캔 PDF | 정상. OCR 도입 시 해결 가능 (Phase 2) |
| 검색 결과가 엉뚱한 타학교 자료 | 참고 자료가 같이 인덱싱됨 | 필터(`--year`) 사용 또는 참고 자료 폴더 제외 |
| 모델 첫 로딩이 느림 | 443MB 모델 로딩 | 두 번째부터는 캐시에서 빠르게 로딩됨 |
| `[스킵] 이미 인덱싱됨` | 중복 방지 정상 동작 | 파일 내용 변경 시 파일명 바꿔서 재인덱싱 |
