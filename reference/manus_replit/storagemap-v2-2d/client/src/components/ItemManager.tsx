import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Trash2, Plus, Edit2, Search } from "lucide-react";
import type { Item, Furniture, Zone } from "../../../drizzle/schema";

interface ItemManagerProps {
  items: Item[];
  furnitureList: Furniture[];
  zoneList: Zone[];
  selectedFurnitureId: string | null;
  onItemCreate: (item: Partial<Item>) => void;
  onItemUpdate: (itemId: string, updates: Partial<Item>) => void;
  onItemDelete: (itemId: string) => void;
  onSearch: (query: string) => void;
  searchResults?: Item[];
}

export default function ItemManager({
  items,
  furnitureList,
  zoneList,
  selectedFurnitureId,
  onItemCreate,
  onItemUpdate,
  onItemDelete,
  onSearch,
  searchResults,
}: ItemManagerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [newItemName, setNewItemName] = useState("");
  const [newItemCategory, setNewItemCategory] = useState("other");
  const [newItemTags, setNewItemTags] = useState("");
  const [newItemMemo, setNewItemMemo] = useState("");
  const [newItemQuantity, setNewItemQuantity] = useState(1);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editItemName, setEditItemName] = useState("");
  const [editItemCategory, setEditItemCategory] = useState("other");
  const [editItemTags, setEditItemTags] = useState("");
  const [editItemMemo, setEditItemMemo] = useState("");
  const [editItemQuantity, setEditItemQuantity] = useState(1);

  const selectedFurniture = furnitureList.find(
    (f) => f.furnitureId === selectedFurnitureId
  );
  const furnitureItems = items.filter(
    (item) => item.furnitureId === selectedFurnitureId
  );

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      onSearch(query);
    }
  };

  const handleCreateItem = () => {
    if (newItemName.trim() && selectedFurnitureId) {
      onItemCreate({
        name: newItemName,
        furnitureId: selectedFurnitureId,
        category: newItemCategory as any,
        tags: newItemTags
          .split(",")
          .map((t) => t.trim())
          .filter((t) => t),
        memo: newItemMemo,
        quantity: newItemQuantity,
      });
      setNewItemName("");
      setNewItemCategory("other");
      setNewItemTags("");
      setNewItemMemo("");
      setNewItemQuantity(1);
    }
  };

  const handleUpdateItem = (itemId: string) => {
    onItemUpdate(itemId, {
      name: editItemName,
      category: editItemCategory as any,
      tags: editItemTags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t),
      memo: editItemMemo,
      quantity: editItemQuantity,
    });
    setEditingItemId(null);
  };

  const displayItems = searchResults && searchQuery ? searchResults : furnitureItems;

  return (
    <div className="space-y-4">
      {/* 검색 */}
      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
        <Input
          placeholder="물건 검색... (이름, 태그, 메모)"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* 검색 결과 표시 */}
      {searchResults && searchQuery && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <p className="text-sm font-semibold text-blue-900">
            검색 결과: {searchResults.length}개
          </p>
          {searchResults.length > 0 && (
            <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
              {searchResults.map((item) => {
                const furn = furnitureList.find((f) => f.furnitureId === item.furnitureId);
                const zone = zoneList.find((z) => z.zoneId === item.zoneId);
                return (
                  <div
                    key={item.itemId}
                    className="text-xs p-2 bg-white rounded hover:bg-blue-100 cursor-pointer"
                  >
                    <p className="font-semibold">{item.name}</p>
                    <p className="text-slate-600">
                      위치: {furn?.name}
                      {zone ? ` > ${zone.name}` : ""}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 선택된 가구의 물건 목록 */}
      {selectedFurniture && !searchQuery && (
        <div className="space-y-2 pt-4 border-t">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">
              {selectedFurniture.name} ({furnitureItems.length})
            </h3>
            <Dialog>
              <DialogTrigger asChild>
                <Button size="sm" variant="outline">
                  <Plus className="w-4 h-4 mr-1" />
                  물건 추가
                </Button>
              </DialogTrigger>
              <DialogContent className="max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>새 물건 추가</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="item-name">물건 이름 *</Label>
                    <Input
                      id="item-name"
                      placeholder="예: 가위, 노트북"
                      value={newItemName}
                      onChange={(e) => setNewItemName(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="item-category">분류</Label>
                    <select
                      id="item-category"
                      value={newItemCategory}
                      onChange={(e) => setNewItemCategory(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                    >
                      <option value="electronics">전자기기</option>
                      <option value="clothing">의류</option>
                      <option value="living_goods">생활용품</option>
                      <option value="documents">서류</option>
                      <option value="tools">공구</option>
                      <option value="teaching_materials">교육용품</option>
                      <option value="stationery">문구</option>
                      <option value="other">기타</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="item-tags">태그 (쉼표로 구분)</Label>
                    <Input
                      id="item-tags"
                      placeholder="예: 중요, 겨울, 충전"
                      value={newItemTags}
                      onChange={(e) => setNewItemTags(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="item-memo">메모</Label>
                    <Input
                      id="item-memo"
                      placeholder="색상, 형태, 포장 등 식별 정보"
                      value={newItemMemo}
                      onChange={(e) => setNewItemMemo(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="item-quantity">수량</Label>
                    <Input
                      id="item-quantity"
                      type="number"
                      min="1"
                      value={newItemQuantity}
                      onChange={(e) => setNewItemQuantity(parseInt(e.target.value))}
                    />
                  </div>
                  <Button onClick={handleCreateItem} className="w-full">
                    추가
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {/* 물건 목록 */}
          <div className="bg-slate-50 rounded-md p-3 max-h-48 overflow-y-auto space-y-2">
            {furnitureItems.length > 0 ? (
              furnitureItems.map((item) => (
                <div
                  key={item.itemId}
                  className="bg-white p-2 rounded border border-slate-200 hover:border-slate-400 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm">{item.name}</p>
                      {item.tags && Array.isArray(item.tags) && (item.tags as string[]).length > 0 ? (
                        <p className="text-xs text-slate-500">
                          {(item.tags as string[]).join(", ")}
                        </p>
                      ) : null}
                      {item.memo && (
                        <p className="text-xs text-slate-600 line-clamp-1">
                          {item.memo}
                        </p>
                      )}
                      <p className="text-xs text-slate-500 mt-1">
                        수량: {item.quantity}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Dialog>
                        <DialogTrigger asChild>
                          <button
                            onClick={() => {
                              setEditingItemId(item.itemId);
                              setEditItemName(item.name);
                              setEditItemCategory(item.category || "other");
                              setEditItemTags(
                                ((item.tags as unknown as string[]) || []).join(", ")
                              );
                              setEditItemMemo(item.memo || "");
                              setEditItemQuantity(item.quantity);
                            }}
                            className="p-1 hover:bg-blue-100 rounded"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[90vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>물건 수정</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <div>
                              <Label htmlFor="edit-item-name">물건 이름</Label>
                              <Input
                                id="edit-item-name"
                                value={editItemName}
                                onChange={(e) => setEditItemName(e.target.value)}
                              />
                            </div>
                            <div>
                              <Label htmlFor="edit-item-category">분류</Label>
                              <select
                                id="edit-item-category"
                                value={editItemCategory}
                                onChange={(e) => setEditItemCategory(e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                              >
                                <option value="electronics">전자기기</option>
                                <option value="clothing">의류</option>
                                <option value="living_goods">생활용품</option>
                                <option value="documents">서류</option>
                                <option value="tools">공구</option>
                                <option value="teaching_materials">교육용품</option>
                                <option value="stationery">문구</option>
                                <option value="other">기타</option>
                              </select>
                            </div>
                            <div>
                              <Label htmlFor="edit-item-tags">태그</Label>
                              <Input
                                id="edit-item-tags"
                                value={editItemTags}
                                onChange={(e) => setEditItemTags(e.target.value)}
                              />
                            </div>
                            <div>
                              <Label htmlFor="edit-item-memo">메모</Label>
                              <Input
                                id="edit-item-memo"
                                value={editItemMemo}
                                onChange={(e) => setEditItemMemo(e.target.value)}
                              />
                            </div>
                            <div>
                              <Label htmlFor="edit-item-quantity">수량</Label>
                              <Input
                                id="edit-item-quantity"
                                type="number"
                                min="1"
                                value={editItemQuantity}
                                onChange={(e) => setEditItemQuantity(parseInt(e.target.value))}
                              />
                            </div>
                            <Button
                              onClick={() => handleUpdateItem(item.itemId)}
                              className="w-full"
                            >
                              수정
                            </Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                      <button
                        onClick={() => onItemDelete(item.itemId)}
                        className="p-1 hover:bg-red-100 text-red-600 rounded"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">물건을 추가해주세요</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
