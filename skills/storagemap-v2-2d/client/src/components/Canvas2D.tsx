import React, { useRef, useEffect, useState, useCallback } from "react";
import type { Furniture } from "../../../drizzle/schema";

interface Canvas2DProps {
  furnitureList: Furniture[];
  selectedFurnitureId: string | null;
  onFurnitureSelect: (furnitureId: string) => void;
  onFurnitureMove: (furnitureId: string, posX: number, posY: number) => void;
  onFurnitureResize: (furnitureId: string, width: number, height: number) => void;
  highlightedFurnitureId?: string | null;
}

interface DragState {
  furnitureId: string;
  type: "move" | "resize";
  startX: number;
  startY: number;
  startPosX: number;
  startPosY: number;
  startWidth: number;
  startHeight: number;
}

export default function Canvas2D({
  furnitureList,
  selectedFurnitureId,
  onFurnitureSelect,
  onFurnitureMove,
  onFurnitureResize,
  highlightedFurnitureId,
}: Canvas2DProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, furnitureId: string, type: "move" | "resize") => {
      e.preventDefault();
      const furniture = furnitureList.find((f) => f.furnitureId === furnitureId);
      if (!furniture) return;

      setDragState({
        furnitureId,
        type,
        startX: e.clientX,
        startY: e.clientY,
        startPosX: furniture.posX,
        startPosY: furniture.posY,
        startWidth: furniture.width,
        startHeight: furniture.height,
      });

      if (type === "move") {
        onFurnitureSelect(furnitureId);
      }
    },
    [furnitureList, onFurnitureSelect]
  );

  useEffect(() => {
    if (!dragState) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - dragState.startX;
      const deltaY = e.clientY - dragState.startY;

      if (dragState.type === "move") {
        const newPosX = Math.max(0, dragState.startPosX + deltaX);
        const newPosY = Math.max(0, dragState.startPosY + deltaY);
        onFurnitureMove(dragState.furnitureId, newPosX, newPosY);
      } else if (dragState.type === "resize") {
        const newWidth = Math.max(50, dragState.startWidth + deltaX);
        const newHeight = Math.max(30, dragState.startHeight + deltaY);
        onFurnitureResize(dragState.furnitureId, newWidth, newHeight);
      }
    };

    const handleMouseUp = () => {
      setDragState(null);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragState, onFurnitureMove, onFurnitureResize]);

  const getMarkerClass = (furnitureId: string) => {
    let classes = "absolute cursor-move transition-all ";
    if (selectedFurnitureId === furnitureId) {
      classes += "ring-2 ring-blue-500 shadow-lg";
    } else if (highlightedFurnitureId === furnitureId) {
      classes += "ring-2 ring-yellow-400 shadow-lg";
    } else {
      classes += "hover:shadow-md";
    }
    return classes;
  };

  return (
    <div
      ref={canvasRef}
      className="relative w-full bg-gradient-to-br from-slate-50 to-slate-100 border-2 border-slate-300 rounded-lg overflow-hidden"
      style={{ height: "600px" }}
    >
      {/* 그리드 배경 */}
      <svg
        className="absolute inset-0 w-full h-full opacity-10"
        style={{
          backgroundImage:
            "linear-gradient(0deg, transparent 24%, rgba(0,0,0,.05) 25%, rgba(0,0,0,.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,.05) 75%, rgba(0,0,0,.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(0,0,0,.05) 25%, rgba(0,0,0,.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,.05) 75%, rgba(0,0,0,.05) 76%, transparent 77%, transparent)",
          backgroundSize: "50px 50px",
        }}
      />

      {/* 가구 마커들 */}
      {furnitureList.map((furn) => (
        <div
          key={furn.furnitureId}
          className={getMarkerClass(furn.furnitureId)}
          style={{
            left: `${furn.posX}px`,
            top: `${furn.posY}px`,
            width: `${furn.width}px`,
            height: `${furn.height}px`,
            backgroundColor: furn.color || "#9333ea",
            borderRadius: "6px",
          }}
          onMouseDown={(e) => handleMouseDown(e, furn.furnitureId, "move")}
        >
          {/* 가구 라벨 */}
          <div className="w-full h-full flex items-center justify-center p-2">
            <div className="text-white text-xs font-semibold text-center truncate">
              {furn.name}
            </div>
          </div>

          {/* 리사이즈 핸들 */}
          {selectedFurnitureId === furn.furnitureId && (
            <div
              className="absolute bottom-0 right-0 w-4 h-4 bg-blue-500 cursor-se-resize rounded-bl"
              onMouseDown={(e) => handleMouseDown(e, furn.furnitureId, "resize")}
            />
          )}

          {/* 가구 사진 미리보기 */}
          {furn.photoUrl && (
            <div
              className="absolute inset-0 rounded-md opacity-0 hover:opacity-100 transition-opacity bg-cover bg-center"
              style={{ backgroundImage: `url(${furn.photoUrl})` }}
            />
          )}
        </div>
      ))}

      {/* 빈 상태 메시지 */}
      {furnitureList.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400">
          <div className="text-center">
            <p className="text-lg font-semibold">가구를 추가해주세요</p>
            <p className="text-sm">2D 평면도에 가구를 배치하면 물건을 관리할 수 있습니다</p>
          </div>
        </div>
      )}
    </div>
  );
}
