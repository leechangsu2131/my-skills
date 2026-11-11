---
name: teacherlesson-courseware-builder
description: Design reusable lesson packages and learning materials, then adapt them to a supported learning platform such as AIEP Courseware or ClassTool. Use when a teacher wants a lesson planned, its files organized, or the package prepared for a learning site; check each platform's actual response and publishing capabilities separately.
---

# 학습 플랫폼 수업꾸러미 제작

수업 설계와 학습자료 제작은 공통 표준으로 하고, 사이트 입력 방식은 플랫폼별 어댑터에 맡긴다. 한 플랫폼의 메뉴·학생 응답 기능·공개 설정을 다른 사이트에 그대로 적용하지 않는다.

## 플랫폼 선택

- 사용자가 사이트나 URL을 지정하면 그 플랫폼을 선택한다.
- AIEP는 [AIEP 어댑터](platforms/aiep.md)와 [AIEP 전용 스킬](../teacherlesson-aiep-courseware/SKILL.md)을 읽는다.
- 클래스툴은 [클래스툴 어댑터](platforms/classtool.md)와 [클래스툴 전용 스킬](../teacherlesson-classtool-courseware/SKILL.md)을 읽는다.
- 새 플랫폼은 로그인된 실제 화면이나 공식 문서를 확인한 뒤 `platforms/<platform>.md`로 추가한다. 실제 편집 절차가 충분히 다르면 전용 하위 스킬도 추가하고 `skills/SKILLS_CATALOG.md`를 갱신한다.
- 플랫폼의 작성 화면에 로그인할 수 없으면 확인된 공개 문서만으로 초안을 만들고, 실제 메뉴·업로드·게시 동작은 확인되지 않았다고 표시한다. 계정 비밀번호를 기록하지 않는다.

## 공통 제작 절차

1. 학년, 교과/주제, 차시와 시간, 학습자, 사용할 환경, 원하는 산출물을 정리한다. 비어 있는 정보는 합리적인 가정과 확인 항목으로 나눈다.
2. 성취기준이 없는 창체·프로젝트 수업은 임의의 기준을 공식 기준처럼 쓰지 않는다. 사용자가 원하면 가까운 관련 기준을 `관련 기준(참고)`로 표시하고, 수업 목표와의 연결을 짧게 설명한다.
3. 차시별 목표·활동·자료·평가 증거가 이어지도록 설계한다. 활동별 교사 안내와 학생용 지시문은 구분한다.
4. 플랫폼과 무관한 꾸러미 표준은 [공통 패키지 양식](references/course-package-template.md)을 사용한다. 사이트별 입력표는 선택한 어댑터의 필드만 추가한다.
5. 학생 응답 요구를 다음 중 하나로 표시한다: `자료 열람`, `실시간 응답`, `지속 보관되는 제출`. 해당 사이트에서 확인되지 않은 기능을 가능하다고 가정하지 않는다. 시험·주관식 답변의 수집, 저장 기간, 다운로드는 현재 화면이나 공식 문서에서 확인한다.
6. PPTX, PDF, 이미지, 영상 및 링크는 선택한 플랫폼이 현재 지원하는지 확인하고, 저작권·출처·학생 개인정보 포함 여부를 점검한다. 지원이 불명확한 형식은 PDF 변환이나 링크 제공을 대안으로 제안하되, 변환이 필요하다고 단정하지 않는다.
7. 결과물을 `output/<날짜>-<짧은-수업명>/` 아래에 모은다. 기본 구성은 `course-package.md`, `자료/`, `출처/`, `미리보기/`이며 산출물 수에 맞춰 간소화한다.
8. 실제 사이트 입력을 요청받으면 해당 플랫폼 스킬의 브라우저 절차를 적용하고 저장 전 미리보기한다. 임시저장, 공개 범위, 학생에게 보이는 화면, 최종 등록을 구분하며 게시 의도를 확인한다.
9. 매뉴얼·화면에서 막히거나 예상과 다른 동작이 발생하면 재현 상태와 해결 방법을 플랫폼별 `records/` Markdown에 남긴다. 학생 이름, 학급 명단, 로그인 정보를 기록하지 않는다.

## 품질 기준

- 수업 목표, 활동, 학생 산출물과 평가 증거가 맞물린다.
- 플랫폼이 실제 제공하는 흐름에 맞춰 활동을 바꾸되, 플랫폼 기능을 과장하지 않는다.
- 학생이 사이트에서 할 수 있는 일과 오프라인/다른 도구가 필요한 일을 명확하게 구분한다.
- 전체 공개를 기본값으로 취급하지 않는다. 플랫폼에 따라 공개 자료실 공유와 학생 클래스 접속은 다른 범위일 수 있다.
- 자료의 출처, 이용 조건, 교사용/학생용 구분과 사이트 배치 순서를 기록한다.
