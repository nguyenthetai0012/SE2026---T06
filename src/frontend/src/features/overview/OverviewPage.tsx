import { useCallback, useState } from 'react'
import type { DashboardRepository } from '../../api/repository'
import type { TimeRange } from '../../api/models'
import { formatDateTime, formatNumber } from '../../api/format'
import { AppLink } from '../../app/navigation'
import { PageTitle, QueryPanel } from '../../components/QueryPanel'
import { useDashboardQuery } from '../../components/useDashboardQuery'

export function OverviewPage({ repository }: { repository: DashboardRepository }) {
  const [range] = useState(() => repository.getDefaultSummaryRange())
  const load = useCallback(() => repository.getSummary({ range }), [repository, range])
  const query = useDashboardQuery(`summary:${range.start}:${range.end}`, load)

  return (
    <section aria-labelledby="overview-title">
      <PageTitle id="overview-title" eyebrow="TỔNG QUAN KHUÔN VIÊN" title="Năng lượng theo tòa nhà" description="Số liệu và khoảng thời gian do nguồn dữ liệu trả về; giao diện không tự tính tổng." />
      <div className="summary-range-note">
        <span className="section-icon">◷</span>
        <div><strong>Khoảng dữ liệu</strong><span>{formatDateTime(range.start)} — {formatDateTime(range.end)} · giờ Việt Nam</span></div>
      </div>
      <QueryPanel state={query} retry={query.retry} isEmpty={(page) => page.items.length === 0} emptyText="Không có tổng quan trong khoảng thời gian này.">
        {(page) => (
          <div className="summary-grid">
            {page.items.map((building) => (
              <article className="summary-card" key={building.buildingId} data-testid={`summary-${building.buildingId}`}>
                <div className="card-topline"><span className="building-mark">{building.buildingId.slice(-1)}</span><span className="muted-label">{building.buildingId}</span><span className={`freshness ${building.isDataStale ? 'is-stale' : 'is-fresh'}`}>{building.isDataStale ? 'Dữ liệu cũ' : 'Đã cập nhật'}</span></div>
                <h2>{building.name}</h2>
                <div className="energy-value">
                  <strong>{building.energyKwh === null ? 'Chưa có dữ liệu' : formatNumber(building.energyKwh)}</strong>
                  {building.energyKwh !== null && <span>{building.unit}</span>}
                </div>
                <div className="coverage-row"><span>Mức phủ dữ liệu</span><strong>{building.coverage === 'none' ? 'Chưa có' : `${formatNumber(building.coverageRatio * 100, 0)}%`}</strong></div>
                <div className="coverage-track" aria-label={`Mức phủ ${formatNumber(building.coverageRatio * 100, 0)} phần trăm`}><span style={{ width: `${Math.min(100, Math.max(0, building.coverageRatio * 100))}%` }} /></div>
                <p className={`coverage-copy coverage-${building.coverage}`}>
                  {building.coverage === 'partial' ? 'Điện năng ghi nhận — dữ liệu chưa đầy đủ' : building.coverage === 'none' ? 'Chưa có khoảng đo được ghi nhận' : `${building.includedIntervalCount} khoảng đo được ghi nhận`}
                </p>
                <div className="card-footer"><span>{formatDateTime(building.range.start)} → {formatDateTime(building.range.end)}</span><AppLink className="text-link" to={`/devices?building_id=${encodeURIComponent(building.buildingId)}`}>Xem thiết bị <span aria-hidden="true">↗</span></AppLink></div>
              </article>
            ))}
          </div>
        )}
      </QueryPanel>
      <p className="synthetic-note">Dữ liệu minh họa, không phải số liệu thực của khuôn viên.</p>
    </section>
  )
}

export function rangeKey(range: TimeRange): string {
  return `${range.start}:${range.end}`
}
