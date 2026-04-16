# StorageMap V3 (Supabase)

StorageMap은 물건 위치를 검색하고, 공간별 2D 배치도를 관리하는 웹앱입니다.  
이번 버전은 기존 Google Sheets/OAuth 백엔드 대신 **Supabase 테이블**을 기본 저장소로 사용합니다.

## 핵심 변경점

- Google Sheets 의존성 제거
- 서버가 Supabase 테이블을 직접 읽고 씀
- 브라우저 로그인 없이 `.env`의 Supabase 키로 동작
- Supabase 연결이 없으면 읽기 전용 샘플 데이터로 자동 폴백

## 준비

루트의 `.env` 또는 `.env.example`에 아래 값을 채웁니다.

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

SUPABASE_TABLE_SPACES=storage_map_spaces
SUPABASE_TABLE_FURNITURE=storage_map_furniture
SUPABASE_TABLE_ZONES=storage_map_zones
SUPABASE_TABLE_ITEMS=storage_map_items
SUPABASE_TABLE_HISTORY=storage_map_history

PORT=3002
NODE_ENV=development

# 로컬 PC의 HTTPS 인증서 신뢰 문제가 있을 때만 사용
# SUPABASE_TLS_INSECURE=true
```

`StorageMap_실행.bat`는 `PORT` 값을 읽어서 같은 포트로 브라우저를 열고, Windows 시스템 인증서를 신뢰하도록 `--use-system-ca` 옵션을 함께 적용합니다.
만약 사내망/백신 SSL 검사 때문에 `fetch failed` 또는 `SELF_SIGNED_CERT_IN_CHAIN`이 계속 나오면, 로컬 개발용으로만 `.env`에 `SUPABASE_TLS_INSECURE=true`를 추가해 우회할 수 있습니다.

## Supabase 스키마 생성

Supabase SQL Editor에서 [`supabase-schema.sql`](./supabase-schema.sql) 내용을 실행하세요.

기본 테이블:

- `storage_map_spaces`
- `storage_map_furniture`
- `storage_map_zones`
- `storage_map_items`
- `storage_map_history`

## 실행

```bash
npm install
cd client
npm install
npm run build
cd ..
npm start
```

개발 모드에서는 서버와 클라이언트를 따로 띄웁니다.

```bash
# server
npm start

# client
cd client
npm run dev
```

## API 메모

기존 프런트와의 호환을 위해 주요 엔드포인트는 유지했습니다.

- `GET /api/data`
- `GET /api/data/reload`
- `GET /api/spaces`
- `GET /api/spaces/:spaceId/furniture`
- `GET /api/search`
- `POST /api/items`
- `POST /api/furniture`
- `POST /api/spaces`
- `PUT /api/items/:itemId`
- `PUT /api/furniture/:furnitureId`
- `PUT /api/furniture/:furnitureId/position`
- `PUT /api/spaces/:spaceId`
- `DELETE /api/items/:itemId`
- `DELETE /api/furniture/:furnitureId`
- `DELETE /api/spaces/:spaceId`

## 동작 방식

- Supabase가 정상 설정되면 읽기/쓰기 모두 활성화됩니다.
- 설정이 없거나 초기 로드가 실패하면 서버는 샘플 데이터를 로드합니다.
- 샘플 모드에서는 조회는 가능하지만 쓰기 API는 `503`을 반환합니다.

## 참고

- Netlify 함수는 그대로 `server.js`를 감싸서 사용합니다.
- 기존 Google OAuth 관련 보조 파일은 남아 있을 수 있지만, 현재 실행 경로에서는 사용하지 않습니다.
