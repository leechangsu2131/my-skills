import { useState, useMemo } from 'react'
import { Link } from 'wouter'
import { Search, Filter, Box, MapPin, Edit, Plus, AlertCircle, Package, ArrowRight } from 'lucide-react'
import { useAllItems, useSpaces } from '@/hooks/useStorageMap'
import type { Item, Furniture } from '../types'
import ItemModal from '@/components/ItemModal'
import Canvas2D from '@/components/Canvas2D'

export default function EnterpriseHome() {
  const { data: allData, isLoading } = useAllItems()
  const { data: spaces } = useSpaces()
  
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('All Assets')
  const [spaceFilter, setSpaceFilter] = useState('All Spaces')
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  
  const [modalState, setModalState] = useState<{isOpen: boolean, mode: 'add'|'edit'}>({
    isOpen: false,
    mode: 'add'
  })

  // Data processing
  const items = allData?.items || []
  const allFurniture = allData?.furniture || []

  // Ensure category and space mapping
  const categories = useMemo(() => {
    const cats = new Set(items.map(i => i.category).filter(Boolean) as string[])
    return ['All Assets', ...Array.from(cats)]
  }, [items])

  const spaceOptions = useMemo(() => {
    return ['All Spaces', ...(spaces?.map(s => s.name) || [])]
  }, [spaces])

  // Map each item to its parent furniture and space for display & filtering
  const itemsWithContext = useMemo(() => {
    return items.map(item => {
      const furniture = allFurniture.find(f => f.furniture_id === item.furniture_id)
      const space = spaces?.find(s => s.space_id === furniture?.space_id)
      return {
        ...item,
        furnitureName: furniture?.name || 'Unknown',
        spaceName: space?.name || 'Unknown Space',
        space_id: space?.space_id || ''
      }
    })
  }, [items, allFurniture, spaces])

  const filteredItems = useMemo(() => {
    return itemsWithContext.filter(item => {
      const matchSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (item.memo && item.memo.toLowerCase().includes(searchQuery.toLowerCase())) ||
                          item.category?.toLowerCase().includes(searchQuery.toLowerCase())
      
      const matchCategory = categoryFilter === 'All Assets' || item.category === categoryFilter
      const matchSpace = spaceFilter === 'All Spaces' || item.spaceName === spaceFilter

      return matchSearch && matchCategory && matchSpace
    })
  }, [itemsWithContext, searchQuery, categoryFilter, spaceFilter])

  // Select first item by default if there is a filtered list but no selection
  // or if the selected item disappears from the filtered list.
  if (filteredItems.length > 0 && (!selectedItem || !filteredItems.find(i => i.item_id === selectedItem.item_id))) {
      setSelectedItem(filteredItems[0])
  } else if (filteredItems.length === 0 && selectedItem) {
      setSelectedItem(null)
  }

  // Derive contextual data for the selected item
  const selectedFurniture = selectedItem ? allFurniture.find(f => f.furniture_id === selectedItem.furniture_id) : null
  const selectedSpace = selectedFurniture && spaces ? spaces.find(s => s.space_id === selectedFurniture.space_id) : null
  const spaceFurnitureList = selectedSpace ? allFurniture.filter(f => f.space_id === selectedSpace.space_id) : []

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
          <p className="text-slate-500 font-medium">Initializing Enterprise Core...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Search & Filters Header */}
      <section className="bg-white px-8 py-6 flex flex-col gap-6 shadow-sm z-10 shrink-0 border-b border-slate-200/50">
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full relative group">
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 ml-1">
              Universal Inventory Locator
            </label>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Scan Item Name, Memo, or Category..."
                className="w-full pl-12 pr-4 py-4 bg-[#f2f4f6] border-none rounded-xl focus:ring-2 focus:ring-blue-800 text-lg font-medium placeholder:text-slate-400 transition-all"
              />
            </div>
          </div>
          <div className="flex gap-4 w-full md:w-auto">
            <div className="flex-1 md:w-48">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 ml-1">Category</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full bg-[#f2f4f6] border-none rounded-xl text-sm py-4 px-4 font-semibold text-slate-700 cursor-pointer focus:ring-2 focus:ring-blue-800"
              >
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="flex-1 md:w-48">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 ml-1">Space</label>
              <select
                value={spaceFilter}
                onChange={(e) => setSpaceFilter(e.target.value)}
                className="w-full bg-[#f2f4f6] border-none rounded-xl text-sm py-4 px-4 font-semibold text-slate-700 cursor-pointer focus:ring-2 focus:ring-blue-800"
              >
                {spaceOptions.map(space => <option key={space} value={space}>{space}</option>)}
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Hybrid Results View */}
      <section className="flex-1 flex overflow-hidden bg-[#f7f9fb]">
        {/* Results List (Left) */}
        <div className="w-full md:w-[360px] lg:w-[400px] border-r border-slate-200/60 overflow-y-auto bg-slate-50 flex flex-col">
          <div className="p-4 flex items-center justify-between border-b border-slate-200/60 bg-white sticky top-0 z-10 shrink-0">
             <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{filteredItems.length} Results Found</span>
             <Filter className="w-4 h-4 text-slate-400 cursor-pointer hover:text-slate-700" />
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {filteredItems.map(item => {
              const isActive = selectedItem?.item_id === item.item_id
              return (
                <div
                  key={item.item_id}
                  onClick={() => setSelectedItem(item)}
                  className={`p-5 cursor-pointer transition-all border-b border-slate-200/50 group ${
                    isActive 
                      ? 'bg-white border-l-4 border-l-blue-800 shadow-sm' 
                      : 'hover:bg-white/60 border-l-4 border-l-transparent'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1.5">
                    <h3 className={`font-bold font-sans text-base ${isActive ? 'text-blue-900' : 'text-slate-800 group-hover:text-blue-700'}`}>
                      {item.name}
                    </h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      item.quantity && item.quantity > 0 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {item.quantity && item.quantity > 0 ? 'In Stock' : 'Out of Stock'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3 truncate line-clamp-1">
                    {item.memo || `Category: ${item.category || 'None'}`}
                  </p>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate">{item.spaceName} &gt; {item.furnitureName}</span>
                  </div>
                </div>
              )
            })}
            
            {filteredItems.length === 0 && (
              <div className="p-10 flex flex-col items-center text-center text-slate-400">
                <Box className="w-12 h-12 mb-3 text-slate-300" />
                <p className="font-semibold text-sm">No items found</p>
                <p className="text-xs mt-1">Try adjusting your search criteria</p>
              </div>
            )}
          </div>
        </div>

        {/* Details Pane (Right) */}
        <div className="flex-1 overflow-y-auto bg-white p-8 lg:p-12 relative flex flex-col">
          {selectedItem && selectedFurniture && selectedSpace ? (
            <div className="max-w-5xl mx-auto w-full flex flex-col gap-10">
              
              {/* Top Identity Area */}
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                    {selectedSpace.name} / {selectedItem.category || 'Uncategorized'}
                  </span>
                </div>
                <div className="flex items-start justify-between">
                  <h2 className="text-4xl lg:text-5xl font-black text-[#1B365D] tracking-tight leading-tight">
                    {selectedItem.name}
                  </h2>
                  <button 
                    onClick={() => setModalState({ isOpen: true, mode: 'edit' })}
                    className="mt-2 bg-slate-100 text-slate-700 px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:bg-slate-200 transition-colors shadow-sm shrink-0"
                  >
                    <Edit className="w-4 h-4" />
                    Edit Specs
                  </button>
                </div>
                {selectedItem.memo && (
                  <p className="mt-4 text-slate-500 text-lg leading-relaxed max-w-3xl">
                    {selectedItem.memo}
                  </p>
                )}
              </div>

              {/* Bento Details Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#f7f9fb] p-6 rounded-2xl border border-slate-200/60 shadow-sm">
                  <Package className="w-5 h-5 text-blue-800 mb-3" />
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Stock Level</p>
                  <p className="text-2xl font-black text-[#1B365D]">
                    {selectedItem.quantity || 1} <span className="text-sm font-medium text-slate-500">units</span>
                  </p>
                </div>
                <div className="bg-[#f7f9fb] p-6 rounded-2xl border border-slate-200/60 shadow-sm">
                  <Box className="w-5 h-5 text-blue-800 mb-3" />
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Furniture</p>
                  <p className="text-lg font-bold text-[#1B365D] line-clamp-1">{selectedFurniture.name}</p>
                </div>
                <div className="bg-[#f7f9fb] p-6 rounded-2xl border border-slate-200/60 shadow-sm">
                  <MapPin className="w-5 h-5 text-blue-800 mb-3" />
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Space</p>
                  <p className="text-lg font-bold text-[#1B365D] line-clamp-1">{selectedSpace.name}</p>
                </div>
                <div className="bg-[#f7f9fb] p-6 rounded-2xl border border-slate-200/60 shadow-sm">
                  <AlertCircle className="w-5 h-5 text-blue-800 mb-3" />
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Status</p>
                  <p className="text-lg font-bold text-emerald-600">Active</p>
                </div>
              </div>

              {/* Contextual Map Viewer */}
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-end">
                  <h3 className="text-lg font-bold text-[#1B365D] uppercase tracking-wider">Location Map Overlay</h3>
                  <Link href={`/spaces/${selectedSpace.space_id}/map`}>
                    <button className="text-sm font-bold text-blue-700 hover:text-blue-900 flex items-center gap-1">
                      Open Full Map <ArrowRight className="w-4 h-4" />
                    </button>
                  </Link>
                </div>
                
                <div className="rounded-3xl bg-white overflow-hidden h-[450px] relative border border-slate-200/60 shadow-inner group">
                  {/* Reuse Canvas2D but disable mutating capabilities for this view */}
                  <div className="absolute inset-0 scale-[0.95] origin-center opacity-90 transition-transform group-hover:scale-100 ease-in-out duration-700">
                    <Canvas2D
                      furnitureList={spaceFurnitureList}
                      selectedFurnitureId={selectedFurniture.furniture_id}
                      highlightedFurnitureId={selectedFurniture.furniture_id}
                      onFurnitureSelect={() => {}}
                      onFurnitureMove={() => {}}
                      onFurnitureResize={() => {}}
                    />
                  </div>
                  
                  {/* Map Floating HUD */}
                  <div className="absolute top-6 left-6 bg-white/90 backdrop-blur-md p-4 rounded-2xl shadow-xl flex flex-col gap-1 border border-white">
                    <h4 className="text-xs font-black uppercase tracking-widest text-blue-900">{selectedSpace.name}</h4>
                    <p className="text-[10px] text-slate-500 font-semibold">{selectedFurniture.name} Area</p>
                  </div>

                  <div className="absolute bottom-6 left-6 pointer-events-none">
                     <div className="bg-blue-900/95 backdrop-blur text-white px-4 py-2 rounded-full text-xs font-bold shadow-xl flex items-center gap-2 border border-blue-400/30">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        RADAR LOCKED
                     </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 bg-[#f2f4f6] rounded-full flex items-center justify-center mx-auto mb-6">
                  <Search className="w-8 h-8 text-slate-300" />
                </div>
                <h3 className="text-2xl font-bold text-slate-300 mb-2">No Item Selected</h3>
                <p className="text-slate-400 font-medium">Select an item from the universal locator<br/>to display its detailed telemetry pane.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Item Form Modal */}
      {modalState.isOpen && (
        <ItemModal
          initialData={modalState.mode === 'edit' && selectedItem ? selectedItem : undefined}
          initialFurnitureId={modalState.mode === 'edit' && selectedItem ? selectedItem.furniture_id : undefined}
          furnitureList={allFurniture}
          onClose={() => setModalState({ isOpen: false, mode: 'add' })}
        />
      )}
      
      {/* Floating Action Badge - Bottom Right */}
      <button 
        onClick={() => setModalState({ isOpen: true, mode: 'add' })}
        className="fixed bottom-8 right-8 w-14 h-14 bg-blue-900 text-white rounded-full shadow-2xl shadow-blue-900/40 flex items-center justify-center hover:-translate-y-1 transition-transform z-50 group font-bold"
        title="Add New Entry"
      >
        <Plus className="w-6 h-6" />
      </button>

    </div>
  )
}
