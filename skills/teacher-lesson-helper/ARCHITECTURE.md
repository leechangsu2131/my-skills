# Teacher Lesson Helper - 아키텍처 설계

## 1. 데이터 모델

### 1.1 주요 엔티티

#### Textbook (지도서)
- `id`: 고유 ID
- `userId`: 소유자 (교사)
- `title`: 지도서 제목 (예: "3학년 수학 지도서")
- `subject`: 교과목 (수학, 국어, 영어 등)
- `grade`: 학년 (1-6)
- `semester`: 학기 (1 또는 2)
- `publisher`: 출판사
- `fileKey`: S3에 저장된 PDF 파일 키
- `fileUrl`: S3 파일 URL
- `totalPages`: 전체 페이지 수
- `createdAt`: 생성 시간
- `updatedAt`: 수정 시간

#### LessonExtraction (차시 추출)
- `id`: 고유 ID
- `textbookId`: 지도서 ID (외래키)
- `lessonNumber`: 차시 번호 (예: 1, 2, 3...)
- `title`: 차시 제목
- `startPage`: 시작 페이지
- `endPage`: 종료 페이지
- `content`: 추출된 텍스트 내용
- `extractedAt`: 추출 시간

#### RecentAccess (최근 접근 이력)
- `id`: 고유 ID
- `userId`: 사용자 ID
- `textbookId`: 지도서 ID
- `lessonNumber`: 차시 번호
- `accessedAt`: 접근 시간

## 2. 기술 스택

### 백엔드
- **PDF 처리**: `pdfjs-dist` (텍스트 추출)
- **파일 저장**: S3 (AWS SDK)
- **데이터베이스**: MySQL (Drizzle ORM)
- **API 프레임워크**: tRPC + Express

### 프론트엔드
- **UI 라이브러리**: React 19 + Tailwind CSS 4
- **상태 관리**: tRPC + React Query
- **컴포넌트**: shadcn/ui

## 3. 주요 기능 흐름

### 3.1 PDF 업로드 및 파싱
1. 사용자가 PDF 파일 선택
2. 백엔드에서 PDF를 S3에 업로드
3. PDF에서 전체 텍스트 추출
4. 차시 구조 자동 감지 (정규식으로 "차시", "단원" 등 패턴 찾기)
5. 데이터베이스에 저장

### 3.2 차시 추출
1. 사용자가 차시 번호 입력
2. 데이터베이스에서 해당 차시 정보 조회
3. 추출된 텍스트 반환

### 3.3 PDF 다운로드
1. 추출된 차시 내용을 PDF로 변환
2. 사용자에게 다운로드 제공

## 4. API 설계

### Textbook 관련
- `textbook.list`: 사용자의 모든 지도서 조회
- `textbook.create`: 새 지도서 업로드
- `textbook.getById`: 특정 지도서 조회
- `textbook.delete`: 지도서 삭제

### Lesson 관련
- `lesson.getByNumber`: 차시 번호로 조회
- `lesson.listByTextbook`: 지도서의 모든 차시 목록
- `lesson.downloadPdf`: 차시를 PDF로 다운로드

### RecentAccess 관련
- `recentAccess.list`: 최근 접근 이력 조회
- `recentAccess.add`: 접근 기록 추가

## 5. 차시 자동 감지 알고리즘

### 패턴 인식
- "차시", "단원", "lesson", "unit" 등의 키워드 찾기
- 페이지 번호와 함께 차시 정보 추출
- 정규식: `/(?:차시|단원|lesson|unit)\s*(\d+)/gi`

### 폴백 전략
- 자동 감지 실패 시 사용자가 수동으로 차시 정보 입력 가능
- 페이지 범위 지정 가능

## 6. 보안 고려사항

- 사용자는 자신의 지도서만 접근 가능 (userId 검증)
- PDF 파일은 S3에 저장 (로컬 저장 금지)
- 파일 크기 제한 (예: 100MB)
- 파일 타입 검증 (PDF만 허용)
