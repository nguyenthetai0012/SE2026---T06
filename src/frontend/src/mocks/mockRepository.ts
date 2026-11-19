import { mapAlertPage, mapDevicePage, mapReadingPage, mapSummaryPage } from '../api/mapper'
import type { Alert, AlertsQuery, BuildingSummary, DevicesQuery, Device, Page, Reading, ReadingsQuery, TimeRange, MockScenario } from '../api/models'
import { RepositoryError, type DashboardRepository } from '../api/repository'
import type { DashboardFixture } from './fixtures'

export class MockDashboardRepository implements DashboardRepository {
  private readonly failedOnce = new Set<string>()
  private readonly requestCounts = new Map<string, number>()

  constructor(
    private readonly fixture: DashboardFixture,
    private readonly scenario: MockScenario = 'normal',
  ) {}

  getDefaultSummaryRange(): TimeRange {
    const item = this.fixture.summary.data[0]
    return { start: item.start, end: item.end }
  }

  getDefaultHistoryRange(): TimeRange {
    return { start: this.fixture.readings.meta.start ?? '', end: this.fixture.readings.meta.end ?? '' }
  }

  async getSummary(): Promise<Page<BuildingSummary>> {
    await this.beforeRequest('summary')
    if (this.scenario === 'empty') return mapSummaryPage({ ...this.fixture.summary, data: [] })
    if (this.scenario === 'zero') {
      return mapSummaryPage({ ...this.fixture.summary, data: this.fixture.summary.data.map((item) => ({ ...item, energy_kwh: 0, coverage: 'complete', coverage_ratio: 1 })) })
    }
    if (this.scenario === 'null-energy') {
      return mapSummaryPage({ ...this.fixture.summary, data: this.fixture.summary.data.map((item) => ({ ...item, energy_kwh: null, included_interval_count: 0, coverage: 'none', coverage_ratio: 0 })) })
    }
    return mapSummaryPage(this.fixture.summary)
  }

  async getDevices(query: DevicesQuery): Promise<Page<Device>> {
    await this.beforeRequest('devices')
    const data = this.scenario === 'empty'
      ? []
      : this.fixture.devices.data.filter((device) => !query.buildingId || device.building_id === query.buildingId)
    return mapDevicePage({ ...this.fixture.devices, data })
  }

  async getReadings(query: ReadingsQuery): Promise<Page<Reading>> {
    await this.beforeRequest('readings')
    const start = Date.parse(query.range.start)
    const end = Date.parse(query.range.end)
    const data = this.scenario === 'empty'
      ? []
      : this.fixture.readings.data.filter((reading) =>
          reading.device_id === query.deviceId && reading.metric === query.metric &&
          Date.parse(reading.event_time) >= start && Date.parse(reading.event_time) < end)
    return mapReadingPage({
      ...this.fixture.readings,
      data,
      meta: { ...this.fixture.readings.meta, device_id: query.deviceId, metric: query.metric, start: query.range.start, end: query.range.end },
    })
  }

  async getAlerts(query: AlertsQuery): Promise<Page<Alert>> {
    await this.beforeRequest('alerts')
    const data = this.scenario === 'empty'
      ? []
      : this.fixture.alerts.data.filter((alert) =>
          (!query.buildingId || alert.building_id === query.buildingId) &&
          (!query.deviceId || alert.device_id === query.deviceId))
    return mapAlertPage({ ...this.fixture.alerts, data })
  }

  private async beforeRequest(key: string): Promise<void> {
    const count = (this.requestCounts.get(key) ?? 0) + 1
    this.requestCounts.set(key, count)
    if (this.scenario === 'delayed') await pause(1400)
    if (this.scenario === 'error-refresh' && count > 1) {
      throw new RepositoryError('Không thể cập nhật dữ liệu minh họa.', 'DEPENDENCY_UNAVAILABLE', `mock-${key}-refresh`, 503)
    }
    if (this.scenario === 'error-once' && !this.failedOnce.has(key)) {
      this.failedOnce.add(key)
      throw new RepositoryError('Không thể tải dữ liệu minh họa. Hãy thử lại.', 'DEPENDENCY_UNAVAILABLE', `mock-${key}-01`, 503)
    }
    if (this.scenario !== 'delayed') await pause(180)
  }
}

function pause(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
