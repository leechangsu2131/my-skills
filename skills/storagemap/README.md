# STORAGEMAP 2D - 물건 위치 관리 시스템

스펙 문서 `storagemap_v2.1_2d.md` 기반의 물건 위치 관리 시스템입니다.

## 🎯 핵심 기능

- **5초 안에 물건 찾기**: 이름으로 검색 → 정확한 위치 경로 반환
- **2D 평면도 시각화**: 가구를 직사각형 마커로 표시하고 클릭으로 물건 목록 확인
- **위치 등록 및 수정**: 30초 이내에 물건 위치 등록
- **Google Sheets 연동**: .env 설정으로 구글 시트와 데이터 연동

## 🏗️ 시스템 구조

```
storagemap/
├── server.js              # Express 백엔드 서버
├── package.json            # 의존성 관리
├── .env.example           # 환경 설정 예시
├── .env                   # 실제 환경 설정 (Git 제외)
├── public/                # 프론트엔드
│   ├── index.html         # 메인 페이지
│   ├── styles.css         # 스타일시트
│   └── app.js             # 프론트엔드 로직
└── README.md              # 이 파일
```

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 환경 설정
`.env.example` 파일을 복사하여 `.env` 파일을 만들고 Google Sheets API 정보를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```
# Google Sheets API 설정
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key_here
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here

# 서버 설정
PORT=3000
NODE_ENV=development

# Google Sheets 시트 이름
SHEET_ITEMS=Items
SHEET_SPACES=Spaces
SHEET_FURNITURE=Furniture
SHEET_ZONES=Zones
SHEET_HISTORY=History
```

### 3. 서버 시작
```bash
# 개발 모드
npm run dev

# 또는 일반 모드
npm start
```

### 4. 접속
브라우저에서 `http://localhost:3000` 접속

## 📊 Google Sheets 설정

### 스프레드시트 구조 (스펙 문서 8.1 참조)

1. **Items 시트**: 물건 마스터 데이터
   - item_id, name, furniture_id, zone_id, category, tags, memo, photo_url, quantity, context, created_at, updated_at

2. **Spaces 시트**: 공간 목록 (L1)
   - space_id, name, description

3. **Furniture 시트**: 가구 목록 (L3)
   - furniture_id, space_id, name, type, photo_url, pos_x, pos_y, width, height, zones_json, notes

4. **Zones 시트**: 구획 목록 (L4)
   - zone_id, furniture_id, name, position_desc, photo_url

5. **History 시트**: 이동 이력
   - history_id, item_id, from_furniture, from_zone, to_furniture, to_zone, moved_at, note

## 🎨 주요 기능

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

## 🐛 트러블슈팅

### Google Sheets 연동 실패
- API 키가 올바른지 확인
- 스프레드시트가 공개되어 있는지 확인
- 시트 이름이 .env 설정과 일치하는지 확인

### 데이터가 표시되지 않음
- 샘플 데이터가 자동으로 로드됩니다
- 브라우저 개발자 도구에서 콘솔 에러 확인

## 📝 라이선스

MIT License
