/**
 * Proposed wire DTOs copied from PR #27's mvp-api.md.
 * Keep these types and their mapper at the transport boundary until that PR is
 * accepted; UI components consume view models instead of depending on fields.
 */
export type Timestamp = string
export type Metric = 'power_kw' | 'energy_kwh'
export type Unit = 'kW' | 'kWh'

export interface ApiEnvelope<T> {
  data: T
  meta: {
    generated_at: Timestamp
    start?: Timestamp
    end?: Timestamp
    building_id?: string | null
    device_id?: string | null
    metric?: Metric | null
    next_cursor?: string | null
  }
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    request_id: string
  }
}

export interface BuildingSummaryDto {
  building_id: string
  name: string
  energy_kwh: number | null
  unit: 'kWh'
  start: Timestamp
  end: Timestamp
  included_interval_count: number
  coverage: 'complete' | 'partial' | 'none'
  coverage_ratio: number
  data_stale: boolean
}

export interface DeviceDto {
  device_id: string
  building_id: string
  name: string
  enabled: boolean
  status: 'online' | 'offline' | 'unknown' | 'disabled'
  last_seen: Timestamp | null
  latest_event_time: Timestamp | null
  data_stale: boolean
  period_seconds: number
}

export interface ReadingDto {
  message_id: string
  device_id: string
  building_id: string
  metric: Metric
  event_time: Timestamp
  received_at: Timestamp
  interval_start: Timestamp | null
  value: number
  unit: Unit
  is_late: boolean
  is_out_of_order: boolean
}

export interface AlertDto {
  alert_id: string
  message_id: string
  device_id: string
  building_id: string
  event_time: Timestamp
  detected_at: Timestamp
  metric: 'power_kw'
  value: number
  threshold: number
  unit: 'kW'
  description: string
}
