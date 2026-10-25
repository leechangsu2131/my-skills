# 스킬·도구 종합 안내

> 기준일: 2026-10-25  
> 범위: 이 폴더 바로 아래의 47개 디렉터리. `SKILL.md`가 있는 35개와 README·AGENTS·코드만 있는 프로젝트/자료 폴더 12개를 함께 정리했다.  
> 버전: 아래 값은 각 폴더의 Markdown 또는 패키지 메타데이터에서 확인한 표기다. 버전 표기가 없으면 `미기재`로 적었다. 이는 폴더를 실제 실행해 최신 동작까지 검증했다는 뜻은 아니다.

## 빠른 찾기

- **학교 행정·구매**: NEIS, K-에듀파인, S2B, 학급운영비, HiTalk, 도서 구입
- **학생 기록·평가**: 관찰 기록 분류/조회/내보내기, 평가문 작성·입력, 시험 채점, 사진 정리
- **수업·교사 도구**: 지도서 PDF 분할·진도표, 수업 시간표, 사회·음악 수업 보조, 교사 대시보드, 3D 프린팅
- **개인·자료 도구**: 투자 기록/분석, 영상·오디오 노트, 도서관 검색, PDF 번역, 웹 수집, 경로·물품 위치 관리

## 학교 행정과 구매

| 폴더 | 버전 | 할 수 있는 일 |
|---|---:|---|
| `admin-buying-product` | 미기재 | 온라인 서점 장바구니의 엑셀(권장) 또는 이미지에서 도서 정보를 읽어 학교 구입 목록 엑셀에 기록한다. 이미지 입력은 목록 확인 절차가 필요하다. |
| `admin-class-buy` | 미기재 | 학급운영비 개산급 정산 행을 준비하고 영수증별 증빙 DOCX를 만든다. 규정·에듀파인 절차 참고 문서가 포함되어 있다. |
| `admin-edufine` | 미기재 | K-에듀파인 물품 품의, 공문 기안, 결재/공람 대기 문서 확인과 관련한 RPA 및 웹 대시보드를 제공한다. |
| `admin-hitalk-sender` | 미기재 | Google Sheets 명단과 템플릿으로 학생·학부모별 HiTalk 메시지를 작성한다. 미리보기·리허설 후 발송할 수 있다. |
| `admin-neis-bot` | 미기재 | NEIS 체험학습·결석 서류 접수, 출장·연수 등록, 창체/동아리 기록, 시간표 작업 등 교사 행정을 자동화한다. |
| `admin-s2b-buyer` | 미기재 | CSV/Excel 품목을 S2B에서 검색해 견적서(장바구니)에 담고 처리 결과 엑셀을 만든다. 실제 구매 확정은 범위에 포함되지 않는다. |

## 학생 기록·평가·채점

| 폴더 | 버전 | 할 수 있는 일 |
|---|---:|---|
| `classmanage-evaluate-to-neis` | 미기재 | Markdown 성취수준 배정표를 읽어 NEIS 입력 자료를 준비하고, 확인·시험 실행 뒤 입력 자동화를 수행한다. |
| `classmanage-exam-grader` | 미기재 | 로컬 시험 채점 워크스테이션. 템플릿 정렬, 학생 PDF 묶음 처리, 교사 검토, 피드백 표시 PDF 생성을 지원한다. |
| `classmanage-exam-graderV2` | 미기재 | 로컬 웹 도구로 시험지와 답안을 정렬하고 문항 영역/OCR/자동 채점을 거쳐 교사 검토 및 마킹 PDF를 만든다. `README.md` 기반 프로젝트이며 별도 `SKILL.md`는 없다. |
| `classmanage-iscream-evaluate` | 미기재 | Supabase의 학생 관찰 기록 및 평가 문장을 바탕으로 i-Scream 과목별 평가 페이지 입력을 자동화한다. |
| `classmanage-notion-sync` | 미기재 | Notion 데이터베이스의 레코드와 속성을 Supabase 테이블로 옮긴다. |
| `classmanage-record-viewer` | v0.1.0 | 여러 학생이 포함된 수업 기록을 학생별로 나눠 필터링해 보는 웹 앱이다. `README.md`와 패키지 메타데이터를 기준으로 했다. |
| `classmanage-student-classifier` | 미기재 | 클로바노트·자유 메모·폼 응답에서 학생별 기록을 분류하고 날짜/과목/분야 등을 구조화해 Notion 입력용으로 만든다. |
| `classmanage-student-eval-generator` | 미기재 | 학생 누적 기록을 바탕으로 학기말 교과 평가와 종합발달상황 문장을 생성한다. |
| `classmanage-student-photo-organizer` | 미기재 | 학생 작품·활동 사진을 학생별 폴더로 분류하고 파일명을 정리한다. |
| `classmanage-supabase-export` | 미기재 | Supabase의 다중 학생 기록을 학생별로 분리해 개인별 워크시트가 있는 Excel 파일로 내보낸다. |

