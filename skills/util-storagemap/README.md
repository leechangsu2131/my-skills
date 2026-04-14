# STORAGEMAP V3 - 물건 위치 관리 시스템

스펙 문서 `storagemap_v2.1_2d.md`를 기반으로 구축된, Google Sheets 연동 2D 평면도 기반 물건 위치 관리 시스템입니다.

최근 V3 메이저 업데이트를 통해 기존 Vanilla JS 프론트엔드를 **React 19 + TypeScript + Vite + Tailwind CSS 4** 기반 최신 스택으로 전면 개편했습니다. 
(`Storage-Map-1` 프로젝트의 직관적인 검색 UI와 `storagemap-v2-2d`의 정교한 데이터 관리 대시보드 및 평면도 기능을 완벽히 통합했습니다.)

## 🎯 핵심 기능

- **5초 안에 물건 찾기 (Hybrid)**: 이름/카테고리/메모 기반의 초고속 검색 및 정확한 공간 경로 반환 시각화
- **2D 평면도 엔진 (Grid-Snap)**: 
  - 가구를 드래그 & 드롭으로 10px 단위 그리드 스냅 배치 (Storage-Map-1 스타일)
  - 가구별 아이템 개수 배지 및 리사이즈 핸들 지원 (v2-2d 스타일)
  - 검색 결과로 찾은 물건이 속한 가구를 강조(Highlight)
- **최적화된 인터페이스 (UX)**:
  - 데스크탑/모바일 반응형 레이아웃 및 Framer-Motion 애니메이션
  - 평면도 내 가구 클릭 시 우측에서 슬라이드되는 물건 관리 사이드바
  - 전체 시스템의 퀄리티(필수 필드 등록률, 고유 명칭 비율 등)를 점검하는 데이터 품질 대시보드
- **서버 자동 Google 인증**: 최초 1회 로그인 후 발급되는 `refresh_token`을 통해 앱 가동 시마다 수동 조작 없이 Google Sheets에 연동

---

## 🏗️ 아키텍처 및 시스템 구조

이 프로젝트는 단일 레포지토리(Monorepo) 스타일로 백엔드와 프론트엔드 환경이 분리되어 통신합니다.

```
storagemap/
├── server.js               # Node.js/Express 백엔드 서버 (구글 시트 연동 및 OAuth)
├── package.json            # 백엔드 의존성 및 공통 관리
├── .env                    # 비밀키 환경 설정 (Git 제외)
├── netlify.toml            # Netlify 프론트+백엔드 통합 배포 훅
│
├── client/                 # ✨ 신규 React 프론트엔드 최상위
│   ├── index.html          # Vite Entry Point 
│   ├── package.json        # 프론트엔드 전용 의존성
│   ├── src/                # React, TypeScript 코드 영역
│   │   ├── components/     # UI 모듈 (Canvas2D, Layout, FurnitureSidebar 등)
│   │   ├── hooks/          # React Query 및 백엔드 Fetching 훅
│   │   ├── pages/          # 라우팅 뷰 (Home, FloorPlan, Dashboard)
│   │   ├── types.ts        # 타입스크립트 스키마 정의
│   │   └── main.tsx        # React Root 모듈
│   └── vite.config.ts      # 번들링 및 /api 프록시 설정
│
└── public/                 # 빌드된 프론트엔드 정적 파일 서빙 폴더 (Vite Outdir)
```

---

## 🚀 설치 및 로컬 실행 가이드

### 1. 전역 시스템 설치
루트 폴더와 클라이언트 폴더 양쪽 모두에서 패키지를 설치해야 합니다.

```bash
# 백엔드 의존성 설치
npm install

# 프론트엔드 의존성 설치
cd client
npm install
cd ..
```

### 2. 환경 설정 (.env)
`.env.example` 등의 형식을 참고하여 루트 폴더에 `.env` 파일을 구성하세요. (OAuth 2.0 정보 및 스프레드시트 ID 필수 지정)

