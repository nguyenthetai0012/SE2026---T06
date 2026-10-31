import { mapAlertPage, mapDevicePage, mapReadingPage, mapSummaryPage } from './mapper'
import type { ApiEnvelope, ApiErrorEnvelope, AlertDto, BuildingSummaryDto, DeviceDto, ReadingDto } from './dto'
import type { Alert, AlertsQuery, BuildingSummary, Device, DevicesQuery, Page, Reading, ReadingsQuery, SummaryQuery, TimeRange } from './models'
import { RepositoryError, type DashboardRepository } from './repository'

/** Proposed PR #27 endpoints, isolated here until the baseline/API contract is accepted. */
export class HttpDashboardRepository implements DashboardRepository {
  constructor(
    private readonly baseUrl: string,
    private readonly fetcher: typeof fetch = fetch,
  ) {}

  getSummary(query: SummaryQuery): Promise<Page<BuildingSummary>> {
    return this.get<BuildingSummaryDto[]>('/buildings/summary', { start: query.range.start, end: query.range.end }).then(mapSummaryPage)
  }

  getDevices(query: DevicesQuery): Promise<Page<Device>> {
    return this.get<DeviceDto[]>('/devices', { building_id: query.buildingId }).then(mapDevicePage)
  }

  getReadings(query: ReadingsQuery): Promise<Page<Reading>> {
    return this.get<ReadingDto[]>(`/devices/${encodeURIComponent(query.deviceId)}/readings`, {
      metric: query.metric,
      start: query.range.start,
      end: query.range.end,
      limit: query.limit,
      cursor: query.cursor,
    }).then(mapReadingPage)
  }

  getAlerts(query: AlertsQuery): Promise<Page<Alert>> {
    return this.get<AlertDto[]>('/alerts', {
      building_id: query.buildingId,
      device_id: query.deviceId,
      limit: query.limit,
      cursor: query.cursor,
    }).then(mapAlertPage)
  }

  getDefaultSummaryRange(): TimeRange {
    return lastTwentyFourHours()
  }

  getDefaultHistoryRange(): TimeRange {
    return lastTwentyFourHours()
  }

  private async get<T>(path: string, values: Record<string, string | number | null | undefined>): Promise<ApiEnvelope<T>> {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(values)) {
      if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
    }
    const response = await this.fetcher(`${this.baseUrl}${path}?${query.toString()}`, {
      headers: { Accept: 'application/json' },
    })
    const payload: unknown = await response.json().catch(() => null)
    if (!response.ok) {
      const error = isApiError(payload) ? payload.error : undefined
      throw new RepositoryError(
        error?.message ?? 'Không thể tải dữ liệu. Vui lòng thử lại.',
        error?.code ?? 'HTTP_ERROR',
        error?.request_id ?? 'unknown',
        response.status,
      )
    }
    if (!isApiEnvelope<T>(payload)) {
      throw new RepositoryError('Phản hồi API không đúng cấu trúc dự kiến.', 'INVALID_RESPONSE', 'unknown', response.status)
    }
    return payload
  }
}

function lastTwentyFourHours(): TimeRange {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

function isApiError(value: unknown): value is ApiErrorEnvelope {
  return typeof value === 'object' && value !== null && 'error' in value
}

function isApiEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  return typeof value === 'object' && value !== null && 'data' in value && 'meta' in value
}

// Keep imports explicit so type changes in the proposal are caught in this boundary.
export type ProposedApiDto = AlertDto | BuildingSummaryDto | DeviceDto | ReadingDto
