import { Route, Switch } from 'wouter'
import Layout from './components/Layout'
import EnterpriseLayout from './components/EnterpriseLayout'
import Home from './pages/Home'
import EnterpriseHome from './pages/EnterpriseHome'
import FloorPlan from './pages/FloorPlan'
import Dashboard from './pages/Dashboard'
import { useTheme } from './contexts/ThemeContext'

export default function App() {
  const { theme } = useTheme()

  const CurrentLayout = theme === 'enterprise' ? EnterpriseLayout : Layout
  const CurrentHome = theme === 'enterprise' ? EnterpriseHome : Home

  return (
    <CurrentLayout>
      <Switch>
        <Route path="/" component={CurrentHome} />
        <Route path="/spaces/:spaceId/map" component={FloorPlan} />
        <Route path="/dashboard" component={Dashboard} />
        <Route>
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="text-center">
              <p className="text-6xl mb-4">🗺️</p>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">페이지를 찾을 수 없습니다</h2>
              <a href="/" className="text-violet-600 hover:underline">홈으로 돌아가기</a>
            </div>
          </div>
        </Route>
      </Switch>
    </CurrentLayout>
  )
}
