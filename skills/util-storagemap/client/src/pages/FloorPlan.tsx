import { useState, useMemo } from 'react'
import { useRoute, Link } from 'wouter'
import { ArrowLeft, Plus, Search } from 'lucide-react'
import Canvas2D from '@/components/Canvas2D'
import FurnitureSidebar from '@/components/FurnitureSidebar'
import ItemModal from '@/components/ItemModal'
import FurnitureModal from '@/components/FurnitureModal'
import {
  useFurnitureBySpace,
  useAllItems,
  useSpaces,
  useCreateFurniture,
  useUpdateFurniturePosition,
  useDeleteFurniture,
  useSearch,
  useCreateItem,
  useDeleteItem,
} from '@/hooks/useStorageMap'
import type { Furniture, Item } from '@/types'

export default function FloorPlan() {
  const [, params] = useRoute('/spaces/:spaceId/map')
  const spaceId = params?.spaceId || ''

  const { data: spaces } = useSpaces()
  const { data: furnitureList = [], isLoading } = useFurnitureBySpace(spaceId)
  const space = spaces?.find((s) => s.space_id === spaceId)

  const [selectedFurnitureId, setSelectedFurnitureId] = useState<string | null>(null)
  const [highlightedFurnitureId, setHighlightedFurnitureId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [furnitureModalState, setFurnitureModalState] = useState<{ isOpen: boolean; mode: 'add' | 'edit' }>({
    isOpen: false,
    mode: 'add'
  })
  
  // For ItemModal we need either a furnitureId to add to, or an existing item to edit
  const [itemModalState, setItemModalState] = useState<{ isOpen: boolean; mode: 'add' | 'edit'; furnitureId?: string; item?: Item }>({
    isOpen: false,
    mode: 'add'
  })

  // To list all furniture in the dropdown when adding/editing items
  const { data: allData } = useAllItems()
  const allFurniture = allData?.furniture || []

  const createFurniture = useCreateFurniture()
  const updatePosition = useUpdateFurniturePosition()
  const deleteFurniture = useDeleteFurniture()
  const deleteItem = useDeleteItem()
  const { data: searchData } = useSearch(searchQuery)

  // Highlight furniture from search
  useMemo(() => {
    if (searchData?.results?.length) {
      const matched = searchData.results[0]
      if (matched.furniture_id) {
        setHighlightedFurnitureId(matched.furniture_id)
      }
    } else {
      setHighlightedFurnitureId(null)
    }
  }, [searchData])

  const selectedFurniture = furnitureList.find(
    (f: Furniture) => f.furniture_id === selectedFurnitureId,
  )
  const selectedItems: Item[] = selectedFurniture?.items || []

  const handleAddItemClick = (furnitureId: string) => {
    setItemModalState({ isOpen: true, mode: 'add', furnitureId })
  }

  const handleEditItemClick = (item: Item) => {
    setItemModalState({ isOpen: true, mode: 'edit', item })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-500">로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 7rem)' }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4 shrink-0 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Link href="/">
            <span className="p-2 bg-white rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer shadow-sm">
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </span>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {space?.name || '평면도'}
            </h1>
            <p className="text-sm text-slate-400">
              가구를 드래그하여 배치하고, 클릭하여 물건을 관리하세요
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Search in floorplan */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              className="pl-9 pr-3 py-2 w-48 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 shadow-sm"
              placeholder="물건 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button
            onClick={() => setFurnitureModalState({ isOpen: true, mode: 'add' })}
            disabled={createFurniture.isPending}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white font-semibold rounded-xl hover:bg-slate-700 transition-colors shadow-md text-sm"
          >
            <Plus className="w-4 h-4" />
            가구 추가
          </button>
        </div>
      </div>

      {/* Canvas + Sidebar */}
      <div className="relative flex-1 overflow-hidden rounded-2xl shadow-sm border border-slate-200">
        <Canvas2D
          furnitureList={furnitureList}
          selectedFurnitureId={selectedFurnitureId}
          onFurnitureSelect={(id) => setSelectedFurnitureId(id || null)}
          onFurnitureMove={(id, x, y) => updatePosition.mutate({ furnitureId: id, x, y })}
          onFurnitureResize={(id, w, h) => updatePosition.mutate({ furnitureId: id, width: w, height: h })}
          highlightedFurnitureId={highlightedFurnitureId}
        />

        {selectedFurniture && (
          <div className="absolute top-0 right-0 h-full shrink-0 w-72 md:w-80 shadow-2xl overflow-hidden border-l border-slate-200 bg-white z-30 sidebar-enter hidden md:block">
            <FurnitureSidebar
              furniture={selectedFurniture}
              spaceName={space?.name || ''}
              items={selectedItems}
              onClose={() => setSelectedFurnitureId(null)}
              onAddItem={handleAddItemClick}
              onEditItem={handleEditItemClick}
              onDeleteItem={(itemId) => deleteItem.mutate(itemId)}
              onDeleteFurniture={(id) => deleteFurniture.mutate(id)}
              onEditFurniture={() => setFurnitureModalState({ isOpen: true, mode: 'edit' })}
            />
          </div>
        )}
      </div>

      {/* Add / Edit Furniture Modal */}
      {furnitureModalState.isOpen && (
        <FurnitureModal
          initialData={furnitureModalState.mode === 'edit' && selectedFurniture ? selectedFurniture : undefined}
          spaceId={furnitureModalState.mode === 'add' ? spaceId : undefined}
          furnitureListLength={furnitureList.length}
          onClose={() => setFurnitureModalState({ isOpen: false, mode: 'add' })}
        />
      )}

      {/* Add/Edit Item Modal */}
      {itemModalState.isOpen && (
        <ItemModal
          furnitureList={allFurniture.length > 0 ? allFurniture : furnitureList}
          initialData={itemModalState.item}
          initialFurnitureId={itemModalState.furnitureId}
          onClose={() => setItemModalState({ isOpen: false, mode: 'add' })}
        />
      )}
    </div>
  )
}
