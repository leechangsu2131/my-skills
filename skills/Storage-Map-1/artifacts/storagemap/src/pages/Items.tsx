import React, { useState } from "react";
import { Layout } from "@/components/Layout";
import { useListItems, useListSpaces, useListFurniture } from "@workspace/api-client-react";
import { useCreateItemMutation, useDeleteItemMutation } from "@/hooks/use-items-wrapper";
import { CATEGORY_LABELS, formatKoreanDate } from "@/lib/utils";
import { Search, Plus, Filter, Package, Trash2, MapPin, X } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";

export default function Items() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSpace, setFilterSpace] = useState<string>("");
  
  const { data: spaces = [] } = useListSpaces();
  const { data: items = [], isLoading } = useListItems({
    q: searchQuery || undefined,
    spaceId: filterSpace || undefined
  });
  
  const deleteItemMutation = useDeleteItemMutation();

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const handleDelete = (id: string, name: string) => {
    if (confirm(`'${name}' 물건을 삭제하시겠습니까?`)) {
      deleteItemMutation.mutate({ itemId: id });
    }
  };

  return (
    <Layout>
      <div className="mb-8 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
        <div>
          <h1 className="text-3xl font-bold text-foreground">전체 물건 관리</h1>
          <p className="text-muted-foreground mt-1">시스템에 등록된 모든 물건을 검색하고 관리합니다.</p>
        </div>
        
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground font-semibold rounded-xl shadow-md hover:bg-primary/90 transition-all"
        >
          <Plus className="w-5 h-5" /> 새 물건 등록
        </button>
      </div>

      {/* Filters & Search */}
      <div className="bg-white p-4 rounded-2xl border shadow-sm flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="물건 이름, 태그 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-secondary/50 border-transparent focus:bg-white focus:border-primary rounded-xl transition-all outline-none ring-0"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-muted-foreground" />
          <select 
            value={filterSpace}
            onChange={(e) => setFilterSpace(e.target.value)}
            className="px-4 py-2.5 bg-secondary/50 border-transparent focus:bg-white focus:border-primary rounded-xl outline-none min-w-[150px]"
          >
            <option value="">모든 공간</option>
            {spaces.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>

      {/* List */}
      <div className="bg-white border rounded-2xl overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-10 text-center animate-pulse text-muted-foreground">목록을 불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="py-12 border-none">
            <EmptyState 
              title="물건이 없습니다" 
              description="검색 조건에 맞는 물건이 없거나 아직 등록된 물건이 없습니다." 
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-secondary/50 text-muted-foreground uppercase">
                <tr>
                  <th className="px-6 py-4 font-semibold">물건 이름</th>
                  <th className="px-6 py-4 font-semibold">카테고리</th>
                  <th className="px-6 py-4 font-semibold">현재 위치</th>
                  <th className="px-6 py-4 font-semibold">수량</th>
                  <th className="px-6 py-4 font-semibold text-right">관리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {items.map(item => (
                  <tr key={item.id} className="hover:bg-secondary/20 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-bold text-foreground">{item.name}</div>
                      {item.tags && item.tags.length > 0 && (
                        <div className="text-xs text-muted-foreground mt-1">#{item.tags.join(', #')}</div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="bg-secondary px-2.5 py-1 rounded-md font-medium text-xs">
                        {item.category ? CATEGORY_LABELS[item.category] : '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 font-medium text-primary">
                        <MapPin className="w-3.5 h-3.5" />
                        {item.spaceName} &gt; {item.furnitureName}
                      </div>
                      {item.zoneName && <div className="text-xs text-muted-foreground mt-1 ml-5">상세: {item.zoneName}</div>}
                    </td>
                    <td className="px-6 py-4 font-semibold">{item.quantity}개</td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => handleDelete(item.id, item.name)}
                        className="p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {isAddModalOpen && (
        <CreateItemModal 
          onClose={() => setIsAddModalOpen(false)} 
          spaces={spaces}
        />
      )}
    </Layout>
  );
}

// Separate component for the complex add modal
function CreateItemModal({ onClose, spaces }: { onClose: () => void, spaces: any[] }) {
  const [formData, setFormData] = useState({
    name: "",
    spaceId: "",
    furnitureId: "",
    category: "other" as any,
    quantity: 1,
    memo: ""
  });
  
  const createMutation = useCreateItemMutation(formData.furnitureId);
  
  // Fetch furniture when a space is selected
  const { data: furnitureList = [] } = useListFurniture(formData.spaceId, { query: { enabled: !!formData.spaceId } });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.furnitureId) return;
    
    createMutation.mutate({
      data: {
        name: formData.name,
        furnitureId: formData.furnitureId,
        category: formData.category,
        quantity: formData.quantity,
        memo: formData.memo
      }
    }, {
      onSuccess: onClose
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-5 border-b flex justify-between items-center bg-secondary/30">
          <h2 className="text-xl font-bold text-foreground">새 물건 등록</h2>
          <button onClick={onClose} className="p-2 hover:bg-white rounded-full transition-colors"><X className="w-5 h-5"/></button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-semibold mb-1.5">물건 이름 *</label>
            <input
              required autoFocus
              className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="예: 아이패드 충전기"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1.5">공간 선택 *</label>
              <select
                required
                className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                value={formData.spaceId}
                onChange={e => setFormData({...formData, spaceId: e.target.value, furnitureId: ""})}
              >
                <option value="">공간을 선택하세요</option>
                {spaces.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5">가구 선택 *</label>
              <select
                required
                disabled={!formData.spaceId || furnitureList.length === 0}
                className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50"
                value={formData.furnitureId}
                onChange={e => setFormData({...formData, furnitureId: e.target.value})}
              >
                <option value="">가구를 선택하세요</option>
                {furnitureList.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1.5">카테고리</label>
              <select
                className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                value={formData.category}
                onChange={e => setFormData({...formData, category: e.target.value as any})}
              >
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5">수량</label>
              <input
                type="number" min="1" required
                className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                value={formData.quantity}
                onChange={e => setFormData({...formData, quantity: parseInt(e.target.value) || 1})}
              />
            </div>
          </div>

          <div className="pt-4 border-t flex justify-end gap-3">
            <button
              type="button" onClick={onClose}
              className="px-6 py-3 rounded-xl font-semibold bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !formData.furnitureId}
              className="px-8 py-3 rounded-xl font-semibold bg-primary text-primary-foreground shadow-lg shadow-primary/20 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none"
            >
              {createMutation.isPending ? "저장 중..." : "등록 완료"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
