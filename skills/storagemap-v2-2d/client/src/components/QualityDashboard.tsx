import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";

interface QualityMetrics {
  requiredFieldsCompleteness: number;
  furnitureAssignmentRate: number;
  nameDuplicateRate: number;
  dataFreshnessRate: number;
}

interface QualityDashboardProps {
  metrics: QualityMetrics | null;
  isLoading?: boolean;
}

export default function QualityDashboard({
  metrics,
  isLoading = false,
}: QualityDashboardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">데이터 품질 대시보드</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">로딩 중...</p>
        </CardContent>
      </Card>
    );
  }

  if (!metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">데이터 품질 대시보드</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">데이터가 없습니다</p>
        </CardContent>
      </Card>
    );
  }

  const getStatusIcon = (value: number, threshold: number = 70) => {
    if (value >= threshold) {
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    } else if (value >= threshold - 20) {
      return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    } else {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getStatusText = (value: number, threshold: number = 70) => {
    if (value >= threshold) {
      return "양호";
    } else if (value >= threshold - 20) {
      return "주의";
    } else {
      return "위험";
    }
  };

  const MetricCard = ({
    title,
    value,
    description,
    threshold = 70,
  }: {
    title: string;
    value: number;
    description: string;
    threshold?: number;
  }) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900">{title}</span>
          {getStatusIcon(value, threshold)}
        </div>
        <span className="text-sm font-bold text-slate-900">{Math.round(value)}%</span>
      </div>
      <Progress value={Math.min(value, 100)} className="h-2" />
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-600">{description}</p>
        <span className="text-xs font-semibold text-slate-500">
          {getStatusText(value, threshold)}
        </span>
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">데이터 품질 대시보드</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <MetricCard
            title="필수 필드 완성도"
            value={metrics.requiredFieldsCompleteness}
            description="이름과 가구 정보 입력 비율"
            threshold={90}
          />
          <MetricCard
            title="가구 배정률"
            value={metrics.furnitureAssignmentRate}
            description="가구에 배정된 물건 비율"
            threshold={90}
          />
          <MetricCard
            title="이름 중복률"
            value={100 - metrics.nameDuplicateRate}
            description="중복되지 않은 물건 이름 비율"
            threshold={80}
          />
          <MetricCard
            title="데이터 최신성"
            value={metrics.dataFreshnessRate}
            description="30일 이내 업데이트된 물건 비율"
            threshold={70}
          />

          {/* 전체 품질 점수 */}
          <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">전체 품질 점수</p>
                <p className="text-xs text-slate-600 mt-1">
                  모든 지표의 평균값입니다
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-blue-600">
                  {Math.round(
                    (metrics.requiredFieldsCompleteness +
                      metrics.furnitureAssignmentRate +
                      (100 - metrics.nameDuplicateRate) +
                      metrics.dataFreshnessRate) /
                      4
                  )}
                </p>
                <p className="text-xs text-slate-600">/ 100</p>
              </div>
            </div>
          </div>

          {/* 개선 권고사항 */}
          <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-xs font-semibold text-amber-900 mb-2">개선 권고</p>
            <ul className="text-xs text-amber-800 space-y-1">
              {metrics.requiredFieldsCompleteness < 90 && (
                <li>• 필수 필드 완성도를 높이기 위해 물건 정보를 더 입력해주세요</li>
              )}
              {metrics.furnitureAssignmentRate < 90 && (
                <li>• 모든 물건을 가구에 배정하여 위치 추적을 개선해주세요</li>
              )}
              {metrics.nameDuplicateRate > 20 && (
                <li>• 중복된 물건 이름을 정리하여 검색 정확도를 높여주세요</li>
              )}
              {metrics.dataFreshnessRate < 70 && (
                <li>• 오래된 데이터를 업데이트하여 정보 신뢰도를 높여주세요</li>
              )}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
