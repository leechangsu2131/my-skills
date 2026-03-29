# StorageMap Google Sheets 기반 장기 업그레이드 로드맵

## 🎯 비전: Google Sheets + 현대적 프론트엔드

Google Sheets를 데이터베이스로 유지하면서 React + TypeScript로 프론트엔드를 현대화합니다.

## 📊 기술 스택 목표

```json
{
  "frontend": {
    "framework": "React 19 + TypeScript",
    "styling": "Tailwind CSS 4 + Radix UI",
    "state": "React Query + Zustand",
    "build": "Vite",
    "data": "Google Sheets API v4"
  },
  "backend": {
    "runtime": "Node.js",
    "framework": "Express + tRPC",
    "database": "Google Sheets (유지)",
    "auth": "OAuth 2.0 + JWT",
    "cache": "Redis (선택)"
  }
}
```

## 🚀 Phase별 업그레이드 계획

### Phase 1: 프론트엔드 현대화 (2-3주)

#### 1.1 React + TypeScript 기반 구축
```bash
# 새 프로젝트 생성
npm create vite@latest storagemap-react --template react-ts
cd storagemap-react

# 필수 의존성 설치
npm install @tanstack/react-query
npm install @radix-ui/react-dialog @radix-ui/react-select
npm install tailwindcss
npm install lucide-react
npm install axios
```

#### 1.2 Google Sheets API 통합
```typescript
// lib/google-sheets.ts
export class GoogleSheetsService {
  private sheets: sheets_v4.Sheets;
  private spreadsheetId: string;

  constructor() {
    const auth = new google.auth.GoogleAuth({
      keyFile: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });
    
    this.sheets = google.sheets({ version: 'v4', auth });
    this.spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID!;
  }

  // CRUD operations
  async getItems(): Promise<Item[]> {
    const response = await this.sheets.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: 'Items!A:L'
    });
    return this.parseSheetData(response.data.values);
  }

  async addItem(item: Omit<Item, 'item_id' | 'created_at' | 'updated_at'>): Promise<Item> {
    const newItem = {
      item_id: generateId(),
      ...item,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    await this.sheets.spreadsheets.values.append({
      spreadsheetId: this.spreadsheetId,
      range: 'Items!A:L',
      valueInputOption: 'USER_ENTERED',
      resource: {
        values: [Object.values(newItem)]
      }
    });

    return newItem;
  }
}
```

#### 1.3 React Query로 데이터 관리
```typescript
// hooks/useGoogleSheets.ts
export const useGoogleSheets = () => {
  const queryClient = useQueryClient();

  const itemsQuery = useQuery({
    queryKey: ['items'],
    queryFn: () => googleSheetsService.getItems(),
    staleTime: 5 * 60 * 1000, // 5분
  });

  const addItemMutation = useMutation({
    mutationFn: googleSheetsService.addItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      toast.success('물건이 추가되었습니다');
    }
  });

  return { itemsQuery, addItemMutation };
};
```

### Phase 2: 고급 2D 캔버스 (2-3주)

#### 2.1 벤치마킹 Canvas2D 컴포넌트 이식
```typescript
// components/Canvas2D.tsx
interface Canvas2DProps {
  furnitureList: Furniture[];
  selectedFurnitureId: string | null;
  onFurnitureSelect: (furnitureId: string) => void;
  onFurnitureMove: (furnitureId: string, x: number, y: number) => void;
}

export const Canvas2D: React.FC<Canvas2DProps> = ({
  furnitureList,
  selectedFurnitureId,
  onFurnitureSelect,
  onFurnitureMove
}) => {
  // 벤치마킹된 드래그 로직 적용
  const [dragState, setDragState] = useState<DragState | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent, furnitureId: string) => {
    const furniture = furnitureList.find(f => f.furnitureId === furnitureId);
    if (!furniture) return;

    setDragState({
      furnitureId,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: furniture.posX,
      startPosY: furniture.posY
    });

    onFurnitureSelect(furnitureId);
  }, [furnitureList, onFurnitureSelect]);

  // Google Sheets에 위치 실시간 저장
  const updateFurniturePosition = useMutation({
    mutationFn: async ({ furnitureId, x, y }: UpdatePositionParams) => {
      return googleSheetsService.updateFurniturePosition(furnitureId, x, y);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['furniture']);
    }
  });

  return (
    <div className="relative w-full h-600 bg-grid">
      {/* 가구 마커들 */}
      {furnitureList.map(furniture => (
        <FurnitureMarker
          key={furniture.furnitureId}
          furniture={furniture}
          isSelected={selectedFurnitureId === furniture.furnitureId}
          onMouseDown={handleMouseDown}
        />
      ))}
    </div>
  );
};
```

