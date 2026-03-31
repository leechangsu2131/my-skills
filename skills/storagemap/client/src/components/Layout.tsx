import { Link, useLocation } from 'wouter'
import { Search, BarChart3, MapPin, RefreshCw, Monitor } from 'lucide-react'
import { useAuthStatus, useReloadData, useSpaces } from '@/hooks/useStorageMap'
import { useTheme } from '@/contexts/ThemeContext'
import type { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation()
  const { data: auth } = useAuthStatus()
  const { data: spaces } = useSpaces()
  const reloadMutation = useReloadData()
  const { setTheme } = useTheme()

  const navItems = [
    { href: '/', label: '검색', icon: Search },
    { href: '/dashboard', label: '대시보드', icon: BarChart3 },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-lg border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/">
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent cursor-pointer">
                STORAGEMAP
              </span>
            </Link>

            <nav className="hidden sm:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = location === item.href
                return (
                  <Link key={item.href} href={item.href}>
                    <span
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                        isActive
                          ? 'bg-violet-100 text-violet-700'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'
                      }`}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </span>
                  </Link>
                )
              })}

              {/* Space links → FloorPlan */}
              {spaces?.map((s) => (
                <Link key={s.space_id} href={`/spaces/${s.space_id}/map`}>
                  <span
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                      location === `/spaces/${s.space_id}/map`
                        ? 'bg-violet-100 text-violet-700'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'
                    }`}
                  >
                    <MapPin className="w-4 h-4" />
                    {s.name}
                  </span>
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setTheme('enterprise')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-white rounded-lg text-sm font-semibold hover:bg-slate-700 transition-all shadow-sm"
              title="엔터프라이즈 모드로 전환"
            >
              <Monitor className="w-4 h-4" />
              <span className="hidden sm:inline">엔터프라이즈 테마</span>
            </button>
            <div className="w-px h-6 bg-slate-200 mx-1"></div>

            <button
              onClick={() => reloadMutation.mutate()}
              disabled={reloadMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-all disabled:opacity-50"
              title="Google Sheets 새로고침"
            >
              <RefreshCw className={`w-4 h-4 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">새로고침</span>
            </button>

            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  auth?.authenticated ? 'bg-emerald-400' : 'bg-slate-300'
                }`}
              />
              <span className="text-xs text-slate-500">
                {auth?.authenticated ? '인증됨' : '미인증'}
              </span>
              {!auth?.authenticated && (
                <a
                  href="/auth/google"
                  className="ml-1 text-xs font-semibold text-violet-600 hover:underline"
                >
                  로그인
                </a>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className={`${location.includes('/map') ? 'w-full' : 'max-w-7xl mx-auto'} px-4 sm:px-6 py-6`}>
        {children}
      </main>
    </div>
  )
}
