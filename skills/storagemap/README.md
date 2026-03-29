# STORAGEMAP 2D - 물건 위치 관리 시스템

스펙 문서 `storagemap_v2.1_2d.md` 기반의 물건 위치 관리 시스템입니다.

## 🎯 핵심 기능

- **5초 안에 물건 찾기**: 이름으로 검색 → 정확한 위치 경로 반환
- **2D 평면도 시각화**: 가구를 직사각형 마커로 표시하고 클릭으로 물건 목록 확인
- **위치 등록 및 수정**: 30초 이내에 물건 위치 등록
- **Google Sheets 연동**: 자동 인증 및 데이터 동기화
- **자동 Google 인증**: 서버 시작 시 refresh_token으로 자동 로그인
- **헤더 자동 생성**: Google Sheets에 데이터 추가 시 헤더 자동 생성
- **통합 테스트 페이지**: `http://localhost:3001/test.html`에서 모든 기능 테스트

## 🏗️ 시스템 구조

```
storagemap/
├── server.js              # Express 백엔드 서버
├── package.json           # 의존성 관리
├── .env.example          # 환경 설정 예시
├── .env                  # 실제 환경 설정 (Git 제외)
├── netlify.toml          # Netlify 배포 설정
├── netlify/
│   └── functions/
│       └── api.js        # 서버리스 함수 어댑터
├── public/               # 프론트엔드
│   ├── index.html        # 메인 페이지
│   ├── test.html         # 통합 테스트 페이지
│   ├── styles.css        # 스타일시트
│   └── app.js            # 프론트엔드 로직
├── README.md             # 이 파일
└── UPGRADE.md            # 업그레이드 로드맵
```

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 환경 설정
`.env.example` 파일을 복사하여 `.env` 파일을 만들고 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일 예시:
```
# Google OAuth 2.0 설정
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
REDIRECT_URI=http://localhost:3001/auth/callback

# 자동 인증 (한 번 로그인 후 받은 refresh_token 저장)
GOOGLE_REFRESH_TOKEN=your_refresh_token_here

# Google Sheets 설정
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here

# 서버 설정
PORT=3001
SESSION_SECRET=your_session_secret_here

# 시트 이름
SHEET_ITEMS=Items
SHEET_SPACES=Spaces
SHEET_FURNITURE=Furniture
SHEET_ZONES=Zones
SHEET_HISTORY=History
```

### 3. 자동 인증 설정 (한 번만)

1. **최초 로그인**: `http://localhost:3001/auth/google`에서 Google 로그인
2. **토큰 받기**: `http://localhost:3001/api/auth/token`에서 refresh_token 복사
3. **환경변수 저장**: `.env` 파일의 `GOOGLE_REFRESH_TOKEN`에 붙여넣기
4. **서버 재시작**: 이후 자동으로 인증됨

### 4. 서버 시작
```bash
# 개발 모드
npm run dev

# 또는 일반 모드
npm start
```

### 5. 접속
- 메인 앱: `http://localhost:3001`
- 테스트 페이지: `http://localhost:3001/test.html`

## 📊 Google Sheets 설정

### 스프레드시트 구조

**⚠️ 중요: 각 시트의 첫 번째 행(Row 1)은 반드시 다음 헤더를 사용해야 합니다:**

#### 1. Spaces 시트 (공간 목록 - L1)
**헤더 행:**
```
space_id | name | description
```

**예시 데이터:**
| space_id | name | description |
|----------|------|-------------|
| s1 | 3학년 2반 | 교실 공간 |
| s2 | 우리 집 | 거실/서재 공간 |

#### 2. Furniture 시트 (가구 목록 - L3)
**헤더 행:**
```
furniture_id | space_id | name | type | pos_x | pos_y | width | height
```

**예시 데이터:**
| furniture_id | space_id | name | type | pos_x | pos_y | width | height |
|--------------|----------|------|------|-------|-------|-------|--------|
| f1 | s1 | 앞 교구장 | 교구장 | 50 | 50 | 120 | 80 |
| f2 | s1 | 교탁 | 교탁 | 300 | 40 | 160 | 60 |

#### 3. Items 시트 (물건 마스터 데이터)
**헤더 행:**
```
item_id | name | furniture_id | category | quantity | memo
```

**예시 데이터:**
| item_id | name | furniture_id | category | quantity | memo |
|---------|------|--------------|----------|----------|------|
| i1 | 리코더 (학생용) | f1 | 교구 | 25 | 학생용 리코더 |
| i2 | 수학 교구 세트 | f1 | 교구 | 5 | 기하 도형 포함 |