#### 2.2 드래그 & 리사이즈 기능
```typescript
// hooks/useDragAndDrop.ts
export const useDragAndDrop = (onMove: (id: string, x: number, y: number) => void) => {
  const [dragState, setDragState] = useState<DragState | null>(null);

  useEffect(() => {
    if (!dragState) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - dragState.startX;
      const deltaY = e.clientY - dragState.startY;
      
      const newX = Math.max(0, dragState.startPosX + deltaX);
      const newY = Math.max(0, dragState.startPosY + deltaY);
      
      onMove(dragState.furnitureId, newX, newY);
    };

    const handleMouseUp = () => {
      // Google Sheets에 위치 저장
      setDragState(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragState, onMove]);

  return { dragState, startDrag: setDragState };
};
```

### Phase 3: 데이터 품질 대시보드 (1-2주)

#### 3.1 Google Sheets 기반 지표 계산
```typescript
// hooks/useQualityMetrics.ts
export const useQualityMetrics = () => {
  const { data: items } = useItems();
  const { data: furniture } = useFurniture();

  const metrics = useMemo(() => {
    if (!items?.length || !furniture?.length) return null;

    // 필수 필드 완성도
    const fieldCompletionRate = (items.filter(item => 
      item.name && item.furniture_id
    ).length / items.length) * 100;

    // 가구 배정률
    const furnitureAssignmentRate = (items.filter(item => 
      item.furniture_id
    ).length / items.length) * 100;

    // 이름 중복률
    const nameGroups = items.reduce((acc, item) => {
      acc[item.name] = (acc[item.name] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const duplicateNames = Object.values(nameGroups).filter(count => count > 1);
    const nameDuplicationRate = (duplicateNames.length / Object.keys(nameGroups).length) * 100;

    // 데이터 최신성 (30일 이내)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    const recentItems = items.filter(item => 
      new Date(item.updated_at) > thirtyDaysAgo
    );
    
    const dataFreshnessRate = (recentItems.length / items.length) * 100;

    return {
      fieldCompletionRate,
      furnitureAssignmentRate,
      nameDuplicationRate,
      dataFreshnessRate,
      totalItems: items.length,
      totalFurniture: furniture.length
    };
  }, [items, furniture]);

  return { metrics };
};
```

#### 3.2 대시보드 UI
```typescript
// components/QualityDashboard.tsx
export const QualityDashboard: React.FC = () => {
  const { metrics } = useQualityMetrics();

  if (!metrics) return <div>로딩 중...</div>;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <MetricCard
        title="필수 필드 완성도"
        value={metrics.fieldCompletionRate}
        status={metrics.fieldCompletionRate > 95 ? 'pass' : metrics.fieldCompletionRate > 80 ? 'warning' : 'danger'}
      />
      <MetricCard
        title="가구 배정률"
        value={metrics.furnitureAssignmentRate}
        status={metrics.furnitureAssignmentRate > 90 ? 'pass' : metrics.furnitureAssignmentRate > 70 ? 'warning' : 'danger'}
      />
      <MetricCard
        title="이름 중복률"
        value={metrics.nameDuplicationRate}
        status={metrics.nameDuplicationRate < 5 ? 'pass' : metrics.nameDuplicationRate < 15 ? 'warning' : 'danger'}
      />
      <MetricCard
        title="데이터 최신성"
        value={metrics.dataFreshnessRate}
        status={metrics.dataFreshnessRate > 85 ? 'pass' : metrics.dataFreshnessRate > 60 ? 'warning' : 'danger'}
      />
    </div>
  );
};
```

