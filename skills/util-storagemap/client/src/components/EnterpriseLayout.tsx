import { Link, useLocation } from 'wouter'
import { Search, BarChart3, MapPin, RefreshCw, LayoutDashboard, History, Settings, MonitorOff, User } from 'lucide-react'
import { useAuthStatus, useReloadData, useSpaces } from '@/hooks/useStorageMap'
import { useTheme } from '@/contexts/ThemeContext'
import type { ReactNode } from 'react'

export default function EnterpriseLayout({ children }: { children: ReactNode }) {
  const [location] = useLocation()
  const { data: auth } = useAuthStatus()
  const reloadMutation = useReloadData()
  const { setTheme } = useTheme()

  const navItems = [
    { href: '/', label: 'Search', icon: Search },
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ]

  return (
    <div className="flex h-screen overflow-hidden bg-[#f7f9fb] text-slate-800 font-sans">
      {/* SideNavBar Shared Component */}
      <aside className="hidden md:flex flex-col h-full py-6 px-4 gap-2 w-64 bg-[#f2f4f6] border-r border-slate-200/60 shadow-none font-medium text-sm flex-shrink-0">
        <div className="mb-8 px-2 flex flex-col gap-1">
          <h1 className="text-lg font-bold text-[#1B365D] uppercase tracking-widest font-sans">STORAGEMAP V3</h1>
          <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold opacity-70">Management Console</p>
        </div>

        <nav className="flex flex-col gap-2">
          {navItems.map((item) => {
            const isActive = location === item.href
            return (
              <Link key={item.href} href={item.href}>
                <span
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer ${
                    isActive
                      ? 'bg-white text-[#1B365D] shadow-sm font-semibold'
                      : 'text-slate-500 hover:text-[#1B365D] hover:bg-white/50'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </span>
              </Link>
            )
          })}
        </nav>

        {/* User Info / Context Area */}
        <div className="mt-auto p-4 bg-white/70 rounded-2xl border border-slate-200/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-900 flex items-center justify-center text-white shadow-sm">
              <User className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-blue-900">{auth?.authenticated ? 'System Admin' : 'Guest'}</p>
              <p className="text-[10px] text-slate-500">{auth?.authenticated ? 'Zone Supervisor' : 'Read Only'}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* TopNavBar Shared Component */}
        <header className="flex justify-between items-center w-full px-8 py-4 bg-white/50 backdrop-blur-md border-b border-slate-200/40 text-[#1B365D] tracking-tight shrink-0">
          <div className="flex items-center gap-4 flex-1">
            <div className="text-xs font-bold uppercase tracking-tighter text-slate-400">Global Search Engine</div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => reloadMutation.mutate()}
              disabled={reloadMutation.isPending}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold hover:bg-slate-100 transition-colors ${reloadMutation.isPending ? 'opacity-50' : ''}`}
              title="Sync Data"
            >
              <RefreshCw className={`w-4 h-4 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Sync</span>
            </button>

            <button
              onClick={() => setTheme('default')}
              className="flex items-center gap-2 px-4 py-1.5 bg-violet-100 text-violet-700 hover:bg-violet-200 rounded-lg text-sm font-semibold transition-colors"
              title="Return to Default Theme"
            >
              <MonitorOff className="w-4 h-4" />
              <span className="hidden sm:inline">기존 테마 복귀</span>
            </button>
            
            {!auth?.authenticated && (
                <a href="/auth/google" className="ml-1 text-xs font-semibold text-blue-600 hover:underline bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100">
                  Authenticate Google
                </a>
            )}
          </div>
        </header>

        {/* Main Display Area */}
        <main className="flex-1 overflow-hidden flex flex-col bg-[#f7f9fb]">
          {children}
        </main>
      </div>
    </div>
  )
}
