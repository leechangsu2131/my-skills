# 스킬 카탈로그

> 이 파일은 `python tools/build_catalog.py`로 자동 생성된다. 직접 고치지 말고 각 스킬의 `SKILL.md` 앞머리(`metadata`)를 고친 뒤 다시 실행한다.
> 생성일: 2026-11-28 · 스킬 62개

## 빠른 찾기

- [🏫 학교 행정](#학교-행정) — 10개
- [📝 학생 기록·평가](#학생-기록평가) — 11개
- [📚 수업·교사 도구](#수업교사-도구) — 11개
- [🌐 홈페이지](#홈페이지) — 1개
- [👤 개인·생활](#개인생활) — 16개
- [🛠️ 공통 유틸](#공통-유틸) — 13개

## 학교 행정

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `admin-buying-product` | ✅ 운영 | - | 온라인 서점 장바구니의 엑셀(권장) 또는 이미지에서 도서 정보를 읽어 학교 구입 목록 엑셀에 기록한다. 이미지 입력은 목록 확인 절차가 필요하다. | [SKILL](skills/admin-buying-product/SKILL.md) · [이슈](skills/admin-buying-product/ISSUES.md) |
| `admin-class-buy` | ✅ 운영 | - | 학급운영비 개산급 정산 행을 준비하고 영수증별 증빙 DOCX를 만든다. 규정·에듀파인 절차 참고 문서가 포함되어 있다. | [SKILL](skills/admin-class-buy/SKILL.md) · [이슈](skills/admin-class-buy/ISSUES.md) |
| `admin-edufine` | ✅ 운영 | - | K-에듀파인 물품 품의, 공문 기안, 결재/공람 대기 문서 확인과 관련한 RPA 및 웹 대시보드를 제공한다. | [SKILL](skills/admin-edufine/SKILL.md) · [이슈](skills/admin-edufine/ISSUES.md) 🔵4 · [README](skills/admin-edufine/README.md) |
| `admin-gbetalk` | ✅ 운영 | - | 지비톡(경북교육청 업무 메신저)에서 받은 쪽지를 날짜·발신자와 함께 로컬 Markdown으로 보관·요약하고, 지비톡 문자(SMS) 창을 9222 Chrome에서 열어 문자를 채우고 확인 후 발송한다. 쪽지 답장은 하지 않는다. | [SKILL](skills/admin-gbetalk/SKILL.md) · [이슈](skills/admin-gbetalk/ISSUES.md) 🔵3 · [README](skills/admin-gbetalk/README.md) |
| `admin-google-profile-picture` | 🔧 개발 | v0.1.0 | 학생별 Chrome 프로필을 만들고 Google 계정 프로필 사진을 설정한다. | [SKILL](skills/admin-google-profile-picture/SKILL.md) · [이슈](skills/admin-google-profile-picture/ISSUES.md) |
| `admin-hitalk-sender` | ✅ 운영 | - | Google Sheets 명단과 템플릿으로 학생·학부모별 HiTalk 메시지를 작성한다. 미리보기·리허설 후 발송할 수 있다. | [SKILL](skills/admin-hitalk-sender/SKILL.md) · [이슈](skills/admin-hitalk-sender/ISSUES.md) |
| `admin-neis-bot` | ✅ 운영 | - | NEIS 체험학습·결석 서류 접수, 출장·연수 등록, 창체/동아리 기록, 시간표 작업 등 교사 행정을 자동화한다. | [SKILL](skills/admin-neis-bot/SKILL.md) · [이슈](skills/admin-neis-bot/ISSUES.md) 🔵2 |
| `admin-s2b-buyer` | ✅ 운영 | - | S2B에서 전국 최저가 검색·상세 비교·견적서 담기/삭제·에듀파인 연계 엑셀 받기를 사용자 Chrome으로 하고, 에듀파인 품의(admin-edufine)로 넘긴다. 실제 계약·구매 확정은 하지 않는다. | [SKILL](skills/admin-s2b-buyer/SKILL.md) · [이슈](skills/admin-s2b-buyer/ISSUES.md) |
| `admin-school-facility` | 🔧 개발 | 0.2.0 | 구글 시트로 학교 기물 대장·공간(특별실·강당 등) 교시별 사용 신청·기물 대여를 관리하고, 3D 건물 화면으로 현황을 보여 주는 Apps Script 웹앱을 만든다. 카카오톡 챗봇(스쿨투두 채널 공유)으로 대여·반납·예약도 된다. | [SKILL](skills/admin-school-facility/SKILL.md) · [이슈](skills/admin-school-facility/ISSUES.md) 🔵1 |
| `school-todo-kakao` | ✅ 운영 | - | 학교 공용 일정 시트와 내가 직접 적은 할 일을 **내 일정DB 시트 한 곳**에 모으고, 평일 아침마다 그날 일정을 카카오톡 **나에게 보내기**로 알려 주는 작은 파이썬 프로그램입니다. | [SKILL](skills/school-todo-kakao/SKILL.md) · [이슈](skills/school-todo-kakao/ISSUES.md) 🔵3 · [README](skills/school-todo-kakao/README.md) |

## 학생 기록·평가

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `classmanage-evaluate-to-neis` | ✅ 운영 | - | Markdown 성취수준 배정표를 읽어 NEIS 입력 자료를 준비하고, 확인·시험 실행 뒤 입력 자동화를 수행한다. | [SKILL](skills/classmanage-evaluate-to-neis/SKILL.md) · [이슈](skills/classmanage-evaluate-to-neis/ISSUES.md) |
| `classmanage-exam-grader` | ✅ 운영 | - | 로컬 시험 채점 워크스테이션. 템플릿 정렬, 학생 PDF 묶음 처리, 교사 검토, 피드백 표시 PDF 생성을 지원한다. | [SKILL](skills/classmanage-exam-grader/SKILL.md) · [이슈](skills/classmanage-exam-grader/ISSUES.md) · [README](skills/classmanage-exam-grader/README.md) |
| `classmanage-exam-graderV2` | ✅ 운영 | - | 로컬 웹 도구로 시험지와 답안을 정렬하고 문항 영역/OCR/자동 채점을 거쳐 교사 검토 및 마킹 PDF를 만든다. | [SKILL](skills/classmanage-exam-graderV2/SKILL.md) · [이슈](skills/classmanage-exam-graderV2/ISSUES.md) · [README](skills/classmanage-exam-graderV2/README.md) |
| `classmanage-iscream-evaluate` | ✅ 운영 | - | Supabase의 학생 관찰 기록 및 평가 문장을 바탕으로 i-Scream 과목별 평가 페이지 입력을 자동화한다. | [SKILL](skills/classmanage-iscream-evaluate/SKILL.md) · [이슈](skills/classmanage-iscream-evaluate/ISSUES.md) |
| `classmanage-notion-sync` | ✅ 운영 | - | Notion 데이터베이스의 레코드와 속성을 Supabase 테이블로 옮긴다. | [SKILL](skills/classmanage-notion-sync/SKILL.md) · [이슈](skills/classmanage-notion-sync/ISSUES.md) |
| `classmanage-record-viewer` | ✅ 운영 | v0.1.0 | 여러 학생이 포함된 수업 기록을 학생별로 나눠 필터링해 보는 웹 앱이다. | [SKILL](skills/classmanage-record-viewer/SKILL.md) · [이슈](skills/classmanage-record-viewer/ISSUES.md) · [README](skills/classmanage-record-viewer/README.md) |
| `classmanage-student-classifier` | ✅ 운영 | - | 클로바노트·자유 메모·폼 응답에서 학생별 기록을 분류하고 날짜/과목/분야 등을 구조화해 Notion 입력용으로 만든다. | [SKILL](skills/classmanage-student-classifier/SKILL.md) · [이슈](skills/classmanage-student-classifier/ISSUES.md) |
| `classmanage-student-eval-generator` | ✅ 운영 | - | 학생 누적 기록을 바탕으로 학기말 교과 평가와 종합발달상황 문장을 생성한다. | [SKILL](skills/classmanage-student-eval-generator/SKILL.md) · [이슈](skills/classmanage-student-eval-generator/ISSUES.md) |
| `classmanage-student-photo-organizer` | ✅ 운영 | - | 학생 작품·활동 사진을 학생별 폴더로 분류하고 파일명을 정리한다. | [SKILL](skills/classmanage-student-photo-organizer/SKILL.md) · [이슈](skills/classmanage-student-photo-organizer/ISSUES.md) |
| `classmanage-supabase-export` | ✅ 운영 | - | Supabase의 다중 학생 기록을 학생별로 분리해 개인별 워크시트가 있는 Excel 파일로 내보낸다. | [SKILL](skills/classmanage-supabase-export/SKILL.md) · [이슈](skills/classmanage-supabase-export/ISSUES.md) |
| `photo-organizer` | ✅ 운영 | - | 활동 사진 폴더의 EXIF 제작 날짜를 인식해 폴더명에 날짜(또는 기간)를 붙이고, 중복 사진(MD5) 제거 및 자동 생성 파일명을 `활동명_YYYYMMDD_반_순번`으로 일괄 정리한다. | [SKILL](skills/photo-organizer/SKILL.md) · [이슈](skills/photo-organizer/ISSUES.md) |

## 수업·교사 도구

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `picture-book-library` | ✅ 운영 | - | 초등 그림책 수업 자료와 개인 서재를 연계하여 도서 추천, 카드 작성, 검색 색인 및 HTML 목록을 관리한다. | [SKILL](skills/picture-book-library/SKILL.md) · [이슈](skills/picture-book-library/ISSUES.md) |
| `teacher-3dprint` | 🔧 개발 | - | 수업 아이디어·물체·지형을 실제 출력 가능한 STL로 설계한다. 실측 지형, 기능 부품, 식품 몰드 참고 절차와 독도 지형 예제가 있다. | [SKILL](skills/teacher-3dprint/SKILL.md) · [이슈](skills/teacher-3dprint/ISSUES.md) |
| `teacherlesson-aiep-courseware` | ✅ 운영 | - | 상위 공통 수업꾸러미의 AIEP 어댑터. 경북 AIEP의 성취기준, LCMS·파일/링크 배치, 공개 범위와 학습 순서를 반영해 꾸러미를 만들고 학습자 미리보기를 점검한다. | [SKILL](skills/teacherlesson-aiep-courseware/SKILL.md) · [이슈](skills/teacherlesson-aiep-courseware/ISSUES.md) · [README](skills/teacherlesson-aiep-courseware/README.md) |
| `teacherlesson-assistant` | 🔧 개발 | v0.1.0 | 진도표·지도서·출판사 사이트·녹음·메모를 묶은 교시별 수업 진행 화면과, 수업 뒤 메모를 정리해 다음 수업에 반영하는 Claude 작업 절차. | [SKILL](skills/teacherlesson-assistant/SKILL.md) · [이슈](skills/teacherlesson-assistant/ISSUES.md) 🔵20 · [README](skills/teacherlesson-assistant/README.md) |
| `teacherlesson-classtool-courseware` | ✅ 운영 | - | 클래스툴의 내 수업 보관함에서 수업자료를 설계하고, 링크·콘텐츠·OX·객관식·주관식·화이트보드 활동을 구성한다. 교사 자료실 공개와 학생 클래스 배포, 실시간 응답 흐름을 구분한다. | [SKILL](skills/teacherlesson-classtool-courseware/SKILL.md) · [이슈](skills/teacherlesson-classtool-courseware/ISSUES.md) |
| `teacherlesson-courseware-builder` | ✅ 운영 | - | 플랫폼 공통 수업 패키지와 자료를 설계하고, AIEP·클래스툴 등 사이트별 어댑터로 콘텐츠 배치, 학생 응답 방식, 공개/배포 범위를 구분해 제작한다. 새 플랫폼은 어댑터와 카탈로그 항목으로 확장한다. | [SKILL](skills/teacherlesson-courseware-builder/SKILL.md) · [이슈](skills/teacherlesson-courseware-builder/ISSUES.md) |
| `teacherlesson-from-neis` | ✅ 운영 | Chrome 확장 v1.7.2 | NEIS 수업내용과 학생 출결·신청 현황을 조회해 뷰어에 표시하고, 신청 내용을 확인해 선택한 결석신고서만 결석 구분과 Chrome에 저장한 유형별 결재선을 적용해 접수·승인요청한다. 최종 결재는 하지 않는다. | [SKILL](skills/teacherlesson-from-neis/SKILL.md) · [이슈](skills/teacherlesson-from-neis/ISSUES.md) 🔵2 · [README](skills/teacherlesson-from-neis/README.md) |
| `teacherlesson-guide` | ✅ 운영 | v1.0.0 | 출판사 지도서 PDF 받기 → 차시별 분할 → 진도표 행 생성·업로드를 한 스킬로 묶은 지도서 처리 흐름. (옛 guide-splitter·guide-mapper·수업 비서의 지도서 받기를 합침) | [SKILL](skills/teacherlesson-guide/SKILL.md) · [이슈](skills/teacherlesson-guide/ISSUES.md) 🔵2 |
| `teacherlesson-schedule` | ✅ 운영 | v1.0.0 | Google Sheets 기반 교사 수업 진도·수업 배치 관리와 자동 시간표 계획 기능을 다룬다. | [SKILL](skills/teacherlesson-schedule/SKILL.md) · [이슈](skills/teacherlesson-schedule/ISSUES.md) · [README](skills/teacherlesson-schedule/README.md) |
| `teacherlesson-update-app` | ✅ 운영 | v0.0.1 | 초등 교사를 위한 Update 앱의 프런트엔드 코드와 가이드라인이다. | [SKILL](skills/teacherlesson-update-app/SKILL.md) · [이슈](skills/teacherlesson-update-app/ISSUES.md) · [README](skills/teacherlesson-update-app/README.md) |
| `teacherlesson-workspace` | ✅ 운영 | v0.1.0 | Supabase 등 여러 교사 도구의 데이터를 모아 보여주는 교사용 대시보드/워크스페이스 앱이다. | [SKILL](skills/teacherlesson-workspace/SKILL.md) · [이슈](skills/teacherlesson-workspace/ISSUES.md) · [README](skills/teacherlesson-workspace/README.md) |

## 홈페이지

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `homepage-school-board` | ✅ 운영 | - | 학교 게시판 크롤링 → GitHub Actions → school.html 공지 탭 연동 | [SKILL](skills/homepage-school-board/SKILL.md) · [이슈](skills/homepage-school-board/ISSUES.md) |

## 개인·생활

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `personal-analyze-trade` | 📦 보관 | - | Google Sheets 투자 기록을 읽어 포트폴리오, 수익, 비중, 섹터, 매매 신호와 전략을 분석한다. 신규 매매 입력은 `personal-record-trade` 담당이다. | [SKILL](skills/personal-analyze-trade/SKILL.md) · [이슈](skills/personal-analyze-trade/ISSUES.md) |
| `personal-attach-files` | ✅ 운영 | - | 프로젝트의 핵심 코드/기획 파일을 모아 AI에 첨부하기 쉬운 임시 폴더로 준비한다. | [SKILL](skills/personal-attach-files/SKILL.md) · [이슈](skills/personal-attach-files/ISSUES.md) |
| `personal-carrot` | 🔧 개발 | - | Appium으로 Android 당근마켓 앱의 매물을 검색·수집해 Google Sheets에 기록한다. | [SKILL](skills/personal-carrot/SKILL.md) · [이슈](skills/personal-carrot/ISSUES.md) |
| `personal-chesley-morning-brief-main` | ✅ 운영 | - | 유튜브 '체슬리모닝브리프' 새 영상을 감지해 전체 스크립트를 Gemini Gems 웹 세션으로 구조화 요약하고 디스코드로 보낸다. | [SKILL](skills/personal-chesley-morning-brief-main/SKILL.md) · [이슈](skills/personal-chesley-morning-brief-main/ISSUES.md) · [README](skills/personal-chesley-morning-brief-main/README.md) |
| `personal-daily-intake` | 🔧 개발 | v0.1.0 | 제미나이 스킬이 받아쓰고 나눈 하루 기록 md를 일정DB 시트·Notion 독서 DB·옵시디언(daily/, 00_Inbox, 10_NOTE/수업)에 표로 확인받고 한 번에 나눠 넣는다. 같은 것을 두 번 넣지 않는다. | [SKILL](skills/personal-daily-intake/SKILL.md) · [이슈](skills/personal-daily-intake/ISSUES.md) 🔵2 |
| `personal-free-parents-app` | 🔧 개발 | - | 공동 육아 놀이터 앱 ‘같이 놀자’의 개발·디자인 통합 안내와 구현 메모를 담는다. | [SKILL](skills/personal-free-parents-app/SKILL.md) · [이슈](skills/personal-free-parents-app/ISSUES.md) 🔵2 · [README](skills/personal-free-parents-app/README.md) |
| `personal-library-search` | ✅ 운영 | - | Notion 도서 목록에서 ISBN/서점 정보를 찾고 경주시립도서관 소장 여부를 확인하며, 미소장 도서 희망도서 신청 흐름을 지원한다. | [SKILL](skills/personal-library-search/SKILL.md) · [이슈](skills/personal-library-search/ISSUES.md) · [README](skills/personal-library-search/README.md) |
| `personal-mp3-baby` | ✅ 운영 | - | 아기 잠자리동화 MP3를 한국어 타임코드 SRT로 전사해 이야기 구간을 찾아 넘길 수 있게 한다. | [SKILL](skills/personal-mp3-baby/SKILL.md) · [이슈](skills/personal-mp3-baby/ISSUES.md) |
| `personal-obsidansystem-main` | ✅ 운영 | v0.3.0 | Obsidian 볼트 메모를 운용지침에 맞게 분류·정리한다. 속성 일괄 수정 GUI, 볼트 묶음(md) 생성 → NotebookLM/Gemini 분석 → 추천표 검증·반영 파이프라인, NotebookLM 소스 추출 연계, Google Keep 메모 가져오기를 담았다. | [SKILL](skills/personal-obsidansystem-main/SKILL.md) · [이슈](skills/personal-obsidansystem-main/ISSUES.md) |
| `personal-reading-book` | ✅ 운영 | - | 긴 문서를 로컬 우선으로 읽고 설명하는 Reading Tutor 프로젝트의 규칙과 정리 스크립트를 담는다. | [SKILL](skills/personal-reading-book/SKILL.md) · [이슈](skills/personal-reading-book/ISSUES.md) |
| `personal-record-trade` | 📦 보관 | - | 이전 Google Sheets 매매일지 입력 절차와 2_add_trade.py 사용법을 보관한다. 현재 신규 기록에는 사용하지 않는다. | [SKILL](skills/personal-record-trade/SKILL.md) · [이슈](skills/personal-record-trade/ISSUES.md) · [README](skills/personal-record-trade/README.md) |
| `personal-vba-book` | 📦 보관 | - | 과거 Excel VBA 도서 크롤러 원본과 Python 마크다운 서재 마이그레이션 아카이브를 보관한다 (실운영은 picture-book-library). | [SKILL](skills/personal-vba-book/SKILL.md) · [이슈](skills/personal-vba-book/ISSUES.md) |
| `personal-video-note` | ✅ 운영 | v0.2.6 | YouTube 자막을 먼저 조회·추출하고, 강의 영상에서 슬라이드 캡처·타임스탬프 전사·Obsidian용 노트를 로컬 생성한다. 같은 슬라이드의 누적 공개 화면은 대표 화면으로 통합하고, 이미지 링크와 `slides/` 구성을 유지한다. | [SKILL](skills/personal-video-note/SKILL.md) · [이슈](skills/personal-video-note/ISSUES.md) 🔵1 · [README](skills/personal-video-note/README.md) |
| `personal-video-url` | ✅ 운영 | - | `krcls.kr`의 기존 로그인 Chrome(CDP 9222)에서 플레이어 프레임에 노출된 미디어 URL을 확인해 CSV/Markdown으로 저장하고, 차시별 진도를 전후 비교한다. 영상은 다운로드하지 않는다. | [SKILL](skills/personal-video-url/SKILL.md) · [이슈](skills/personal-video-url/ISSUES.md) |
| `personal-youtube-gemini-kakao-automation` | ✅ 운영 | - | 체슬리 모닝 브리프 YouTube 영상의 Gemini 요약 파이프라인을 실행하고 중단 기간의 요약 백로그를 처리한다. | [SKILL](skills/personal-youtube-gemini-kakao-automation/SKILL.md) · [이슈](skills/personal-youtube-gemini-kakao-automation/ISSUES.md) |
| `personal-youtube-transcript-kakao-bot` | ✅ 운영 | - | 유튜브 재생목록의 새 영상 자막을 매일 자동으로 가져와 저장하고, 카카오톡 '나에게 보내기'(또는 디스코드 웹훅)로 알려주는 깃허브 액션 자동화를 만들고, 설정하고, 고쳐 쓰는 스킬. | [SKILL](skills/personal-youtube-transcript-kakao-bot/SKILL.md) · [이슈](skills/personal-youtube-transcript-kakao-bot/ISSUES.md) |

## 공통 유틸

| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |
|---|---|---|---|---|
| `ego-browser` | 🔧 개발 | - | Ego Lite의 `ego-browser` CLI로 브라우저를 조작하고, 사용자 탭과 관리형 TaskSpace 창의 차이를 확인하며 작업 기록·스크린샷을 과업별 폴더에 정리한다. | [SKILL](skills/ego-browser/SKILL.md) · [이슈](skills/ego-browser/ISSUES.md) · [README](skills/ego-browser/README.md) |
| `util-bat-launcher` | 🔧 개발 | v0.1.0 | 저장소의 모든 bat·cmd 를 분야·스킬별로 모아 보여 주고 더블클릭으로 실행하는 실행기. 찾기, 즐겨찾기, 최근 실행, 바탕화면 바로가기. | [SKILL](skills/util-bat-launcher/SKILL.md) · [이슈](skills/util-bat-launcher/ISSUES.md) 🔵1 |
| `util-chrome-profiles` | 🔧 개발 | v0.1.0 | Chrome·Edge 프로필을 그룹으로 묶어 클릭으로 열고, 열린 창을 미리보기로 보며 일괄 입력·변화 없음 감시·타이머 알림을 주는 Windows 앱. 로그인 상태는 그대로 유지된다. | [SKILL](skills/util-chrome-profiles/SKILL.md) · [이슈](skills/util-chrome-profiles/ISSUES.md) 🔵3 |
| `util-discord-memo` | ✅ 운영 | - | Discord 메모 채널의 내용을 요약해 공지/리포트로 정리하는 대화형 워크플로를 설명한다. | [SKILL](skills/util-discord-memo/SKILL.md) · [이슈](skills/util-discord-memo/ISSUES.md) |
| `util-edusearch-main` | ✅ 운영 | - | 인디스쿨·수업나누리 등에서 수집한 교육 자료를 내 PC의 로컬 검색 DB로 모아 한 번에 검색하는 개인용 스크래퍼+검색 시스템. | [SKILL](skills/util-edusearch-main/SKILL.md) · [이슈](skills/util-edusearch-main/ISSUES.md) · [README](skills/util-edusearch-main/README.md) |
| `util-map-time` | ✅ 운영 | - | Kakao 지도 기반 로컬 웹 앱. Excel 장소의 이동 거리·시간, 다대다 경로, 중간지점 및 경유지 비교를 제공한다. | [SKILL](skills/util-map-time/SKILL.md) · [이슈](skills/util-map-time/ISSUES.md) · [README](skills/util-map-time/README.md) |
| `util-notebooklm` | 🔧 개발 | v0.1.0 | 긴 PDF 를 Claude 가 통째로 읽지 않도록, Gemini CLI·NotebookLM 이 관련 쪽을 찾고 그 쪽만 잘라 프런티어 모델에 넘기는 찾기·잘라내기·소스 만들기 도구. | [SKILL](skills/util-notebooklm/SKILL.md) · [이슈](skills/util-notebooklm/ISSUES.md) 🔵1 |
| `util-pdf-translator` | ✅ 운영 | 스크립트 패키지 v1.0.0 | 영문 PDF를 챕터별로 나누고 Gemini Gems로 번역한 뒤 Discord로 보낸다. | [SKILL](skills/util-pdf-translator/SKILL.md) · [이슈](skills/util-pdf-translator/ISSUES.md) |
| `util-school-print` | ✅ 운영 | - | Windows 한글(HWP) 자동화로 학년/반별 안내장을 배치 인쇄하고 반별 간지를 넣는다. | [SKILL](skills/util-school-print/SKILL.md) · [이슈](skills/util-school-print/ISSUES.md) |
| `util-storagemap` | ✅ 운영 | 패키지 v2.1.0; README는 V3 표기 | 물건 위치와 공간별 2D 배치를 관리하는 Supabase 기반 웹앱이다. README의 V3와 `package.json` 버전 표기가 서로 다르다. | [SKILL](skills/util-storagemap/SKILL.md) · [이슈](skills/util-storagemap/ISSUES.md) · [README](skills/util-storagemap/README.md) |
| `util-web-scraper` | 🔧 개발 | - | URL의 페이지를 수집해 EduSearch 로컬 검색 인덱스를 갱신한다. | [SKILL](skills/util-web-scraper/SKILL.md) · [이슈](skills/util-web-scraper/ISSUES.md) |
| `util-webtoguide` | ✅ 운영 | - | 웹페이지, 특히 네이버 블로그의 글·이미지를 추출해 출처 링크가 포함된 Markdown 가이드로 변환한다. | [SKILL](skills/util-webtoguide/SKILL.md) · [이슈](skills/util-webtoguide/ISSUES.md) |
| `workflow-hub-main` | ✅ 운영 | - | Antigravity(기획)→Cursor(구현)→Codex(점검) 삼각 협업과 GitHub 중심 AI 워크플로우 규칙·프로젝트 템플릿 모음. | [SKILL](skills/workflow-hub-main/SKILL.md) · [이슈](skills/workflow-hub-main/ISSUES.md) · [README](skills/workflow-hub-main/README.md) |

## 범례

| 상태 | 의미 |
|---|---|
| ✅ 운영 | 실제로 사용 중 |
| 🔧 개발 | 만드는 중이거나 미완성 |
| 📦 보관 | 더 이상 쓰지 않지만 참고용으로 둠 |
| ❔ 확인 필요 | 상태를 아직 정하지 않음 |

🔵 숫자 = `ISSUES.md`의 '진행 중' 항목 수