### Phase 4: 실시간 기능 및 최적화 (2-3주)

#### 4.1 Google Sheets 변경 감지
```typescript
// lib/google-sheets-webhook.ts
// Google Apps Script 웹훅으로 실시간 변경 감지
export const setupGoogleSheetsWebhook = () => {
  // Google Apps Script에서 웹훅 설정
  // onChange 이벤트로 서버에 알림
};

// 서버에서 WebSocket으로 클라이언트에 실시간 전파
io.on('google-sheets-update', (data) => {
  // React Query 무효화
  queryClient.invalidateQueries(['items']);
  queryClient.invalidateQueries(['furniture']);
});
```

#### 4.2 캐싱 최적화
```typescript
// lib/cache.ts
export class GoogleSheetsCache {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private TTL = 5 * 60 * 1000; // 5분

  async get<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    const cached = this.cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < this.TTL) {
      return cached.data;
    }

    const data = await fetcher();
    this.cache.set(key, { data, timestamp: Date.now() });
    
    return data;
  }

  invalidate(key: string) {
    this.cache.delete(key);
  }
}
```

## 🛠️ Google Sheets 서비스 계정 설정

### 1. 서비스 계정 생성
```bash
# Google Cloud Console에서 서비스 계정 생성
gcloud iam service-accounts create storagemap-service \
    --display-name="StorageMap Service" \
    --description="Service account for StorageMap"
```

### 2. 키 파일 생성 및 권한 설정
```bash
# JSON 키 파일 다운로드
# 스프레드시트에 서비스 계정 이메일 공유 (편집자 권한)
```

### 3. 환경 설정
```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=./path/to/service-account-key.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

## 📋 마이그레이션 체크리스트

### Phase 1: 프론트엔드 현대화
- [ ] Vite + React + TypeScript 프로젝트 생성
- [ ] Google Sheets API 서비스 라이브러리 구현
- [ ] React Query로 데이터 상태 관리
- [ ] 기존 UI 컴포넌트 마이그레이션
- [ ] Tailwind CSS + Radix UI 적용

### Phase 2: 2D 캔버스 고도화
- [ ] Canvas2D 컴포넌트 React로 이식
- [ ] 드래그 & 리사이즈 기능 구현
- [ ] 그리드 배경 및 스냅 기능
- [ ] 실시간 위치 저장 (Google Sheets)

### Phase 3: 데이터 품질 대시보드
- [ ] 품질 지표 계산 로직 구현
- [ ] 대시보드 UI 컴포넌트 개발
- [ ] Pass/주의/위험 상태 표시
- [ ] 차트 및 시각화 요소 추가

### Phase 4: 실시간 기능
- [ ] Google Apps Script 웹훅 설정
- [ ] WebSocket 서버 구현
- [ ] 실시간 데이터 동기화
- [ ] 캐싱 최적화
- [ ] 성능 모니터링

## 🎯 최종 목표

Google Sheets의 **간편한 데이터 관리** 장점은 유지하면서, **현대적인 사용자 경험**과 **고급 기능**을 제공하는 하이브리드 솔루션:

✅ **Google Sheets 기반 데이터 관리** (유지)  
✅ **React + TypeScript 현대적 프론트엔드**  
✅ **고급 2D 캔버스 및 드래그 기능**  
✅ **데이터 품질 모니터링 대시보드**  
✅ **실시간 동기화 및 캐싱 최적화**  
✅ **스펙 문서 100% 준수**