## 수업·교사 도구

| 폴더 | 버전 | 할 수 있는 일 |
|---|---:|---|
| `teacher-3dprint` | 미기재 | 수업 아이디어·물체·지형을 실제 출력 가능한 STL로 설계한다. 실측 지형, 기능 부품, 식품 몰드 참고 절차와 독도 지형 예제가 있다. |
| `teacher-guide-subunit-splitter` | 미기재 | 초등 교사용 지도서 PDF의 목차·개관·지도 계획 표 등을 찾아 단원/제재/차시 단위로 분할한다. 실행 스크립트는 있으나 `SKILL.md`가 없다. |
| `teacherlesson-guide-splitter` | 미기재 | 지도서 PDF를 구조 신호에 따라 단원 또는 세부 항목으로 분할하고 그룹명을 보정한다. |
| `teacherlesson-guide-mapper` | 미기재 | 지도서 및 분할 결과에서 진도표 행을 만들고 시트 업로드용 데이터를 생성한다. |
| `teacherlesson-guide-tracker` | 미기재 | 분할기의 `groups.json`을 읽어 Notion 과목별 진도표 데이터베이스를 만든다. |
| `teacherlesson-schedule` | v1.0.0 | Google Sheets 기반 교사 수업 진도·수업 배치 관리와 자동 시간표 계획 기능을 다룬다. |
| `teacherlesson-social-helper` | 미기재 | Douclass 사회 차시 자료를 열고 자주 쓰는 수업 구성을 저장하는 반자동 도우미다. |
| `teacherlesson-music-helper` | 미기재 | Douclass 음악 자료 접근, 지도서 PDF 추출·요약과 수업 관리용 스크립트가 들어 있다. 설명용 `SKILL.md`는 없다. |
| `teacherlesson-workspace` | v0.1.0 | Supabase 등 여러 교사 도구의 데이터를 모아 보여주는 교사용 대시보드/워크스페이스 앱이다. 별도 `SKILL.md`는 없다. |
| `teacherlesson-update-app` | v0.0.1 | 초등 교사를 위한 Update 앱의 프런트엔드 코드와 가이드라인이다. 별도 `SKILL.md`는 없다. |

## 개인 생산성·자료 도구

| 폴더 | 버전 | 할 수 있는 일 |
|---|---:|---|
| `personal-analyze-trade` | 미기재 | Google Sheets 투자 기록을 읽어 포트폴리오, 수익, 비중, 섹터, 매매 신호와 전략을 분석한다. 신규 매매 입력은 `personal-record-trade` 담당이다. |
| `personal-record-trade` | 미기재 | 자연어·거래 화면 캡처 등에서 새 매매 내역을 정리해 Google Sheets 매매일지에 추가한다. |
| `personal-attach-files` | 미기재 | 프로젝트의 핵심 코드/기획 파일을 모아 AI에 첨부하기 쉬운 임시 폴더로 준비한다. |
| `personal-carrot` | 미기재 | Appium으로 Android 당근마켓 앱의 매물을 검색·수집해 Google Sheets에 기록한다. |
| `personal-free-parents-app` | 미기재 | 공동 육아 놀이터 앱 ‘같이 놀자’의 개발·디자인 통합 안내와 구현 메모를 담는다. 별도 `SKILL.md`는 없다. |
| `personal-library-search` | 미기재 | Notion 도서 목록에서 ISBN/서점 정보를 찾고 경주시립도서관 소장 여부를 확인하며, 미소장 도서 희망도서 신청 흐름을 지원한다. |
| `personal-mp3-baby` | 미기재 | 아기 잠자리동화 MP3를 한국어 타임코드 SRT로 전사해 이야기 구간을 찾아 넘길 수 있게 한다. |
| `personal-reading-book` | 미기재 | 긴 문서를 로컬 우선으로 읽고 설명하는 Reading Tutor 프로젝트의 규칙과 정리 스크립트를 담는다. `SKILL.md`는 없다. |
| `personal-vba-book` | 미기재 | 책 목록·독서 감상문 데이터와 VBA/서재 관리용 스크립트를 보관한다. 독립 스킬 설명 문서는 없다. |
| `personal-video-note` | v0.2.6 | YouTube 자막을 먼저 조회·추출하고, 권한 있는 강의 영상에서 슬라이드 캡처·타임스탬프 전사·Obsidian용 노트를 로컬 생성한다. 같은 슬라이드의 누적 공개 화면은 대표 화면으로 통합하고, 이미지 링크와 `slides/` 구성을 유지한다. 외부 AI에 영상을 자동 전송하지 않는다. |
| `personal-video-url` | 미기재 | `krcls.kr`의 기존 로그인 Chrome(CDP 9222)에서 플레이어 프레임에 노출된 미디어 URL을 확인해 CSV/Markdown으로 저장하고, 차시별 진도를 전후 비교한다. 영상은 다운로드하지 않는다. |
| `personal-youtube-gemini-kakao-automation` | 미기재 | 체슬리 모닝 브리프 YouTube 영상의 Gemini 요약 파이프라인을 실행하고 중단 기간의 요약 백로그를 처리한다. |

