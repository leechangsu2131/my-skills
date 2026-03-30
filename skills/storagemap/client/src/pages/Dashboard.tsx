import QualityDashboard from '@/components/QualityDashboard'
import { useQualityMetrics, useAllItems } from '@/hooks/useStorageMap'
import { BarChart3, Package, MapPin, Archive } from 'lucide-react'

export default function Dashboard() {
  const metrics = useQualityMetrics()
  const { data: allData } = useAllItems()

  const stats = [
    { label: '전체 물건', value: allData?.items?.length || 0, icon: Package, color: 'from-violet-500 to-indigo-500' },
    { label: '전체 가구', value: allData?.furniture?.length || 0, icon: Archive, color: 'from-blue-500 to-cyan-500' },
    { label: '전체 공간', value: allData?.spaces?.length || 0, icon: MapPin, color: 'from-emerald-500 to-teal-500' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-6 h-6 text-violet-600" />
        <h1 className="text-2xl font-bold text-slate-800">데이터 품질 대시보드</h1>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="relative overflow-hidden bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
            <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${stat.color} opacity-10 rounded-full -translate-y-6 translate-x-6`} />
            <div className="relative">
              <div className="flex items-center gap-2 mb-2">
                <stat.icon className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-500">{stat.label}</span>
              </div>
              <p className="text-3xl font-extrabold text-slate-800">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quality metrics */}
      <QualityDashboard metrics={metrics} />
    </div>
  )
}
