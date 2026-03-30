import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Trash2, Plus, Edit2 } from "lucide-react";
import type { Space, Furniture } from "../../../drizzle/schema";

interface SpaceManagerProps {
  spaces: Space[];
  selectedSpaceId: string | null;
  onSpaceSelect: (spaceId: string) => void;
  onSpaceCreate: (name: string, description?: string) => void;
  onSpaceUpdate: (spaceId: string, name: string, description?: string) => void;
  onSpaceDelete: (spaceId: string) => void;
  onFurnitureCreate: (spaceId: string, name: string, type?: string, color?: string) => void;
  furnitureList: Furniture[];
}

export default function SpaceManager({
  spaces,
  selectedSpaceId,
  onSpaceSelect,
  onSpaceCreate,
  onSpaceUpdate,
  onSpaceDelete,
  onFurnitureCreate,
  furnitureList,
}: SpaceManagerProps) {
  const [newSpaceName, setNewSpaceName] = useState("");
  const [newSpaceDesc, setNewSpaceDesc] = useState("");
  const [editingSpaceId, setEditingSpaceId] = useState<string | null>(null);
  const [editSpaceName, setEditSpaceName] = useState("");
  const [editSpaceDesc, setEditSpaceDesc] = useState("");
  const [newFurnitureName, setNewFurnitureName] = useState("");
  const [newFurnitureType, setNewFurnitureType] = useState("other");
  const [newFurnitureColor, setNewFurnitureColor] = useState("#9333ea");

  const handleCreateSpace = () => {
    if (newSpaceName.trim()) {
      onSpaceCreate(newSpaceName, newSpaceDesc);
      setNewSpaceName("");
      setNewSpaceDesc("");
    }
  };

  const handleUpdateSpace = (spaceId: string) => {
    if (editSpaceName.trim()) {
      onSpaceUpdate(spaceId, editSpaceName, editSpaceDesc);
      setEditingSpaceId(null);
    }
  };

  const handleCreateFurniture = () => {
    if (selectedSpaceId && newFurnitureName.trim()) {
      onFurnitureCreate(selectedSpaceId, newFurnitureName, newFurnitureType, newFurnitureColor);
      setNewFurnitureName("");
      setNewFurnitureType("other");
      setNewFurnitureColor("#9333ea");
    }
  };

  const selectedSpace = spaces.find((s) => s.spaceId === selectedSpaceId);

  return (
    <div className="space-y-4">
      {/* 공간 탭 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">공간 관리</h3>
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Plus className="w-4 h-4 mr-1" />
                공간 추가
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>새 공간 추가</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="space-name">공간 이름</Label>
                  <Input
                    id="space-name"
                    placeholder="예: 우리 집, 3학년 2반"
                    value={newSpaceName}
                    onChange={(e) => setNewSpaceName(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="space-desc">설명 (선택)</Label>
                  <Input
                    id="space-desc"
                    placeholder="공간에 대한 설명"
                    value={newSpaceDesc}
                    onChange={(e) => setNewSpaceDesc(e.target.value)}
                  />
                </div>
                <Button onClick={handleCreateSpace} className="w-full">
                  추가
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* 공간 목록 */}
        <div className="flex flex-wrap gap-2">
          {spaces.map((space) => (
            <div key={space.spaceId} className="flex items-center gap-1">
              <button
                onClick={() => onSpaceSelect(space.spaceId)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  selectedSpaceId === space.spaceId
                    ? "bg-blue-500 text-white"
                    : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                }`}
              >
                {space.name}
              </button>
              <Dialog>
                <DialogTrigger asChild>
                  <button
                    onClick={() => {
                      setEditingSpaceId(space.spaceId);
                      setEditSpaceName(space.name);
                      setEditSpaceDesc(space.description || "");
                    }}
                    className="p-1 hover:bg-slate-200 rounded"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>공간 수정</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="edit-space-name">공간 이름</Label>
                      <Input
                        id="edit-space-name"
                        value={editSpaceName}
                        onChange={(e) => setEditSpaceName(e.target.value)}
                      />
                    </div>
                    <div>
                      <Label htmlFor="edit-space-desc">설명</Label>
                      <Input
                        id="edit-space-desc"
                        value={editSpaceDesc}
                        onChange={(e) => setEditSpaceDesc(e.target.value)}
                      />
                    </div>
                    <Button
                      onClick={() => handleUpdateSpace(space.spaceId)}
                      className="w-full"
                    >
                      수정
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
              <button
                onClick={() => onSpaceDelete(space.spaceId)}
                className="p-1 hover:bg-red-100 text-red-600 rounded"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* 가구 추가 */}
      {selectedSpace && (
        <div className="space-y-2 pt-4 border-t">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">
              가구 관리 ({furnitureList.length})
            </h3>
            <Dialog>
              <DialogTrigger asChild>
                <Button size="sm" variant="outline">
                  <Plus className="w-4 h-4 mr-1" />
                  가구 추가
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>새 가구 추가</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="furniture-name">가구 이름</Label>
                    <Input
                      id="furniture-name"
                      placeholder="예: TV 장식장, 앞 교구장"
                      value={newFurnitureName}
                      onChange={(e) => setNewFurnitureName(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="furniture-type">가구 종류</Label>
                    <select
                      id="furniture-type"
                      value={newFurnitureType}
                      onChange={(e) => setNewFurnitureType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                    >
                      <option value="drawer">서랍장</option>
                      <option value="wardrobe">옷장</option>
                      <option value="bookshelf">책장</option>
                      <option value="shelf">선반</option>
                      <option value="storage_box">수납함</option>
                      <option value="cabinet">캐비닛</option>
                      <option value="desk">책상</option>
                      <option value="locker">사물함</option>
                      <option value="other">기타</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="furniture-color">마커 색상</Label>
                    <div className="flex gap-2">
                      <input
                        id="furniture-color"
                        type="color"
                        value={newFurnitureColor}
                        onChange={(e) => setNewFurnitureColor(e.target.value)}
                        className="w-12 h-10 rounded cursor-pointer"
                      />
                      <div
                        className="flex-1 rounded"
                        style={{ backgroundColor: newFurnitureColor }}
                      />
                    </div>
                  </div>
                  <Button onClick={handleCreateFurniture} className="w-full">
                    추가
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {/* 가구 목록 */}
          <div className="bg-slate-50 rounded-md p-3 max-h-32 overflow-y-auto">
            {furnitureList.length > 0 ? (
              <ul className="space-y-1 text-sm">
                {furnitureList.map((furn) => (
                  <li
                    key={furn.furnitureId}
                    className="flex items-center gap-2 p-2 rounded hover:bg-slate-200"
                  >
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: furn.color }}
                    />
                    <span className="flex-1">{furn.name}</span>
                    <span className="text-xs text-slate-500">
                      {furn.type || "기타"}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">가구를 추가해주세요</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
