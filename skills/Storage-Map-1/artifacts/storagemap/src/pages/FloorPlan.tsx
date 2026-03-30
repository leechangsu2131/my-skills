import React, { useState, useRef, useEffect } from "react";
import { useRoute } from "wouter";
import { Layout } from "@/components/Layout";
import { useGetSpace, useListFurniture } from "@workspace/api-client-react";
import { 
  useCreateFurnitureMutation, 
  useUpdateFurnitureMutation,
  useDeleteFurnitureMutation 
} from "@/hooks/use-furniture-wrapper";
import { useListItemsByFurniture } from "@workspace/api-client-react";
import { FURNITURE_TYPE_LABELS } from "@/lib/utils";
import { Plus, ArrowLeft, X, Package, Trash2, Edit2, Archive } from "lucide-react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";

// Sub-component for the Sidebar that shows items in a selected furniture
function FurnitureDetailsSidebar({ 
  spaceId, 
  furnitureId, 
  onClose,
  furnitureName 
}: { 
  spaceId: string, 
  furnitureId: string, 
  onClose: () => void,
  furnitureName: string 
}) {
  const { data: items = [], isLoading } = useListItemsByFurniture(furnitureId);
  const deleteMutation = useDeleteFurnitureMutation(spaceId);

  const handleDelete = () => {
    if (items.length > 0) {
      alert("이 가구 안에 물건이 있습니다. 물건을 먼저 비우거나 삭제해주세요.");
      return;
    }
    if (confirm("가구를 삭제하시겠습니까?")) {
      deleteMutation.mutate({ furnitureId });
      onClose();
    }
  };

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white border-l shadow-2xl flex flex-col z-20 animate-in slide-in-from-right duration-300">
      <div className="p-4 border-b flex justify-between items-center bg-secondary/30">
        <div>
          <h3 className="font-bold text-lg text-foreground">{furnitureName}</h3>
          <p className="text-xs text-muted-foreground">{items.length}개의 물건</p>
        </div>
        <button onClick={onClose} className="p-2 bg-white rounded-full hover:bg-secondary transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4 flex gap-2 border-b">
        <button className="flex-1 bg-primary text-primary-foreground py-2 rounded-lg text-sm font-semibold flex justify-center items-center gap-1 hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" /> 물건 넣기
        </button>
        <button 
          onClick={handleDelete}
          className="p-2 bg-destructive/10 text-destructive rounded-lg hover:bg-destructive hover:text-white transition-colors"
          title="가구 삭제"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          <div className="text-center py-10 text-muted-foreground text-sm">로딩 중...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-12 h-12 text-border mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">비어 있습니다.</p>
          </div>
        ) : (
          items.map(item => (
            <div key={item.id} className="p-3 border rounded-xl bg-background hover:border-primary/50 transition-colors">
              <div className="font-semibold text-sm mb-1">{item.name}</div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{item.zoneName || "위치 미지정"}</span>
                <span>{item.quantity}개</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function FloorPlan() {
  const [, params] = useRoute("/spaces/:spaceId/map");
  const spaceId = params?.spaceId || "";
  
  const { data: space, isLoading: spaceLoading } = useGetSpace(spaceId);
  const { data: furnitureList = [], isLoading: furnitureLoading } = useListFurniture(spaceId);
  
  const createFurniture = useCreateFurnitureMutation();
  const updateFurniture = useUpdateFurnitureMutation(spaceId);

  const [selectedFurniture, setSelectedFurniture] = useState<any>(null);
  const [isAddMode, setIsAddMode] = useState(false);
  
  // Custom Drag State
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragState, setDragState] = useState<{ id: string, offsetX: number, offsetY: number, currentX: number, currentY: number } | null>(null);

  const handleAddDefaultFurniture = () => {
    createFurniture.mutate({
      spaceId,
      data: {
        name: `새 가구 ${furnitureList.length + 1}`,
        type: "shelf",
        posX: 50,
        posY: 50,
        width: 100,
        height: 60,
      }
    });
  };

  const handleMouseDown = (e: React.MouseEvent, f: any) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // offset from top-left of the furniture block
    setDragState({
      id: f.id,
      offsetX: x - (f.posX || 0),
      offsetY: y - (f.posY || 0),
      currentX: f.posX || 0,
      currentY: f.posY || 0
    });
    
    if (selectedFurniture?.id !== f.id) {
      setSelectedFurniture(f);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragState || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    let x = e.clientX - rect.left - dragState.offsetX;
    let y = e.clientY - rect.top - dragState.offsetY;

    // Snap to 10px grid
    x = Math.round(x / 10) * 10;
    y = Math.round(y / 10) * 10;

    // Bounds check
    x = Math.max(0, Math.min(x, rect.width - 100)); // assume 100 width
    y = Math.max(0, Math.min(y, rect.height - 60)); // assume 60 height

    setDragState(prev => prev ? { ...prev, currentX: x, currentY: y } : null);
  };

  const handleMouseUp = () => {
    if (dragState) {
      const original = furnitureList.find(f => f.id === dragState.id);
      if (original && (original.posX !== dragState.currentX || original.posY !== dragState.currentY)) {
        updateFurniture.mutate({
          furnitureId: dragState.id,
          data: {
            posX: dragState.currentX,
            posY: dragState.currentY
          }
        });
      }
      setDragState(null);
    }
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => handleMouseUp();
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, [dragState]);

  if (spaceLoading) return <Layout><div className="p-10 text-center">로딩 중...</div></Layout>;
  if (!space) return <Layout><div className="p-10 text-center">공간을 찾을 수 없습니다.</div></Layout>;

  return (
    <Layout>
      <div className="flex flex-col h-[calc(100vh-8rem)]">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div className="flex items-center gap-4">
            <Link href="/spaces" className="p-2 bg-secondary rounded-xl hover:bg-border transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{space.name}</h1>
              <p className="text-sm text-muted-foreground">평면도에서 가구를 드래그하여 배치하세요.</p>
            </div>
          </div>
          <button 
            onClick={handleAddDefaultFurniture}
            disabled={createFurniture.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-foreground text-background font-semibold rounded-xl hover:bg-foreground/90 transition-colors shadow-md"
          >
            <Plus className="w-4 h-4" />
            가구 추가
          </button>
        </div>

        {/* Canvas Area */}
        <div className="relative flex-1 bg-white rounded-2xl border shadow-inner overflow-hidden">
          <div 
            ref={containerRef}
            className="absolute inset-0 bg-grid-pattern w-full h-full cursor-crosshair"
            onMouseMove={handleMouseMove}
            onClick={() => setSelectedFurniture(null)} // deselect when clicking background
          >
            {furnitureList.map(f => {
              const isDragging = dragState?.id === f.id;
              const x = isDragging ? dragState.currentX : (f.posX || 0);
              const y = isDragging ? dragState.currentY : (f.posY || 0);
              const isSelected = selectedFurniture?.id === f.id;

              return (
                <div
                  key={f.id}
                  onMouseDown={(e) => handleMouseDown(e, f)}
                  className={cn(
                    "absolute flex flex-col items-center justify-center rounded-lg shadow-md border-2 select-none transition-shadow",
                    isDragging ? "cursor-grabbing opacity-80 shadow-2xl z-10 scale-105" : "cursor-grab hover:shadow-lg hover:border-primary/50",
                    isSelected ? "border-primary bg-primary/10 ring-4 ring-primary/20" : "border-border bg-white"
                  )}
                  style={{
                    left: `${x}px`,
                    top: `${y}px`,
                    width: `${f.width || 100}px`,
                    height: `${f.height || 60}px`,
                    transition: isDragging ? 'none' : 'all 0.2s ease-out'
                  }}
                  onClick={(e) => e.stopPropagation()} // prevent deselecting
                >
                  <div className="text-xs font-bold truncate px-2 text-center w-full">{f.name}</div>
                  <div className="absolute -top-3 -right-3 bg-primary text-white text-[10px] font-bold w-6 h-6 flex items-center justify-center rounded-full shadow-sm ring-2 ring-white">
                    {f.itemCount || 0}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Details Sidebar overlay */}
          {selectedFurniture && (
            <FurnitureDetailsSidebar 
              spaceId={spaceId}
              furnitureId={selectedFurniture.id}
              furnitureName={selectedFurniture.name}
              onClose={() => setSelectedFurniture(null)}
            />
          )}
        </div>
      </div>
    </Layout>
  );
}