#### 4. Zones 시트 (구획 목록 - L4)
**헤더 행:**
```
zone_id | furniture_id | name | position_desc
```

#### 5. History 시트 (이동 이력)
**헤더 행:**
```
history_id | item_id | from_furniture | to_furniture | moved_at | note
```

**참고**: 헤더가 없는 경우, 데이터 추가 시 자동으로 헤더가 생성됩니다.

## 🛠️ API 엔드포인트

### 기본 API
- `GET /api/health` - 서버 상태 확인
- `GET /api/data` - 전체 데이터 조회
- `GET /api/spaces` - 공간 목록 조회
- `GET /api/spaces/:spaceId` - 특정 공간 데이터
- `GET /api/spaces/:spaceId/furniture` - 공간별 가구 조회
- `GET /api/search?q=query` - 물건 검색
- `GET /api/floorplan/:spaceId` - 2D 평면도 데이터

### 인증 필요 API (POST/PUT)
- `POST /api/spaces` - 공간 추가
- `POST /api/furniture` - 가구 추가
- `POST /api/items` - 물건 추가
- `PUT /api/furniture/:furnitureId/position` - 가구 위치 업데이트
- `GET /api/data/reload` - Google Sheets 데이터 재로드

### 인증 API
- `GET /auth/google` - Google OAuth 로그인
- `GET /auth/callback` - OAuth 콜백
- `GET /api/auth/status` - 인증 상태 확인
- `GET /api/auth/token` - refresh_token 조회
- `GET /api/debug/sheets` - Google Sheets 진단

### 검색 시스템 (스펙 문서 5장)
- **우선순위 1**: 이름 완전 일치
- **우선순위 2**: 이름 부분 일치  
- **우선순위 3**: 태그 일치
- **우선순위 4**: 메모 포함

### 2D 평면도 (스펙 문서 7장)
- 가구를 직사각형 마커로 시각화
- 클릭으로 물건 목록 표시
- 확대/축소 기능
- 검색 결과 하이라이트

### 데이터 모델 (스펙 문서 3장)
- 3단계 공간 계층: 공간(L1) → 가구(L3) → 구획(L4)
- 필수 필드: item_id, name, furniture_id, created_at, updated_at
- 선택 필드: zone_id, category, tags, memo, photo_url, quantity, context

## 🛠️ 개발

### API 엔드포인트

- `GET /api/health` - 서버 상태 확인
- `GET /api/data/load` - Google Sheets에서 데이터 로드
- `GET /api/data` - 전체 데이터 조회
- `GET /api/spaces/:spaceId` - 특정 공간 데이터
- `GET /api/search?q=query` - 검색
- `GET /api/floorplan/:spaceId` - 2D 평면도 데이터

### 개발 모드
```bash
npm run dev  # nodemon으로 자동 재시작
```

## 📋 스펙 문서 준수

이 시스템은 `storagemap_v2.1_2d.md` 스펙 문서의 다음 항목을 준수합니다:

- ✅ 설계 원칙 (1장)
- ✅ 공간 계층 구조 (2장)  
- ✅ 데이터 모델 (3장)
- ✅ 시스템 규칙 (4장)
- ✅ 검색 규칙 (5장)
- ✅ 2D 평면도 운용 가이드 (7장)
- ✅ Google Sheets 운용 가이드 (8장)

## 🔄 버전 히스토리

### v2.1.0 (현재)
- Google OAuth 2.0 자동 인증
- 서버 시작 시 refresh_token으로 자동 로그인
- 헤더 자동 생성 기능
- 통합 테스트 페이지 추가
- Netlify 배포 설정

## 🐛 트러블슈팅

### Google Sheets 연동 실패
- **인증 오류**: `GOOGLE_REFRESH_TOKEN`이 유효한지 확인
- **시트 없음**: 스프레드시트 ID와 시트 이름 확인
- **헤더 오류**: 수동으로 헤더 행 추가 또는 자동 생성 대기

### 자동 인증 실패
- `.env`의 `GOOGLE_REFRESH_TOKEN` 확인
- 토큰이 만료되었다면 재로그인 후 새 토큰 저장
- Google Cloud Console에서 OAuth 동의 화면 설정 확인

### 데이터 로드 문제
- 서버 콘솔 로그 확인 (자세한 디버깅 정보 출력)
- `http://localhost:3001/api/debug/sheets`에서 진단
- Google Sheets 공유 설정 확인 (편집자 권한 필요)

## 📝 라이선스

MIT License
