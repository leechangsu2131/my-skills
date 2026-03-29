# StorageMap 기술 업그레이드 가이드

## 🎯 벤치마킹 기반 개선 방향

### 1. 프론트엔드 현대화

#### 현재 → 개선 방향
```javascript
// 현재: Vanilla JS
class StorageMapApp {
  constructor() { ... }
}

// 개선: React + TypeScript
interface StorageMapProps {
  spaces: Space[];
  selectedSpaceId: string;
}

const StorageMap: React.FC<StorageMapProps> = ({ spaces, selectedSpaceId }) => {
  // React hooks 사용
};
```

#### 2. UI 컴포넌트 라이브러리 도입
```bash
# Radix UI + Tailwind CSS
npm install @radix-ui/react-dialog @radix-ui/react-select
npm install tailwindcss
```

#### 3. 타입 세이프한 API 통신
```typescript
// 현재: fetch + manual typing
const response = await fetch('/api/data');
const data = await response.json();

// 개선: tRPC
const spacesQuery = trpc.space.list.useQuery();
// 자동 타입 추론 + 에러 핸들링
```

### 2. 2D 캔버스 기능 고도화

#### 드래그 & 리사이즈 구현
```typescript
// 벤치마킹: Canvas2D.tsx 참조
interface DragState {
  furnitureId: string;
  type: "move" | "resize";
  startX: number;
  startY: number;
  startPosX: number;
  startPosY: number;
}

const handleMouseDown = useCallback(
  (e: React.MouseEvent, furnitureId: string, type: "move" | "resize") => {
    // 드래그 로직 구현
  },
  [furnitureList, onFurnitureSelect]
);
```

#### 그리드 배경 및 스냅
```css
/* 벤치마킹: 그리드 배경 */
.grid-background {
  background-image: 
    linear-gradient(0deg, transparent 24%, rgba(0,0,0,.05) 25%, ...),
    linear-gradient(90deg, transparent 24%, rgba(0,0,0,.05) 25%, ...);
  background-size: 50px 50px;
}
```

### 3. 데이터 품질 대시보드

#### 지표 계산 로직
```typescript
// 벤치마킹: QualityDashboard.tsx
interface QualityMetrics {
  fieldCompletionRate: number;    // 필수 필드 완성도
  furnitureAssignmentRate: number; // 가구 배정률
  nameDuplicationRate: number;   // 이름 중복률
  dataFreshnessRate: number;     // 데이터 최신성
}

const calculateMetrics = (items: Item[], furniture: Furniture[]): QualityMetrics => {
  // 각 지표 계산 로직
};
```

### 4. 실시간 데이터 동기화

#### React Query + WebSocket
```typescript
// 실시간 데이터 업데이트
const itemsQuery = trpc.item.list.useQuery(undefined, {
  refetchInterval: 5000, // 5초마다 자동 리프레시
});

// 실시간 위치 업데이트
const updateFurnitureMutation = trpc.furniture.updatePosition.useMutation({
  onSuccess: () => {
    // 다른 클라이언트에 실시간 반영
    queryClient.invalidateQueries(['furniture.list']);
  }
});
```

## 🚀 단계적 마이그레이션 계획

### Phase 1: 기본 구조 개선 (1-2주)
1. **React + TypeScript 도입**
   ```bash
   npm create vite@latest storagemap-react --template react-ts
   ```

2. **기존 컴포넌트 마이그레이션**
   - SearchComponent → React 컴포넌트
   - FurnitureMarker → React 컴포넌트
   - Sidebar → React 컴포넌트

3. **Tailwind CSS 도입**
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

### Phase 2: 고급 기능 구현 (2-3주)
1. **2D 캔버스 고도화**
   - 드래그 & 리사이즈 기능
   - 그리드 스냅 기능
   - 가구 사진 미리보기

2. **데이터 품질 대시보드**
   - 지표 계산 로직
   - 시각적 차트 표시
   - Pass/주의/위험 상태 표시

### Phase 3: 백엔드 현대화 (2-3주)
1. **tRPC 도입**
   ```bash
   npm install @trpc/server @trpc/client
   ```

2. **데이터베이스 마이그레이션**
   - Google Sheets → MySQL/PostgreSQL
   - Drizzle ORM 도입

3. **실시간 기능**
   - WebSocket 연동
   - 다중 사용자 지원

## 📋 기술 스택 최종 목표

```json
{
  "frontend": {
    "framework": "React 19 + TypeScript",
    "styling": "Tailwind CSS 4 + Radix UI",
    "state": "React Query + tRPC",
    "build": "Vite + esbuild"
  },
  "backend": {
    "runtime": "Node.js",
    "framework": "Express + tRPC",
    "database": "MySQL + Drizzle ORM",
    "auth": "OAuth 2.0 + JWT"
  },
  "features": {
    "2d-canvas": "드래그 & 리사이즈",
    "realtime": "WebSocket 실시간 동기화",
    "dashboard": "데이터 품질 모니터링",
    "testing": "Vitest + 통합 테스트"
  }
}
```

## 🎯 즉시 적용 가능한 개선사항

### 1. CSS 개선 (벤치마킹 적용)
```css
/* 그리드 배경 추가 */
.floor-plan {
  background-image: 
    linear-gradient(0deg, transparent 24%, rgba(0,0,0,.05) 25%, rgba(0,0,0,.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,.05) 75%, rgba(0,0,0,.05) 76%, transparent 77%, transparent),
    linear-gradient(90deg, transparent 24%, rgba(0,0,0,.05) 25%, rgba(0,0,0,.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,.05) 75%, rgba(0,0,0,.05) 76%, transparent 77%, transparent);
  background-size: 50px 50px;
}
```

### 2. 드래그 기능 개선
```javascript
// 벤치마킹 Canvas2D.tsx 로직 적용
class DragHandler {
  constructor() {
    this.dragState = null;
  }
  
  handleMouseDown(e, furnitureId, type) {
    this.dragState = {
      furnitureId,
      type,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: furniture.posX,
      startPosY: furniture.posY
    };
  }
}
```

### 3. 데이터 품질 지표 계산
```javascript
// 벤치마킹 지표 계산 로직 적용
function calculateQualityMetrics(items, furniture) {
  const fieldCompletionRate = (items.filter(item => 
    item.name && item.furniture_id
  ).length / items.length) * 100;
  
  const furnitureAssignmentRate = (items.filter(item => 
    item.furniture_id
  ).length / items.length) * 100;
  
  return { fieldCompletionRate, furnitureAssignmentRate };
}
```

이 가이드를 참고하여 단계적으로 기술을 업그레이드할 수 있습니다!
