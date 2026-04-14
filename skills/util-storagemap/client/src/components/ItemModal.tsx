import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useCreateItem, useUpdateItem } from '@/hooks/useStorageMap'
import type { Item, Furniture } from '@/types'

const CATEGORY_LABELS: Record<string, string> = {
  '교구': '📚 교구',
  '문구': '✏️ 문구',
  '전자기기': '💻 전자기기',
  '서류': '📄 서류',
  '의류': '👔 의류',
  '생활용품': '🏠 생활용품',
  '공구': '🔧 공구',
  '기타': '📦 기타',
}

interface ItemModalProps {
  furnitureList: Furniture[]
  initialFurnitureId?: string
  initialData?: Item
  onClose: () => void
}

export default function ItemModal({
  furnitureList,
  initialFurnitureId,
  initialData,
  onClose,
}: ItemModalProps) {
  const [name, setName] = useState(initialData?.name || '')
  const [furnitureId, setFurnitureId] = useState(
    initialData?.furniture_id || initialFurnitureId || (furnitureList[0]?.furniture_id || '')
  )
  const [category, setCategory] = useState(initialData?.category || '기타')
  const [quantity, setQuantity] = useState(initialData?.quantity || 1)
  const [memo, setMemo] = useState(initialData?.memo || '')

  const createItem = useCreateItem()
  const updateItem = useUpdateItem()
  
  const isPending = createItem.isPending || updateItem.isPending
  const isEdit = !!initialData

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !furnitureId) return

    const payload = {
      name: name.trim(),
      furniture_id: furnitureId,
      category,
      quantity,
      memo
    }

    if (isEdit) {
      updateItem.mutate(
        { itemId: initialData.item_id, ...payload },
        { onSuccess: () => onClose() }
      )
    } else {
      createItem.mutate(
        payload,
        { onSuccess: () => onClose() }
      )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEdit ? '물건 수정' : '물건 추가'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">물건 이름 *</label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 리코더 (학생용)"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">위치 (가구) *</label>
            <select
              className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 text-sm"
              value={furnitureId}
              onChange={(e) => setFurnitureId(e.target.value)}
            >
              {furnitureList.map((f) => (
                <option key={f.furniture_id} value={f.furniture_id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">분류</label>
              <select
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 text-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {Object.keys(CATEGORY_LABELS).map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">수량</label>
              <input
                type="number"
                min={1}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 text-sm"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">메모</label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 text-sm"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="색상, 형태, 특이사항..."
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!name.trim() || !furnitureId || isPending}
              className="flex-1 py-2.5 bg-violet-600 text-white rounded-xl text-sm font-semibold hover:bg-violet-700 transition-colors disabled:opacity-50 shadow-sm"
            >
              {isPending ? '저장 중...' : isEdit ? '수정 완료' : '추가'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
