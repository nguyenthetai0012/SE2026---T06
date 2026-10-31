import type { Metric, Unit } from './dto'

export interface TimeRange {
  start: string
  end: string
}

export interface PageMeta {
  generatedAt: string
  start?: string
  end?: string
  buildingId?: string | null
  deviceId?: string | null
  metric?: Metric | null
  nextCursor: string | null
}

export interface Page<T> {
  items: T[]
  meta: PageMeta
}

export interface BuildingSummary {
  buildingId: string
  name: string
  energyKwh: number | null
  unit: 'kWh'
  range: TimeRange
  includedIntervalCount: number
  coverage: 'complete' | 'partial' | 'none'
  coverageRatio: number
  isDataStale: boolean
}

export interface Device {
  deviceId: string
  buildingId: string
  name: string
  enabled: boolean
  status: 'online' | 'offline' | 'unknown' | 'disabled'
  lastSeen: string | null
  latestEventTime: string | null
  isDataStale: boolean
  periodSeconds: number
}

export interface Reading {
  messageId: string
  deviceId: string
  buildingId: string
  metric: Metric
  eventTime: string
  receivedAt: string
  intervalStart: string | null
  value: number
  unit: Unit
  isLate: boolean
  isOutOfOrder: boolean
}

export interface Alert {
  alertId: string
  messageId: string
  deviceId: string
  buildingId: string
  eventTime: string
  detectedAt: string
  metric: 'power_kw'
  value: number
  threshold: number
  unit: 'kW'
  description: string
}

export interface SummaryQuery {
  range: TimeRange
}

export interface DevicesQuery {
  buildingId?: string
}

export interface ReadingsQuery {
  deviceId: string
  metric: Metric
  range: TimeRange
  cursor?: string | null
  limit?: number
}

export interface AlertsQuery {
  buildingId?: string
  deviceId?: string
  cursor?: string | null
  limit?: number
}

export type MockScenario = 'normal' | 'empty' | 'error-once' | 'error-refresh' | 'delayed' | 'zero' | 'null-energy'
