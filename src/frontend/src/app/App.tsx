import { useEffect, useState } from 'react'
import type { DashboardRepository, DataMode } from '../api/repository'
import { createDashboardRepository, getDataMode, getMockScenarioFromLocation } from '../api/repository'
import { AlertsPage } from '../features/alerts/AlertsPage'
import { DevicesPage } from '../features/devices/DevicesPage'
import { HistoryPage } from '../features/history/HistoryPage'
import { OverviewPage } from '../features/overview/OverviewPage'
import { AppLink, useRoute } from './navigation'

const scenarioLabels: Record<string, string> = {
  normal: 'Dữ liệu mẫu',
  empty: 'Rỗng thành công',
  'error-once': 'Lỗi một lần rồi thành công',
  'error-refresh': 'Tải mới lỗi, giữ dữ liệu cũ',
  delayed: 'Tải chậm',
  zero: 'Điện năng bằng 0',
  'null-energy': 'Chưa có điện năng',
}

export function App({ repository: suppliedRepository }: { repository?: DashboardRepository }) {
  const [repository, setRepository] = useState<DashboardRepository | null>(suppliedRepository ?? null)
  const route = useRoute()

  useEffect(() => {
    if (suppliedRepository) {
      setRepository(suppliedRepository)
      return
    }
    let active = true
    void createDashboardRepository().then((instance) => { if (active) setRepository(instance) })
    return () => { active = false }
  }, [suppliedRepository])

  if (!repository) return <main className="app-boot" role="status">Đang khởi tạo Dashboard…</main>

  const active = route.page === 'overview' ? 'overview' : route.page === 'devices' ? 'devices' : route.page
  const mode = getDataMode()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <AppLink to="/" className="brand-lockup"><span className="brand-symbol">C</span><span><strong>Campus</strong><small>ENERGY MONITOR</small></span></AppLink>
        <p className="nav-label">KHUÔN VIÊN</p>
        <nav aria-label="Điều hướng chính" className="main-nav">
          <AppLink to="/" className={active === 'overview' ? 'nav-link active' : 'nav-link'} aria-current={active === 'overview' ? 'page' : undefined}><span className="nav-icon">◫</span>Tổng quan</AppLink>
          <AppLink to="/devices" className={active === 'devices' ? 'nav-link active' : 'nav-link'} aria-current={active === 'devices' ? 'page' : undefined}><span className="nav-icon">▦</span>Thiết bị</AppLink>
          <AppLink to="/devices/A-01/history" className={active === 'history' ? 'nav-link active' : 'nav-link'} aria-current={active === 'history' ? 'page' : undefined}><span className="nav-icon">⌁</span>Lịch sử</AppLink>
          <AppLink to="/alerts" className={active === 'alerts' ? 'nav-link active' : 'nav-link'} aria-current={active === 'alerts' ? 'page' : undefined}><span className="nav-icon">◇</span>Cảnh báo</AppLink>
        </nav>
        <div className="sidebar-bottom"><span className="connection-dot" /><div><strong>{mode === 'mock' ? 'Chế độ minh họa' : 'Nguồn API'}</strong><small>{mode === 'mock' ? 'Không gửi dữ liệu tới Backend' : 'DTO/API đang theo đề xuất PR #27'}</small></div></div>
      </aside>

      <div className="main-column">
        <header className="topbar"><div className="breadcrumb"><span>APP-05</span><span aria-hidden="true">/</span><strong>Smart Campus Energy</strong></div><div className="topbar-actions"><span className="timezone-chip">◷ &nbsp; Asia/Ho_Chi_Minh</span>{mode === 'mock' && import.meta.env.DEV && <MockScenarioPicker />}</div></header>
        <main className="main-content">
          {route.page === 'overview' && <OverviewPage repository={repository} />}
          {route.page === 'devices' && <DevicesPage key={route.buildingId ?? 'all'} repository={repository} initialBuildingId={route.buildingId} />}
          {route.page === 'history' && <HistoryPage key={route.deviceId} repository={repository} deviceId={route.deviceId} />}
          {route.page === 'alerts' && <AlertsPage repository={repository} />}
        </main>
        <footer className="app-footer"><span>APP-05 · Smart Campus Energy Dashboard</span><span>Dữ liệu mô phỏng cho phát triển Frontend</span></footer>
      </div>
    </div>
  )
}

function MockScenarioPicker() {
  const value = getMockScenarioFromLocation() ?? import.meta.env.VITE_MOCK_SCENARIO ?? 'normal'
  function changeScenario(next: string) {
    const url = new URL(window.location.href)
    if (next === 'normal') url.searchParams.delete('demo')
    else url.searchParams.set('demo', next)
    window.location.assign(url)
  }
  return (
    <label className="scenario-picker">Tình huống <select aria-label="Tình huống dữ liệu minh họa" value={value} onChange={(event) => changeScenario(event.target.value)}>
      {Object.entries(scenarioLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}
    </select></label>
  )
}

export type { DataMode }
