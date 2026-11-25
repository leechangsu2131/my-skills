# 스킬 메타데이터 점검 결과

- **작업**: T34
- **점검일**: 2026-11-25
- **범위**: `skills/*/SKILL.md` 58개
- **제외**: `docs/templates/SKILL.md`(양식), `workflow-hub-main/projects/.../doc-indexer/SKILL.md`(프로젝트 안의 별도 스킬)
- **원칙**: 이번 작업에서는 SKILL.md를 직접 고치지 않고, 검토가 필요한 곳만 목록으로 남긴다.

## 전체 결과

| 항목 | 결과 |
|---|---|
| 점검한 SKILL.md | 58개 |
| description | 58개 모두 있음 |
| summary | 58개 모두 있음 |
| status | 58개 모두 있음 |
| status 분포 | 운영 48개 · 개발 7개 · 보관 3개 |
| summary 길이 | 1~2문장 범위에서 크게 벗어난 항목을 찾지 못함 |
| description과 summary가 같은 문장 | 11개 확인 |

## 1. description에 사용 시점·요청 예시를 보완하면 좋은 곳

아래 항목은 기능이나 프로젝트 설명은 있지만, 어떤 사용자 요청에서 이 스킬을 선택해야 하는지 분명하지 않거나 문장이 짧다. 기존 설명을 없애지 말고 첫 문장 또는 끝에 사용 상황을 덧붙이는 편이 좋다.

| 스킬 | 검토할 점 |
|---|---|
| `admin-buying-product` | 온라인 서점 장바구니 엑셀·이미지를 처리한다는 기능 설명은 있으나, 사용자가 어떤 구입 업무를 요청할 때 선택할지 추가 |
| `admin-edufine` | 에듀파인 기능 목록 중심. 품의·공문 기안·결재 대기 확인 등 요청 예시를 짧게 추가 |
| `admin-neis-bot` | 자동화 범위는 넓게 적혀 있으나, 요청 유형별로 언제 이 스킬을 호출할지 첫 문장에 명시 |
| `classmanage-exam-grader` | 시험 채점 도구 설명에 더해 시험지 채점·답안 정렬 요청에서 사용한다고 명시 |
| `classmanage-exam-graderV2` | description이 summary와 같고 사용 요청 예시가 없음 |
| `classmanage-iscream-evaluate` | 평가 페이지 자동 입력 기능은 있으나, 어떤 평가 자료를 입력하려 할 때 쓰는지 명시 |
| `classmanage-notion-sync` | Notion → Supabase 이관 기능만 설명. 이관·동기화 요청에서 사용한다고 명시 |
| `classmanage-record-viewer` | 학생별 수업 기록 보기 기능만 설명. 여러 학생 기록을 학생별로 나눠 확인할 때 사용한다고 명시 |
| `classmanage-student-classifier` | 메모 분류 기능은 있으나, 클로바노트·자유 메모를 학생별로 정리해 달라는 요청 예시를 추가 |
| `classmanage-student-eval-generator` | 평가 문장 생성 기능은 있으나, 학기말 평가 문장 작성 요청에서 사용한다고 명시 |
| `classmanage-student-photo-organizer` | 기능 설명이 짧음. 작품·활동 사진을 학생별로 정리해 달라는 요청 예시를 추가 |
| `classmanage-supabase-export` | Supabase 기록을 Excel로 내보내는 기능은 있으나, 학생별 기록 파일을 만들 때 사용한다고 명시 |
| `personal-attach-files` | AI 첨부용 파일 모으기 기능은 있으나, 프로젝트 자료를 한 번에 첨부해 달라는 요청 예시를 추가 |
| `personal-carrot` | Appium 기반 수집 시스템이라는 설명만 있음. 매물 수집·시트 기록 요청에서 사용한다고 명시 |
| `personal-chesley-morning-brief-main` | 파이프라인 설명에 더해 새 영상 요약·누락분 처리 요청에서 사용한다고 명시 |
| `personal-free-parents-app` | 앱 개발 메모라는 설명만 있음. 앱 기능 기획·디자인·개발 요청에서 사용한다고 명시 |
| `personal-library-search` | 도서 검색·희망도서 신청 기능은 있으나, Notion 도서 목록의 ISBN·도서관 소장 여부 확인 요청에서 사용한다고 명시 |
| `personal-reading-book` | 프로젝트 설명과 summary가 같음. 긴 문서 읽기·설명 요청에서 사용한다고 명시 |
| `picture-book-library` | 도서 관리 범위는 있으나, 그림책 추천·수업 연계·도서 카드 작성 요청 예시를 추가 |
| `school-todo-kakao` | 프로그램 설명에 더해 학교 일정·개인 할 일 알림 설정 또는 점검 요청에서 사용한다고 명시 |
| `teacherlesson-schedule` | 파일·기술 구성 설명 중심. 진도표·수업배치·시수 조정 요청에서 사용한다고 명시 |
| `teacherlesson-update-app` | 앱 프런트엔드라는 설명과 summary가 같고 사용 상황이 없음 |
| `teacherlesson-workspace` | 대시보드 앱 설명과 summary가 같음. 교사 도구 통합 화면을 만들거나 고칠 때 사용한다고 명시 |
| `util-discord-memo` | Discord 메모 정리 기능 설명과 summary가 같음. 채널 메모를 공지·보고서로 정리할 때 사용한다고 명시 |
| `util-edusearch-main` | 로컬 교육 자료 검색 시스템 설명과 summary가 같음. 자료 수집·검색·색인 갱신 요청에서 사용한다고 명시 |
| `util-map-time` | 지도 웹 앱 설명만 있음. Excel 장소의 이동 시간·중간 지점·경유지 비교 요청에서 사용한다고 명시 |
| `util-pdf-translator` | PDF 번역·Discord 전송 기능은 있으나, 챕터별 번역 요청에서 사용한다고 명시 |
| `util-school-print` | 한글 배치 인쇄 기능 설명만 있음. 학년·반별 안내장 일괄 인쇄 요청에서 사용한다고 명시 |
| `util-storagemap` | Supabase 웹앱 설명과 summary가 같음. 물건 위치·공간 배치 관리 화면 요청에서 사용한다고 명시 |
| `util-webtoguide` | 영어 한 줄 설명. 웹페이지, 특히 네이버 블로그를 Markdown 안내서로 바꾸려는 요청 예시를 한국어로 추가 |
| `workflow-hub-main` | 협업 도구 구성 설명과 summary가 같음. AI 역할 분담·프로젝트 템플릿·GitHub 협업 흐름을 만들 때 사용한다고 명시 |

