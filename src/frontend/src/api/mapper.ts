import type {
  AlertDto,
  ApiEnvelope,
  BuildingSummaryDto,
  DeviceDto,
  ReadingDto,
} from './dto'
import type { Alert, BuildingSummary, Device, Page, Reading } from './models'

function mapPageMeta(meta: ApiEnvelope<unknown>['meta']): Page<never>['meta'] {
  return {
    generatedAt: meta.generated_at,
    start: meta.start,
    end: meta.end,
    buildingId: meta.building_id,
    deviceId: meta.device_id,
    metric: meta.metric,
    nextCursor: meta.next_cursor ?? null,
  }
}

export function mapSummaryPage(envelope: ApiEnvelope<BuildingSummaryDto[]>): Page<BuildingSummary> {
  return {
    items: envelope.data.map((dto) => ({
      buildingId: dto.building_id,
      name: dto.name,
      energyKwh: dto.energy_kwh,
      unit: dto.unit,
      range: { start: dto.start, end: dto.end },
      includedIntervalCount: dto.included_interval_count,
      coverage: dto.coverage,
      coverageRatio: dto.coverage_ratio,
      isDataStale: dto.data_stale,
    })),
    meta: mapPageMeta(envelope.meta),
  }
}

export function mapDevicePage(envelope: ApiEnvelope<DeviceDto[]>): Page<Device> {
  return {
    items: envelope.data.map((dto) => ({
      deviceId: dto.device_id,
      buildingId: dto.building_id,
      name: dto.name,
      enabled: dto.enabled,
      status: dto.status,
      lastSeen: dto.last_seen,
      latestEventTime: dto.latest_event_time,
      isDataStale: dto.data_stale,
      periodSeconds: dto.period_seconds,
    })),
    meta: mapPageMeta(envelope.meta),
  }
}

export function mapReadingPage(envelope: ApiEnvelope<ReadingDto[]>): Page<Reading> {
  return {
    items: envelope.data.map((dto) => ({
      messageId: dto.message_id,
      deviceId: dto.device_id,
      buildingId: dto.building_id,
      metric: dto.metric,
      eventTime: dto.event_time,
      receivedAt: dto.received_at,
      intervalStart: dto.interval_start,
      value: dto.value,
      unit: dto.unit,
      isLate: dto.is_late,
      isOutOfOrder: dto.is_out_of_order,
    })),
    meta: mapPageMeta(envelope.meta),
  }
}

export function mapAlertPage(envelope: ApiEnvelope<AlertDto[]>): Page<Alert> {
  return {
    items: envelope.data.map((dto) => ({
      alertId: dto.alert_id,
      messageId: dto.message_id,
      deviceId: dto.device_id,
      buildingId: dto.building_id,
      eventTime: dto.event_time,
      detectedAt: dto.detected_at,
      metric: dto.metric,
      value: dto.value,
      threshold: dto.threshold,
      unit: dto.unit,
      description: dto.description,
    })),
    meta: mapPageMeta(envelope.meta),
  }
}
