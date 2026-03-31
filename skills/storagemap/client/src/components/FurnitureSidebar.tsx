import { X, Package, Trash2, Plus, Edit2 } from 'lucide-react'
import type { Furniture, Item } from '../types'

interface FurnitureSidebarProps {
  furniture: Furniture
  spaceName: string
  items: Item[]
  onClose: () => void
  onAddItem: (furnitureId: string) => void
  onDeleteItem: (itemId: string) => void
  onDeleteFurniture: (furnitureId: string) => void
  onEditItem?: (item: Item) => void
  onEditFurniture?: () => void
}

export default function FurnitureSidebar({
  furniture,
  spaceName,
  items,
  onClose,
  onAddItem,
  onDeleteItem,
  onDeleteFurniture,
  onEditItem,
  onEditFurniture,
}: FurnitureSidebarProps) {
  const handleDelete = () => {
    if (items.length > 0) {
      alert('이 가구 안에 물건이 있습니다. 물건을 먼저 비우거나 삭제해주세요.')
      return
    }
    if (confirm('가구를 삭제하시겠습니까?')) {
      onDeleteFurniture(furniture.furniture_id)
      onClose()
    }
  }

  return (
    <div className="flex-shrink-0 w-72 md:w-80 bg-white h-full flex flex-col sidebar-enter">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 bg-gradient-to-r from-violet-50 to-indigo-50">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-bold text-lg text-slate-900">{furniture.name}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {spaceName} &gt; {furniture.name}
            </p>
            <p className="text-xs text-slate-400 mt-1">{items.length}개의 물건</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 bg-white rounded-full hover:bg-slate-100 transition-colors shadow-sm"
          >
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="p-3 flex gap-2 border-b border-slate-100">
        <button
          onClick={() => onAddItem(furniture.furniture_id)}
          className="flex-1 bg-violet-600 text-white py-2 rounded-xl text-sm font-semibold flex justify-center items-center gap-1.5 hover:bg-violet-700 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" /> 물건 추가
        </button>
        <button
          onClick={onEditFurniture}
          className="p-2 bg-slate-50 text-slate-600 rounded-xl hover:bg-slate-200 transition-colors"
          title="가구 정보 수정"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <button
          onClick={handleDelete}
          className="p-2 bg-red-50 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-colors"
          title="가구 삭제"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Items list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {items.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-12 h-12 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">비어 있습니다</p>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.item_id}
              onClick={() => onEditItem?.(item)}
              className="p-3 border border-slate-100 rounded-xl bg-white hover:border-violet-300 hover:shadow-sm transition-all group cursor-pointer relative"
              title="클릭하여 물건 수정"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0 pr-6">
                  <div className="font-semibold text-sm text-slate-800 truncate group-hover:text-violet-700 transition-colors">
                    {item.name}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                    {item.category && (
                      <span className="px-1.5 py-0.5 bg-violet-50 text-violet-600 rounded-md font-medium">
                        {item.category}
                      </span>
                    )}
                    <span>수량: {item.quantity || 1}</span>
                  </div>
                  {item.memo && (
                    <p className="text-xs text-slate-400 mt-1 truncate">{item.memo}</p>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm(`'${item.name}'을(를) 삭제하시겠습니까?`)) {
                      onDeleteItem(item.item_id)
                    }
                  }}
                  className="absolute right-3 top-3 p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                  title="물건 삭제"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
