import { useState } from 'react'
import { Link } from 'wouter'
import { Search, MapPin, ArrowRight, Tag, Box, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSearch, useSpaces, useAllItems } from '@/hooks/useStorageMap'
import type { Item } from '@/types'
import ItemModal from '@/components/ItemModal'

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

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  const { data: searchData, isLoading: searchLoading } = useSearch(searchQuery)
  const { data: allData, isLoading: allLoading } = useAllItems()
  const { data: spaces } = useSpaces()

  const results = searchQuery
    ? searchData?.results || []
    : allData?.items?.slice(0, 12) || []
  const isLoading = searchQuery ? searchLoading : allLoading

  return (
    <div>
      {/* Hero search (from Storage-Map-1) */}
      <div className="relative rounded-3xl overflow-hidden mb-10 hero-gradient">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_50%)]" />
        <div className="relative px-6 py-16 sm:py-20 sm:px-12 flex flex-col items-center text-center">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4 drop-shadow-md">
            물건을 찾는 가장 빠른 방법
          </h1>
          <p className="text-violet-200 text-lg max-w-2xl mb-8">
            등록된 모든 물건의 위치를 5초 안에 확인하세요
          </p>

          <div className="w-full max-w-2xl relative group">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-400 group-focus-within:text-violet-500 transition-colors" />
            </div>
            <input
              type="text"
              className="w-full h-14 pl-12 pr-4 rounded-2xl bg-white text-lg text-slate-800 placeholder:text-slate-400 shadow-xl focus:outline-none focus:ring-4 focus:ring-white/30 transition-all"
              placeholder="물건 이름, 카테고리, 메모 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
          </div>

          {/* Space quick links */}
          {spaces && spaces.length > 0 && (
            <div className="flex gap-2 mt-6 flex-wrap justify-center">
              {spaces.map((s) => (
                <Link key={s.space_id} href={`/spaces/${s.space_id}/map`}>
                  <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-white/15 backdrop-blur-sm text-white text-sm font-medium rounded-xl hover:bg-white/25 transition-colors cursor-pointer">
                    <MapPin className="w-3.5 h-3.5" />
                    {s.name} 평면도
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Results header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-800">
          {searchQuery ? `"${searchQuery}" 검색 결과` : '등록된 물건'}
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            {results.length}개
          </span>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-violet-600 text-white text-sm font-semibold rounded-xl hover:bg-violet-700 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> 물건 추가
          </button>
        </div>
      </div>

      {/* Results grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-44 skeleton" />
          ))}
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-slate-200">
          <Box className="w-16 h-16 text-slate-200 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700 mb-2">
            {searchQuery ? '검색 결과가 없습니다' : '등록된 물건이 없습니다'}
          </h3>
          <p className="text-slate-400">
            {searchQuery
              ? '다른 검색어를 입력해보세요'
              : '평면도에서 가구를 클릭하여 물건을 등록해보세요'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <AnimatePresence>
            {results.map((item: Item) => (
              <motion.div
                key={item.item_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="group bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:shadow-xl hover:border-violet-100 transition-all duration-300"
              >
                {/* Name + category */}
                <div className="flex justify-between items-start mb-3">
                  <h3 
                    className="text-base font-bold text-slate-800 truncate pr-2 hover:text-violet-600 cursor-pointer"
                    onClick={() => setSelectedItem(item)}
                    title="클릭하여 수정하기"
                  >
                    {item.name}
                  </h3>
                  {item.category && (
                    <span className="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full bg-violet-50 text-violet-600">
                      {CATEGORY_LABELS[item.category] || item.category}
                    </span>
                  )}
                </div>

                {/* Location path */}
                {(item.path || item.furniture) && (
                  <div className="bg-slate-50 rounded-xl p-3 mb-3">
                    <div className="flex items-center text-xs font-medium text-slate-600 mb-1.5">
                      <MapPin className="w-3.5 h-3.5 text-violet-500 mr-1.5" />
                      위치 경로
                    </div>
                    <div className="flex items-center flex-wrap gap-1 text-sm text-slate-500">
                      {item.path ? (
                        <>
                          {item.path.split(' > ').map((part, i, arr) => (
                            <span key={i} className="flex items-center gap-1">
                              <span className={i === arr.length - 1 ? 'font-semibold text-violet-600' : 'font-medium text-slate-700'}>
                                {part}
                              </span>
                              {i < arr.length - 1 && <ArrowRight className="w-3 h-3 text-slate-300" />}
                            </span>
                          ))}
                        </>
                      ) : (
                        <span className="font-semibold text-violet-600">{item.furniture}</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Memo */}
                {item.memo && (
                  <p className="text-xs text-slate-400 mb-2 truncate">{item.memo}</p>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-50">
                  <span>수량: {item.quantity || 1}개</span>
                  {item.matchScore && (
                    <span className="text-violet-400 font-medium">
                      매칭 {item.matchScore}%
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Modals */}
      {(showAddModal || selectedItem) && (
        <ItemModal
          furnitureList={allData?.furniture || []}
          initialData={selectedItem || undefined}
          onClose={() => {
            setShowAddModal(false)
            setSelectedItem(null)
          }}
        />
      )}
    </div>
  )
}