## 공통 유틸리티·앱·자료

| 폴더 | 버전 | 할 수 있는 일 |
|---|---:|---|
| `discord-memo-agent` | 미기재 | 현재 폴더에는 `.env`만 있어 기능·실행 방법을 확인할 Markdown/코드 설명이 없다. |
| `md` | 해당 없음 | 보안 사고와 재발 방지 내용을 기록한 `SECURITY_LESSONS_LEARNED.md` 보관 폴더다. 실행 스킬로 확인되지는 않는다. |
| `util-discord-memo` | 미기재 | Discord 메모 채널의 내용을 요약해 공지/리포트로 정리하는 대화형 워크플로를 설명한다. |
| `util-map-time` | 미기재 | Kakao 지도 기반 로컬 웹 앱. Excel 장소의 이동 거리·시간, 다대다 경로, 중간지점 및 경유지 비교를 제공한다. |
| `util-pdf-translator` | 스크립트 패키지 v1.0.0 | 영문 PDF를 챕터별로 나누고 Gemini Gems로 번역한 뒤 Discord로 보낸다. |
| `util-school-print` | 미기재 | Windows 한글(HWP) 자동화로 학년/반별 안내장을 배치 인쇄하고 반별 간지를 넣는다. |
| `util-storagemap` | 패키지 v2.1.0; README는 V3 표기 | 물건 위치와 공간별 2D 배치를 관리하는 Supabase 기반 웹앱이다. README의 V3와 `package.json` 버전 표기가 서로 다르다. |
| `util-web-scraper` | 미기재 | URL의 페이지를 수집해 EduSearch 로컬 검색 인덱스를 갱신한다. |
| `util-webtoguide` | 미기재 | 웹페이지, 특히 네이버 블로그의 글·이미지를 추출해 출처 링크가 포함된 Markdown 가이드로 변환한다. |

## 버전 표기 요약

폴더의 현재 버전을 비교할 수 있도록 버전 표기를 한 곳에 모았다. 문서에 버전이 없는 항목은 해당 폴더에 버전 번호를 새로 만들지 않았다. `util-storagemap`은 README의 제품 표기(V3)와 패키지 메타데이터(v2.1.0)가 일치하지 않아 함께 적었다.

| 표시된 버전 | 폴더 |
|---|---|
| v0.0.1 | `teacherlesson-update-app` |
| v0.1.0 | `classmanage-record-viewer`, `teacherlesson-workspace` |
| v0.2.6 | `personal-video-note` |
| v1.0.0 | `teacherlesson-schedule`, `util-pdf-translator`의 스크립트 패키지 |
| v2.1.0 / README V3 | `util-storagemap` |
| 미기재 | 나머지 폴더 |

## 정리 기준

- 폴더별 기능은 우선 `SKILL.md`를 읽고, 그 파일이 없으면 README/AGENTS 및 해당 폴더의 설명 문서를 기준으로 요약했다.
- `SKILL.md`가 없는 프로젝트/자료 폴더는 스킬과 구별해 설명했다. Markdown 설명이 없고 코드도 없는 `discord-memo-agent`는 기능 확인이 필요하다고 표시했다.
- 이 문서는 탐색용 목차다. 세부 사용 조건, 실행 명령, 입력/출력 형식, 안전 절차는 각 폴더의 `SKILL.md`와 README를 확인한다.

