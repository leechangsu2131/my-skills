import { useState, useEffect } from 'react'
import type { Furniture } from '@/types'
import { useCreateFurniture, useUpdateFurniture } from '@/hooks/useStorageMap'

const FURNITURE_TYPES = ['교구장', '교탁', '서랍장', '옷장', '책장', '선반', '수납함', '사물함', '기타']
const PRESET_COLORS = [
  { label: '기본 보라', value: '#7c3aed' },
  { label: '파스텔 블루', value: '#3b82f6' },
  { label: '민트 그린', value: '#10b981' },
  { label: '머스타드', value: '#eab308' },
  { label: '코랄 핑크', value: '#f43f5e' },
  { label: '인디고', value: '#4f46e5' },
  { label: '차콜', value: '#475569' },
]

interface FurnitureModalProps {
  initialData?: Furniture
  spaceId?: string
  furnitureListLength?: number
  onClose: () => void
}

export default function FurnitureModal({ initialData, spaceId, furnitureListLength = 0, onClose }: FurnitureModalProps) {
  const isEditing = !!initialData
  const [name, setName] = useState(initialData?.name || '')
  const [type, setType] = useState(initialData?.type || '기타')
  const [color, setColor] = useState(initialData?.color || PRESET_COLORS[0].value)
  const [notes, setNotes] = useState(initialData?.notes || '')
  
  const createMutation = useCreateFurniture()
  const updateMutation = useUpdateFurniture()
  const isPending = createMutation.isPending || updateMutation.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    
    if (isEditing) {
      updateMutation.mutate({
        furnitureId: initialData.furniture_id,
        name: name.trim(),
        type,
        color,
        notes: notes.trim()
      }, {
        onSuccess: () => onClose()
      })
    } else if (spaceId) {
      createMutation.mutate({
        name: name.trim(),
        space_id: spaceId,
        type,
        color,
        notes: notes.trim(),
        pos_x: 50 + furnitureListLength * 30,
        pos_y: 50 + furnitureListLength * 20,
      }, {
        onSuccess: () => onClose()
      })
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-2xl shadow-2xl w-full max-w-sm flex flex-col max-h-[90vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between shrink-0">
          <h2 className="text-xl font-bold text-slate-800">
            {isEditing ? '가구 설정 변경' : '새 가구 추가'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex flex-col gap-5">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 flex justify-between">
              가구 이름 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium transition-all"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 앞 교구장"
              autoFocus
            />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">유형</label>
            <div className="flex flex-wrap gap-2">
              {FURNITURE_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                    type === t
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300 hover:text-blue-700'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">테마 색상</label>
            <div className="flex flex-wrap gap-3">
              {PRESET_COLORS.map(c => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setColor(c.value)}
                  className={`w-8 h-8 rounded-full border-2 transition-all ${
                    color === c.value ? 'border-slate-800 scale-110 shadow-md' : 'border-transparent hover:scale-105 shadow-sm'
                  }`}
                  style={{ backgroundColor: c.value }}
                  title={c.label}
                />
              ))}
              
              <div className="relative w-8 h-8 rounded-full border border-slate-300 overflow-hidden shadow-sm flex items-center justify-center cursor-pointer hover:border-slate-800 transition-all">
                <input 
                  type="color" 
                  value={color} 
                  onChange={(e) => setColor(e.target.value)}
                  className="absolute -inset-2 w-12 h-12 cursor-pointer opacity-0"
                  title="사용자 지정 색상"
                />
                <div 
                  className="w-full h-full" 
                  style={{ 
                    background: 'conic-gradient(red, yellow, lime, aqua, blue, magenta, red)'
                  }} 
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 flex justify-between">
              메모 (선택)
            </label>
            <textarea
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium transition-all min-h-[80px]"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="가구에 대한 간단한 설명을 남겨주세요"
            />
          </div>

          <div className="flex gap-3 pt-3 mt-1 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 border border-slate-200 bg-white rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 hover:text-slate-800 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isPending || !name.trim()}
              className="flex-1 py-3 bg-[#1B365D] text-white rounded-xl text-sm font-bold hover:bg-[#122440] disabled:opacity-50 transition-colors shadow-sm"
            >
              {isPending ? '저장 중...' : (isEditing ? '변경사항 저장' : '가구 생성')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
