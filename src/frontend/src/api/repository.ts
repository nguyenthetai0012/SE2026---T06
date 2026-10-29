import type { Alert, AlertsQuery, BuildingSummary, Device, DevicesQuery, Page, Reading, ReadingsQuery, SummaryQuery, TimeRange } from './models'

export interface DashboardRepository {
  getSummary(query: SummaryQuery): Promise<Page<BuildingSummary>>
  getDevices(query: DevicesQuery): Promise<Page<Device>>
  getReadings(query: ReadingsQuery): Promise<Page<Reading>>
  getAlerts(query: AlertsQuery): Promise<Page<Alert>>
  getDefaultSummaryRange(): TimeRange
  getDefaultHistoryRange(): TimeRange
}

export class RepositoryError extends Error {
  constructor(
    message: string,
    readonly code = 'INTERNAL_ERROR',
    readonly requestId = 'unknown',
    readonly status?: number,
  ) {
    super(message)
    this.name = 'RepositoryError'
  }
}

export type DataMode = 'mock' | 'api'

export function getDataMode(): DataMode {
  return import.meta.env.VITE_DATA_MODE === 'api' ? 'api' : 'mock'
}

export function getMockScenarioFromLocation(): string | null {
  return new URLSearchParams(window.location.search).get('demo')
}

export async function createDashboardRepository(): Promise<DashboardRepository> {
  if (getDataMode() === 'api') {
    const { HttpDashboardRepository } = await import('./httpRepository')
    return new HttpDashboardRepository(import.meta.env.VITE_API_BASE_URL ?? '/api/v1')
  }
  const [{ MockDashboardRepository }, { dashboardFixture }] = await Promise.all([
    import('../mocks/mockRepository'),
    import('../mocks/fixtures'),
  ])
  const queryScenario = getMockScenarioFromLocation()
  const envScenario = import.meta.env.VITE_MOCK_SCENARIO
  return new MockDashboardRepository(dashboardFixture, (queryScenario ?? envScenario ?? 'normal') as import('./models').MockScenario)
}