> 위 목록은 사용 시점을 판단하기 위한 검토 후보이다. 설명에 기능이 충분히 드러나는 항목도 있으므로, 고칠 때는 실제 호출 방식과 겹치는 스킬을 확인한다.

## 2. description과 summary가 같은 곳

아래 11개는 두 필드가 사실상 같은 문장이다. description에는 사용 조건·호출 예시를, summary에는 핵심 기능만 남기면 역할이 분명해진다.

- `classmanage-exam-graderV2`
- `personal-chesley-morning-brief-main`
- `personal-free-parents-app`
- `personal-reading-book`
- `teacherlesson-update-app`
- `teacherlesson-workspace`
- `util-discord-memo`
- `util-edusearch-main`
- `util-map-time`
- `util-storagemap`
- `workflow-hub-main`

## 3. status 확인이 필요한 곳

모든 58개 파일에 status가 있고 값은 운영·개발·보관으로 구분되어 있다. 아래는 본문과 status가 모순이라고 단정한 것이 아니라, 소유자가 현재 사용 여부를 확인하면 좋은 항목이다.

| 스킬 | 현재 status | 확인할 점 |
|---|---|---|
| `personal-analyze-trade` | 보관 | description은 Codex가 포트폴리오 분석에 사용하는 스킬로 안내한다. 보관 상태가 의도된 것인지, 분석 스킬을 다시 운영할지 확인 |
| `personal-record-trade` | 보관 | description은 신규 매매 기록 입력에 사용하는 스킬로 안내한다. 보관 상태가 의도된 것인지 확인 |
| `personal-vba-book` | 보관 | 과거 VBA 크롤러와 마이그레이션 기록을 보관한다고 설명하므로 현재 status와 일치하는 것으로 보임 |
| `teacherlesson-assistant` | 개발 | 실제 수업 비서의 사용자 흐름과 기능 문서가 상세하다. 아직 개발 중인지, 운영 상태로 바꿀 시점인지 확인 |
| `util-notebooklm` | 개발 | 다른 스킬에서 공용 도구로 안내하고 있다. 개발 상태가 맞는지 확인 |

## 4. 우선 정리 순서 제안

1. **먼저 status 결정**: `personal-analyze-trade`, `personal-record-trade`, `teacherlesson-assistant`, `util-notebooklm`.
2. **description과 summary 중복 11개**: description에 사용 조건을 보충하고 summary는 한두 문장 기능 요약으로 유지.
3. **사용 시점이 불분명한 나머지 항목**: 사용자가 실제로 말할 법한 요청 예시를 한 가지씩 추가.
4. **직접 수정 전 확인**: 스킬 간 역할이 겹치거나 보관 상태가 의도된 경우에는 소유자 확인 후 수정.

## 점검 한계

- 이번 점검은 YAML 앞머리와 각 SKILL.md의 첫 부분을 읽어 메타데이터만 검토했다. 실제 코드 실행 빈도, GitHub Actions 사용 기록, 외부 서비스 연결 상태는 확인하지 않았다.
- 따라서 status는 확정 변경 대상이 아니라 소유자 확인 목록이다.
- 이번 작업에서는 58개 SKILL.md를 직접 수정하지 않았다.
