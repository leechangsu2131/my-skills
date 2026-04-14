import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import QualityDashboard from "@/components/QualityDashboard";
import { trpc } from "@/lib/trpc";
import { Link } from "wouter";
import { ArrowLeft } from "lucide-react";

export default function Dashboard() {
  const { isAuthenticated } = useAuth();
  const metricsQuery = trpc.metrics.getQuality.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <p className="text-slate-600">로그인이 필요합니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 헤더 */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              돌아가기
            </Button>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">데이터 품질 대시보드</h1>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6">
          <QualityDashboard
            metrics={metricsQuery.data || null}
            isLoading={metricsQuery.isLoading}
          />

          {/* 정보 카드 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              지표 설명
            </h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  필수 필드 완성도
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  모든 물건이 이름과 가구 정보를 가지고 있는 비율입니다. 높을수록 데이터 품질이 좋습니다.
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  가구 배정률
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  물건이 특정 가구에 배정된 비율입니다. 높을수록 물건 위치 추적이 정확합니다.
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  이름 중복률
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  같은 이름을 가진 물건이 없는 비율입니다. 높을수록 검색 결과가 명확합니다.
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  데이터 최신성
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  최근 30일 이내에 업데이트된 물건의 비율입니다. 높을수록 정보가 최신입니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