```env
# Google OAuth 2.0 설정
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
REDIRECT_URI=http://localhost:3001/auth/callback
GOOGLE_REFRESH_TOKEN=... # 초기 로그인 시 얻은 토큰 기록 (자동 연동용)

# Google Sheets 설정
GOOGLE_SHEETS_SPREADSHEET_ID=...

# 백엔드 포트
PORT=3001
SESSION_SECRET=...
```

### 3. 개발 서버 동시 실행

React 개발(HMR)과 백엔드를 켤 때는 포트를 분리해서 구동하면 편리합니다.
1. **백엔드 실행**: 루트에서 `npm start` 또는 `node server.js` (기본 3001포트)
2. **프론트 개발 모드**: `client/`로 이동 후 `npm run dev` (Vite 기본 5173포트 구동, 3001번 포트로 API 프록시 묶여 있음)

### 4. 프로덕션 빌드 (서버 1개로 통합 실행)
React 코드를 수정 완료하고 배포하거나, 하나의 서버로 구동하고 싶을 때 사용합니다.

```bash
# 클라이언트 디렉토리 내에서 정적 에셋 빌드 -> ../public 으로 컴파일
cd client
npm run build
cd ..

# 통합 서버 실행 (public 내의 정적 에셋과 API를 포트 하나로 모두 서빙)
npm start
```
*로컬 브라우저에서 `http://localhost:3001` 접속*

---

## 📊 Google Sheets 설정 및 구조

데이터베이스를 대신하는 구글 스프레드시트는 아래 시트들로 나뉘어 구성되어야 합니다.

- **Spaces (공간 목록 - L1)**: `space_id` | `name` | `description`
- **Furniture (가구 목록 - L3)**: `furniture_id` | `space_id` | `name` | `type` | `pos_x` | `pos_y` | `width` | `height`
- **Items (물건 마스터 - L5)**: `item_id` | `name` | `furniture_id` | `category` | `quantity` | `memo`
- **History (이동 이력)**: `history_id` | `item_id` | `from_furniture` | `to_furniture` | `moved_at` | `note`

*참고: 백엔드는 서버가 시작되거나 `새로고침` 버튼을 누를 때마다 이 시트 구조를 캐싱하여 RAM에 올립니다.*

## 🛠️ API 엔드포인트 주요 내역

| Method | Route | 용도 (권한 검사 포함됨) |
| --- | --- | --- |
| `GET` | `/api/auth/status` | 현재 OAuth/Refresh Token 인증 상태 검증 |
| `GET` | `/api/data` | 전체 스키마 패치 (Items, Furniture, Spaces 동시 호출) |
| `GET` | `/api/data/reload` | Google Sheets 캐시 데이터 수동 강제 갱신 |
| `GET` | `/api/search` | 물건 단어 색인 검색 API |
| `POST` / `PUT` / `DELETE` | `/api/items/:id` | 물건 객체 생성, 리사이즈 변경, 제거 처리 |
| `PUT` | `/api/furniture/:id/position` | 캔버스 상의 X, Y 좌표 및 W, H 스케일 백엔드 동기화 |
| `GET` | `/*` | **(React SPA Fallback)** 매칭되지 않는 딥 링크 접근 시 `index.html` 전달 |

## 💡 자주 겪는 문제 (Troubleshooting)

- **서버 콘솔에 "수동 로그인이 필요합니다" 에러 노출**: `.env`에 `GOOGLE_REFRESH_TOKEN`이 지정되지 않았거나 만료되었습니다. `http://localhost:3001/auth/google`에 브라우저로 접속해 인증하고 서버 로그에 뜨는 토큰을 설정 파일에 넣어주세요.
- **가구 이동을 저정했는데 새로고침시 원래대로 돌아옴**: 쓰기 권한이 없는 구글 시트이거나 `Furniture` 시트에 `pos_x`, `pos_y`, `width`, `height` 컬럼이 제대로 만들어져 있지 않아 저장이 반려되었을 가능성이 큽니다.
- **"물건을 찾을 수 없습니다" 화면 백지화**: React 앱 재빌드가 이루어지지 않았습니다. `client` 폴더 안에서 새로 `npm run build`를 호출하세요.

## 📝 라이선스

MIT License
