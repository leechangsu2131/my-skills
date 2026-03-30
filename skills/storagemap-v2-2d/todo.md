# StorageMap v2.1 (2D) - 개발 진행 현황

## 데이터베이스 및 스키마
- [x] 공간(Space) 테이블 생성 - space_id, name, description
- [x] 가구(Furniture) 테이블 생성 - furniture_id, space_id, name, type, photo_url, pos_x, pos_y, width, height, zones_json, notes
- [x] 구획(Zone) 테이블 생성 - zone_id, furniture_id, name, position_desc, photo_url
- [x] 물건(Item) 테이블 생성 - item_id, name, furniture_id, zone_id, category, tags, memo, photo_url, quantity, context, created_at, updated_at
- [x] 이동 이력(History) 테이블 생성 - history_id, item_id, from_furniture, from_zone, to_furniture, to_zone, moved_at, note
- [x] 마이그레이션 SQL 생성 및 적용

## 백엔드 기능
- [x] Space 관련 tRPC 프로시저 (생성, 조회, 수정, 삭제)
- [x] Furniture 관련 tRPC 프로시저 (생성, 조회, 수정, 삭제, 위치 업데이트)
- [x] Zone 관련 tRPC 프로시저 (생성, 조회, 수정, 삭제)
- [x] Item 관련 tRPC 프로시저 (생성, 조회, 수정, 삭제, 검색)
- [x] History 관련 tRPC 프로시저 (조회, 자동 기록)
- [x] 검색 프로시저 (이름/태그/메모 우선순위 검색)
- [x] 데이터 품질 지표 계산 프로시저

## 프론트엔드 - 레이아웃 및 네비게이션
- [x] 메인 레이아웃 구조 설계 (사이드바 + 메인 영역)
- [x] 상단 네비게이션 바 구현
- [x] 공간 선택 탭
- [x] 통계 정보 표시

## 프론트엔드 - 2D 평면도 및 가구 관리
- [x] 2D 캔버스 컴포넌트 구현 (HTML/CSS 기반)
- [x] 가구 마커 렌더링 (직사각형, 색상, 라벨)
- [x] 가구 마커 드래그 기능 (마우스 이벤트)
- [x] 가구 마커 위치 자동 저장 (pos_x, pos_y)
- [x] 가구 마커 크기 조정 기능 (width, height)
- [x] 가구 마커 색상 커스터마이징 UI
- [x] 공간 추가/편집 UI
- [x] 가구 추가/편집/삭제 UI
- [x] 가구 유형 선택 기능

## 프론트엔드 - 물건 검색
- [x] 검색 입력 필드 구현
- [x] 검색 결과 표시 (우선순위: 이름 완전 일치 → 부분 일치 → 태그 → 메모)
- [x] 검색 결과에 경로 표시 (공간 > 가구 > 구획)
- [x] 2D 평면도에서 검색된 가구 하이라이트

## 프론트엔드 - 물건 관리
- [x] 물건 등록 폼 (이름, 가구, 구획, 분류, 태그, 메모, 수량)
- [x] 필수 필드 검증 (이름, 가구)
- [x] 물건 편집 UI
- [x] 물건 삭제 UI
- [x] 가구 클릭 시 물건 목록 표시
- [x] 물건 목록에서 추가/편집/삭제 기능

## 프론트엔드 - 물건 이동 및 이력
- [x] 물건 위치 변경 시 History 자동 기록
- [x] 이동 이력 조회 UI
- [x] 이동 이력 타임라인 표시

## 프론트엔드 - 데이터 품질 대시보드
- [x] 필수 필드 완성도 지표 표시
- [x] 가구 배정률 지표 표시
- [x] 이름 중복률 지표 표시
- [x] 데이터 최신성 지표 표시 (30일 이내 업데이트 비율)
- [x] 각 지표별 Pass/주의/위험 상태 표시
- [x] 대시보드 페이지 구현

## 테스트
- [x] 백엔드 유닛 테스트 (tRPC 프로시저) - 14개 테스트 모두 통과
- [x] 프론트엔드 통합 테스트 (검색, 등록, 수정, 삭제) - 15개 테스트 모두 통과
- [x] 2D 평면도 드래그 기능 테스트 - 드래그 로직 검색 및 위치 업데이트 테스트 포함
- [x] 데이터 품질 지표 계산 테스트 - 4개 지표 계산 로직 테스트 포함

## 배포 및 최적화
- [x] 성능 최적화 (쿼리 최적화, 렌더링 최적화) - 기본 최적화 완료
- [x] 에러 처리 및 사용자 피드백 - tRPC 에러 처리 및 toast 알림 구현
- [x] 반응형 디자인 검증 - Tailwind CSS 4 기반 반응형 디자인 적용
- [x] 최종 체크포인트 생성 (2f35db62)
