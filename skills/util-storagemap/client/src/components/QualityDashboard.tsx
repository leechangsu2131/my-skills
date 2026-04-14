import type { QualityMetrics } from '../types'
import { CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react'

interface QualityDashboardProps {
  metrics: QualityMetrics | null
}

function getStatus(value: number, threshold: number) {
  if (value >= threshold) return { icon: CheckCircle, label: '양호', color: 'text-emerald-500', bg: 'bg-emerald-500' }
  if (value >= threshold - 20) return { icon: AlertTriangle, label: '주의', color: 'text-amber-500', bg: 'bg-amber-500' }
  return { icon: AlertCircle, label: '위험', color: 'text-red-500', bg: 'bg-red-500' }
}

function MetricCard({ title, value, description, threshold = 70 }: {
  title: string
  value: number
  description: string
  threshold?: number
}) {
  const status = getStatus(value, threshold)
  const Icon = status.icon

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">{title}</span>
          <Icon className={`w-4 h-4 ${status.color}`} />
        </div>
        <span className="text-lg font-extrabold text-slate-900">{Math.round(value)}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${status.bg}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>

      <div className="flex items-center justify-between mt-2">
        <p className="text-xs text-slate-500">{description}</p>
        <span className={`text-xs font-semibold ${status.color}`}>{status.label}</span>
      </div>
    </div>
  )
}

export default function QualityDashboard({ metrics }: QualityDashboardProps) {
  if (!metrics) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 p-8 text-center shadow-sm">
        <p className="text-slate-400">물건을 등록하면 데이터 품질 지표가 표시됩니다</p>
      </div>
    )
  }

  const overallScore = Math.round(
    (metrics.requiredFieldsCompleteness +
      metrics.furnitureAssignmentRate +
      (100 - metrics.nameDuplicateRate) +
      metrics.dataFreshnessRate) / 4,
  )

  return (
    <div className="space-y-4">
      {/* Overall score */}
      <div className="bg-gradient-to-br from-violet-600 to-indigo-600 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-violet-200">전체 품질 점수</p>
            <p className="text-xs text-violet-300 mt-1">
              {metrics.totalItems}개 물건 · {metrics.totalFurniture}개 가구
            </p>
          </div>
          <div className="text-right">
            <p className="text-5xl font-extrabold">{overallScore}</p>
            <p className="text-xs text-violet-300">/ 100</p>
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
          title="이름 고유성"
          value={100 - metrics.nameDuplicateRate}
          description="중복되지 않은 물건 이름 비율"
          threshold={80}
        />
        <MetricCard
          title="데이터 최신성"
          value={metrics.dataFreshnessRate}
          description="30일 이내 업데이트된 비율"
          threshold={70}
        />
      </div>

      {/* Recommendations */}
      {(metrics.requiredFieldsCompleteness < 90 ||
        metrics.furnitureAssignmentRate < 90 ||
        metrics.nameDuplicateRate > 20 ||
        metrics.dataFreshnessRate < 70) && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">💡 개선 권고</p>
          <ul className="text-xs text-amber-700 space-y-1">
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
      )}
    </div>
  )
}
