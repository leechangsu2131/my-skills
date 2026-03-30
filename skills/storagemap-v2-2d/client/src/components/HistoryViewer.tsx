import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, Calendar } from "lucide-react";
import type { History, Furniture, Zone } from "../../../drizzle/schema";

interface HistoryViewerProps {
  histories: History[];
  furnitureList: Furniture[];
  zoneList: Zone[];
}

export default function HistoryViewer({
  histories,
  furnitureList,
  zoneList,
}: HistoryViewerProps) {
  const getFurnitureName = (furnitureId: string | null) => {
    if (!furnitureId) return "알 수 없음";
    return furnitureList.find((f) => f.furnitureId === furnitureId)?.name || "알 수 없음";
  };

  const getZoneName = (zoneId: string | null) => {
    if (!zoneId) return "기본";
    return zoneList.find((z) => z.zoneId === zoneId)?.name || "알 수 없음";
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (histories.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">이동 이력</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">이동 이력이 없습니다</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">이동 이력 ({histories.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {histories.map((hist, idx) => (
            <div
              key={hist.historyId}
              className="flex items-center gap-2 p-3 bg-slate-50 rounded-md border border-slate-200 hover:bg-slate-100 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-900">
                    {getFurnitureName(hist.fromFurnitureId)}
                  </span>
                  <span className="text-xs text-slate-500">
                    ({getZoneName(hist.fromZoneId || null)})
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold text-slate-900">
                    {getFurnitureName(hist.toFurnitureId)}
                  </span>
                  <span className="text-xs text-slate-500">
                    ({getZoneName(hist.toZoneId || null)})
                  </span>
                </div>
                <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
                  <Calendar className="w-3 h-3" />
                  {formatDate(hist.movedAt)}
                </div>
              </div>
              <div className="text-xs text-slate-400 whitespace-nowrap">
                #{idx + 1}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
