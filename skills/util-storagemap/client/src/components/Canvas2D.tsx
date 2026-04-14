import { useState, useRef, useEffect, useCallback } from 'react'
import type { Furniture } from '../types'

interface Canvas2DProps {
  furnitureList: Furniture[]
  selectedFurnitureId: string | null
  onFurnitureSelect: (furnitureId: string) => void
  onFurnitureMove: (furnitureId: string, x: number, y: number) => void
  onFurnitureResize: (furnitureId: string, width: number, height: number) => void
  highlightedFurnitureId?: string | null
}

interface DragState {
  furnitureId: string
  type: 'move' | 'resize'
  startX: number
  startY: number
  startPosX: number
  startPosY: number
  startWidth: number
  startHeight: number
  currentX: number
  currentY: number
  currentW: number
  currentH: number
}

const TYPE_COLORS: Record<string, string> = {
  '교구장': '#7c3aed',
  '교탁': '#6366f1',
  '서랍장': '#8b5cf6',
  '옷장': '#a78bfa',
  '책장': '#2563eb',
  '선반': '#0891b2',
  '수납함': '#059669',
  '사물함': '#d97706',
  '기타': '#64748b',
}

function getColor(furniture: Furniture) {
  if (furniture.color) return furniture.color
  return TYPE_COLORS[furniture.type] || '#7c3aed'
}

export default function Canvas2D({
  furnitureList,
  selectedFurnitureId,
  onFurnitureSelect,
  onFurnitureMove,
  onFurnitureResize,
  highlightedFurnitureId,
}: Canvas2DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dragState, setDragState] = useState<DragState | null>(null)

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, furnitureId: string, type: 'move' | 'resize') => {
      e.preventDefault()
      e.stopPropagation()
      const f = furnitureList.find((f) => f.furniture_id === furnitureId)
      if (!f) return

      setDragState({
        furnitureId,
        type,
        startX: e.clientX,
        startY: e.clientY,
        startPosX: f.pos_x,
        startPosY: f.pos_y,
        startWidth: f.width || 100,
        startHeight: f.height || 60,
        currentX: f.pos_x,
        currentY: f.pos_y,
        currentW: f.width || 100,
        currentH: f.height || 60,
      })

      if (type === 'move') {
        onFurnitureSelect(furnitureId)
      }
    },
    [furnitureList, onFurnitureSelect],
  )

  useEffect(() => {
    if (!dragState) return

    const handleMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - dragState.startX
      const dy = e.clientY - dragState.startY

      if (dragState.type === 'move') {
        // Snap to 10px grid (from Storage-Map-1)
        let newX = Math.round((dragState.startPosX + dx) / 10) * 10
        let newY = Math.round((dragState.startPosY + dy) / 10) * 10
        newX = Math.max(0, newX)
        newY = Math.max(0, newY)
        setDragState((prev) => prev ? { ...prev, currentX: newX, currentY: newY } : null)
      } else {
        const newW = Math.max(50, Math.round((dragState.startWidth + dx) / 10) * 10)
        const newH = Math.max(30, Math.round((dragState.startHeight + dy) / 10) * 10)
        setDragState((prev) => prev ? { ...prev, currentW: newW, currentH: newH } : null)
      }
    }

    const handleMouseUp = () => {
      if (dragState.type === 'move') {
        onFurnitureMove(dragState.furnitureId, dragState.currentX, dragState.currentY)
      } else {
        onFurnitureResize(dragState.furnitureId, dragState.currentW, dragState.currentH)
      }
      setDragState(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [dragState, onFurnitureMove, onFurnitureResize])

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white rounded-2xl border-2 border-slate-200 overflow-hidden grid-pattern"
      style={{ minHeight: '500px', height: 'calc(100vh - 320px)' }}
      onClick={() => onFurnitureSelect('')}
    >
      {furnitureList.map((f) => {
        const isDragging = dragState?.furnitureId === f.furniture_id
        const x = isDragging && dragState.type === 'move' ? dragState.currentX : f.pos_x
        const y = isDragging && dragState.type === 'move' ? dragState.currentY : f.pos_y
        const w = isDragging && dragState.type === 'resize' ? dragState.currentW : (f.width || 100)
        const h = isDragging && dragState.type === 'resize' ? dragState.currentH : (f.height || 60)
        const isSelected = selectedFurnitureId === f.furniture_id
        const isHighlighted = highlightedFurnitureId === f.furniture_id
        const color = getColor(f)

        return (
          <div
            key={f.furniture_id}
            className={`absolute flex flex-col items-center justify-center rounded-xl select-none transition-shadow ${
              isDragging
                ? 'cursor-grabbing shadow-2xl z-20 scale-[1.03]'
                : 'cursor-grab hover:shadow-lg'
            } ${
              isSelected
                ? 'ring-3 ring-blue-500 shadow-lg z-10'
                : isHighlighted
                  ? 'ring-3 ring-yellow-400 shadow-lg z-10 marker-highlight'
                  : ''
            }`}
            style={{
              left: `${x}px`,
              top: `${y}px`,
              width: `${w}px`,
              height: `${h}px`,
              backgroundColor: color,
              transition: isDragging ? 'none' : 'box-shadow 0.2s, transform 0.15s',
            }}
            onMouseDown={(e) => handleMouseDown(e, f.furniture_id, 'move')}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Label */}
            <div className="text-white text-xs font-bold text-center truncate px-2 leading-tight drop-shadow-sm">
              {f.name}
            </div>
            {f.type && (
              <div className="text-white/70 text-[10px] mt-0.5">{f.type}</div>
            )}

            {/* Item count badge (from Storage-Map-1) */}
            {(f.itemCount !== undefined && f.itemCount > 0) && (
              <div className="absolute -top-2.5 -right-2.5 bg-white text-violet-700 text-[10px] font-extrabold w-5 h-5 flex items-center justify-center rounded-full shadow-md ring-2 ring-violet-200">
                {f.itemCount}
              </div>
            )}

            {/* Resize handle (from v2-2d) */}
            {isSelected && (
              <div
                className="absolute bottom-0 right-0 w-4 h-4 bg-blue-500 cursor-se-resize rounded-tl-md opacity-80 hover:opacity-100"
                onMouseDown={(e) => handleMouseDown(e, f.furniture_id, 'resize')}
              />
            )}
          </div>
        )
      })}

      {/* Empty state */}
      {furnitureList.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400">
          <div className="text-center">
            <p className="text-5xl mb-3">🗺️</p>
            <p className="text-lg font-semibold">가구를 추가해주세요</p>
            <p className="text-sm mt-1">2D 평면도에 가구를 배치하면 물건을 관리할 수 있습니다</p>
          </div>
        </div>
      )}
    </div>
  )
}
