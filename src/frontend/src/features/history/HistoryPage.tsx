import { useCallback, useState } from 'react'
import type { Metric } from '../../api/dto'
import type { DashboardRepository } from '../../api/repository'
import type { Reading, TimeRange } from '../../api/models'
import { formatDateTime, formatNumber } from '../../api/format'
import { AppLink } from '../../app/navigation'
import { PageTitle, QueryPanel, TimeRangeForm } from '../../components/QueryPanel'
import { useDashboardQuery } from '../../components/useDashboardQuery'

export function HistoryPage({ repository, deviceId }: { repository: DashboardRepository; deviceId: string }) {
  const [metric, setMetric] = useState<Metric>('power_kw')
  const [range, setRange] = useState(() => repository.getDefaultHistoryRange())
  const load = useCallback(() => repository.getReadings({ deviceId, metric, range, limit: 100 }), [repository, deviceId, metric, range])
  const query = useDashboardQuery(`history:${deviceId}:${metric}:${range.start}:${range.end}`, load)

  return (
    <section aria-labelledby="history-title">
      <PageTitle id="history-title" eyebrow="LỊCH SỬ CẢM BIẾN" title={`Lịch sử · ${deviceId}`} description="Trục thời gian dùng thời điểm đo; dữ liệu đến trễ và sai thứ tự được gắn cờ theo phản hồi nguồn." action={<AppLink className="button button-quiet" to="/devices">← Danh sách thiết bị</AppLink>} />
      <div className="toolbar history-toolbar"><label className="filter-label">Thông số <select aria-label="Chọn thông số" value={metric} onChange={(event) => setMetric(event.target.value as Metric)}><option value="power_kw">Công suất</option><option value="energy_kwh">Điện năng</option></select></label><TimeRangeForm key={`${deviceId}-${metric}`} initial={range} onApply={setRange} /></div>
      <QueryPanel state={query} retry={query.retry} isEmpty={(page) => page.items.length === 0} emptyText="Không có bản ghi phù hợp với thiết bị, thông số và khoảng thời gian đã chọn.">
        {(page) => <HistoryResults readings={page.items} nextCursor={page.meta.nextCursor} />}
      </QueryPanel>
    </section>
  )
}

function HistoryResults({ readings, nextCursor }: { readings: Reading[]; nextCursor: string | null }) {
  return (
    <>
      <div className="history-summary"><span>{readings.length} điểm dữ liệu trong trang hiện tại</span>{nextCursor && <span className="pagination-note">Còn dữ liệu chưa tải · cursor được nguồn cung cấp</span>}</div>
      <div className="chart-card"><div className="chart-heading"><div><p className="eyebrow">DIỄN BIẾN</p><h2>Giá trị theo thời điểm đo</h2></div><span className="unit-tag">{readings[0]?.unit ?? ''}</span></div><HistoryChart readings={readings} /></div>
      <div className="table-wrap"><table><caption>Bảng dữ liệu cảm biến, giữ nguyên đơn vị và cờ do nguồn cung cấp</caption><thead><tr><th scope="col">Thời điểm đo</th><th scope="col">Giá trị</th><th scope="col">Thời điểm nhận</th><th scope="col">Chất lượng dữ liệu</th></tr></thead><tbody>
        {readings.map((reading) => <tr key={reading.messageId}><td>{formatDateTime(reading.eventTime)}</td><td><strong>{formatNumber(reading.value)}</strong> {reading.unit}</td><td>{formatDateTime(reading.receivedAt)}</td><td><div className="flag-list">{reading.isLate && <span className="flag flag-late">Đến trễ</span>}{reading.isOutOfOrder && <span className="flag flag-order">Sai thứ tự nhận</span>}{!reading.isLate && !reading.isOutOfOrder && <span className="muted-label">Bình thường</span>}</div></td></tr>)}
      </tbody></table></div>
      <p className="synthetic-note">Mẫu hiển thị giữ thứ tự dữ liệu do repository trả về; giao diện không sửa cờ late/out-of-order.</p>
    </>
  )
}

function HistoryChart({ readings }: { readings: Reading[] }) {
  if (readings.length === 0) return null
  const values = readings.map((reading) => reading.value)
  const low = Math.min(...values)
  const high = Math.max(...values)
  const span = high - low || 1
  const points = readings.map((reading, index) => {
    const x = readings.length === 1 ? 50 : 8 + index * (84 / (readings.length - 1))
    const y = 82 - ((reading.value - low) / span) * 62
    return `${x},${y}`
  }).join(' ')
  return (
    <div className="chart-layout">
      <span className="chart-max">{formatNumber(high)}</span>
      <svg className="line-chart" viewBox="0 0 100 100" role="img" aria-label={`Biểu đồ ${readings.length} điểm dữ liệu, đơn vị ${readings[0].unit}`}>
        <line x1="6" y1="20" x2="94" y2="20" className="chart-gridline" /><line x1="6" y1="51" x2="94" y2="51" className="chart-gridline" /><line x1="6" y1="82" x2="94" y2="82" className="chart-gridline" />
        <polyline points={points} className="chart-line" />
        {readings.map((reading, index) => {
          const x = readings.length === 1 ? 50 : 8 + index * (84 / (readings.length - 1))
          const y = 82 - ((reading.value - low) / span) * 62
          return <circle key={reading.messageId} cx={x} cy={y} r="2.2" className={reading.isLate ? 'chart-point chart-point-late' : 'chart-point'}><title>{`${formatDateTime(reading.eventTime)} · ${formatNumber(reading.value)} ${reading.unit}${reading.isLate ? ' · đến trễ' : ''}`}</title></circle>
        })}
      </svg>
      <span className="chart-min">{formatNumber(low)}</span>
      <div className="chart-axis"><span>{formatDateTime(readings[0].eventTime)}</span><span>{formatDateTime(readings[readings.length - 1].eventTime)}</span></div>
    </div>
  )
}

export function historyRange(query: TimeRange): string {
  return `${query.start}/${query.end}`
}
