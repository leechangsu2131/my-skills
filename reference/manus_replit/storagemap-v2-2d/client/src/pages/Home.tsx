import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import Canvas2D from "@/components/Canvas2D";
import SpaceManager from "@/components/SpaceManager";
import ItemManager from "@/components/ItemManager";
import HistoryViewer from "@/components/HistoryViewer";
import { trpc } from "@/lib/trpc";
import { getLoginUrl } from "@/const";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { BarChart3 } from "lucide-react";
import { Link } from "wouter";
import type { Space, Furniture, Zone, Item } from "../../../drizzle/schema";

export default function Home() {
  const { user, isAuthenticated } = useAuth();
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
  const [selectedFurnitureId, setSelectedFurnitureId] = useState<string | null>(null);
  const [highlightedFurnitureId, setHighlightedFurnitureId] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<Item[]>([]);

  // 데이터 페칭
  const spacesQuery = trpc.space.list.useQuery(undefined, { enabled: isAuthenticated });
  const furnitureQuery = trpc.furniture.listBySpace.useQuery(
    { spaceId: selectedSpaceId || "" },
    { enabled: isAuthenticated && !!selectedSpaceId }
  );
  const itemsQuery = trpc.item.list.useQuery(undefined, { enabled: isAuthenticated });
  const zonesQuery = trpc.zone.listByFurniture.useQuery(
    { furnitureId: selectedFurnitureId || "" },
    { enabled: isAuthenticated && !!selectedFurnitureId }
  );

  // 뮤테이션
  const createSpaceMutation = trpc.space.create.useMutation({
    onSuccess: () => {
      spacesQuery.refetch();
      toast.success("공간이 추가되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const updateSpaceMutation = trpc.space.update.useMutation({
    onSuccess: () => {
      spacesQuery.refetch();
      toast.success("공간이 수정되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const deleteSpaceMutation = trpc.space.delete.useMutation({
    onSuccess: () => {
      spacesQuery.refetch();
      setSelectedSpaceId(null);
      toast.success("공간이 삭제되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const createFurnitureMutation = trpc.furniture.create.useMutation({
    onSuccess: () => {
      furnitureQuery.refetch();
      toast.success("가구가 추가되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const updateFurnitureMutation = trpc.furniture.update.useMutation({
    onSuccess: () => {
      furnitureQuery.refetch();
    },
    onError: (error) => toast.error(error.message),
  });

  const createItemMutation = trpc.item.create.useMutation({
    onSuccess: () => {
      itemsQuery.refetch();
      toast.success("물건이 추가되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const updateItemMutation = trpc.item.update.useMutation({
    onSuccess: () => {
      itemsQuery.refetch();
      toast.success("물건이 수정되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const deleteItemMutation = trpc.item.delete.useMutation({
    onSuccess: () => {
      itemsQuery.refetch();
      toast.success("물건이 삭제되었습니다");
    },
    onError: (error) => toast.error(error.message),
  });

  const [searchQuery, setSearchQuery] = useState("");
  const searchQuery_Query = trpc.item.search.useQuery(
    { query: searchQuery },
    { enabled: isAuthenticated && searchQuery.length > 0 }
  );

  useEffect(() => {
    if (searchQuery_Query.data) {
      setSearchResults(searchQuery_Query.data);
      if (searchQuery_Query.data.length > 0) {
        setHighlightedFurnitureId(searchQuery_Query.data[0].furnitureId);
      }
    }
  }, [searchQuery_Query.data]);

  // 초기 공간 선택
  useEffect(() => {
    if (spacesQuery.data && spacesQuery.data.length > 0 && !selectedSpaceId) {
      setSelectedSpaceId(spacesQuery.data[0].spaceId);
    }
  }, [spacesQuery.data, selectedSpaceId]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-slate-900">StorageMap v2.1</h1>
          <p className="text-lg text-slate-600">물건 위치 관리 시스템</p>
          <p className="text-slate-500 max-w-md">
            2D 평면도를 활용하여 집안 물건의 위치를 체계적으로 관리하고 빠르게 찾을 수 있습니다.
          </p>
          <Button size="lg" asChild>
            <a href={getLoginUrl()}>로그인</a>
          </Button>
        </div>
      </div>
    );
  }

  const spaces = spacesQuery.data || [];
  const furniture = furnitureQuery.data || [];
  const items = itemsQuery.data || [];
  const zones = zonesQuery.data || [];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 헤더 */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">StorageMap v2.1</h1>
            <p className="text-sm text-slate-600">안녕하세요, {user?.name}님</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">
              공간: {spaces.length} | 가구: {furniture.length} | 물건: {items.length}
            </span>
            <Link href="/dashboard">
              <Button size="sm" variant="outline">
                <BarChart3 className="w-4 h-4 mr-2" />
                대시보드
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 왼쪽 사이드바 - 공간/가구/물건 관리 */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <SpaceManager
                spaces={spaces}
                selectedSpaceId={selectedSpaceId}
                onSpaceSelect={setSelectedSpaceId}
                onSpaceCreate={(name, desc) =>
                  createSpaceMutation.mutate({ name, description: desc })
                }
                onSpaceUpdate={(spaceId, name, desc) =>
                  updateSpaceMutation.mutate({ spaceId, name, description: desc })
                }
                onSpaceDelete={(spaceId) => deleteSpaceMutation.mutate({ spaceId })}
                onFurnitureCreate={(spaceId, name, type, color) =>
                  createFurnitureMutation.mutate({ spaceId, name, type, color })
                }
                furnitureList={furniture}
              />
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <ItemManager
                items={items}
                furnitureList={furniture}
                zoneList={zones}
                selectedFurnitureId={selectedFurnitureId}
                onItemCreate={(item) => {
                  createItemMutation.mutate(item as any);
                }}
                onItemUpdate={(itemId, updates) => {
                  updateItemMutation.mutate({ itemId, ...(updates as any) });
                }}
                onItemDelete={(itemId) => deleteItemMutation.mutate({ itemId })}
                onSearch={(query) => setSearchQuery(query)}
                searchResults={searchResults}
              />
            </div>
          </div>

          {/* 오른쪽 메인 영역 - 2D 평면도 */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                {selectedSpaceId
                  ? spaces.find((s) => s.spaceId === selectedSpaceId)?.name
                  : "공간을 선택해주세요"}
              </h2>
              <Canvas2D
                furnitureList={furniture}
                selectedFurnitureId={selectedFurnitureId}
                onFurnitureSelect={setSelectedFurnitureId}
                onFurnitureMove={(furnitureId, posX, posY) => {
                  updateFurnitureMutation.mutate({ furnitureId, posX, posY });
                }}
                onFurnitureResize={(furnitureId, width, height) => {
                  updateFurnitureMutation.mutate({ furnitureId, width, height });
                }}
                highlightedFurnitureId={highlightedFurnitureId}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
