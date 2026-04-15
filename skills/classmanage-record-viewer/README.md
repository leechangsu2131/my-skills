# Class Record Viewer (학생 개별 기록 조회기)

수업 중 교사가 기록한 다중 학생 기록을 개인별로 분리하고 필터링해주는 뷰어 애플리케이션입니다.

## 시스템 소속 및 참조 구조 (Lineage)

앱 아키텍처의 의존성 및 출처는 다음과 같이 문서화되어 관리됩니다.

### 1. Database 및 의존 스킬 (my-skills/skills)
이 애플리케이션의 핵심 데이터(학생 기록)는 노션(Notion) 데이터베이스 원본을 기반으로 하며, 다음과 같은 파이썬 스킬에 의해 매일 동기화/가공되어 앱으로 들어옵니다.

* **동기화 원천 기술**: `util-notion-to-supabase` 스킬
  * 노션의 `class-manage` 데이터베이스 테이블을 읽어오며, 다중 선택된 Relation 학생 이름을 순수 텍스트 콤마 방식(예: "강시우, 김은우")으로 변환하여 Supabase DB에 적재합니다.
* **엑셀 추출 (Export)**: `util-supabase-to-sheet` 스킬

### 2. UI/UX 디자인 출처 (Design Reference)
이 애플리케이션의 매끄럽고 부드러운 카드 레이아웃과 CSS 퍼블리싱은 아래 디자인 산출물로부터 참고, 이식하여 구축되었습니다.

* `teacherlesson-update-app` (Figma to Code 산출물 패키지) 

## 실행 방법
```bash
npm install
npm run dev -- -p 3001
```
