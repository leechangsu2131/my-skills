# Teacher Workspace (Core Hub)

교사를 위한 궁극의 스케줄러 및 통합 대시보드 애플리케이션입니다.
`my-skills` 거대 모노레포(Monorepo)의 중심 화면(뷰어) 역할을 수행하며, 시스템 전반의 파이썬 마이크로 스킬들로부터 조달된 데이터를 시각화합니다.

## 시스템 소속 및 참조 구조 (Lineage)

앱 아키텍처의 의존성 및 백엔드 출처는 다음과 같습니다.

### 1. Database (백엔드 데이터)
* **Supabase**: `lessons` 테이블 및 `teacher_guides` 버킷 스토리지에 데이터를 의존합니다.

### 2. 의존 스킬 (my-skills/skills)
이 애플리케이션 화면에 출력되는 PDF 파일 구조 및 일정 데이터는 아래 내부 스킬들로부터 자동 파싱되어 주입됩니다.
* `teacherlesson-guide-mapper`
* `teacherlesson-guide-splitter`
* `teacherlesson-schedule`

### 3. 참고 및 벤치마크 (Reference)
이 통합 워크스페이스의 기반 아이디어 및 UI 레이아웃, 기획 로드맵들은 다음의 과거 레퍼런스 앱들로부터 착안, 발전되었습니다. (`reference` 디렉토리 참조)
* `Class-Planner-Pro` (과목별 진도 배치)
* `Lesson-Navigator` (네비게이션 툴)
* `teacher-lesson-helper`

## 실행 방법
```bash
npm install
npm run dev
```
