import { useCallback, useState } from 'react'
import type { DashboardRepository } from '../../api/repository'
import { formatDateTime, formatNumber } from '../../api/format'
import { AppLink } from '../../app/navigation'
import { PageTitle, QueryPanel } from '../../components/QueryPanel'
import { useDashboardQuery } from '../../components/useDashboardQuery'

export function AlertsPage({ repository }: { repository: DashboardRepository }) {
  const [buildingId, setBuildingId] = useState('')
  const [deviceId, setDeviceId] = useState('')
  const load = useCallback(() => repository.getAlerts({ buildingId: buildingId || undefined, deviceId: deviceId || undefined }), [repository, buildingId, deviceId])
  const query = useDashboardQuery(`alerts:${buildingId}:${deviceId}`, load)

  return (
    <section aria-labelledby="alerts-title">
      <PageTitle id="alerts-title" eyebrow="CẢNH BÁO" title="Bất thường được ghi nhận" description="Dashboard chỉ hiển thị cảnh báo do nguồn dữ liệu cung cấp; không tự áp ngưỡng hay tạo cảnh báo." />
      <div className="toolbar"><label className="filter-label">Tòa nhà <select aria-label="Lọc cảnh báo theo tòa nhà" value={buildingId} onChange={(event) => { setBuildingId(event.target.value); setDeviceId('') }}><option value="">Tất cả tòa nhà</option><option value="BLD-A">Tòa nhà A</option><option value="BLD-B">Tòa nhà B</option></select></label><label className="filter-label">Thiết bị <select aria-label="Lọc cảnh báo theo thiết bị" value={deviceId} onChange={(event) => setDeviceId(event.target.value)}><option value="">Tất cả thiết bị</option><option value="A-01">A-01</option><option value="A-02">A-02</option><option value="B-01">B-01</option></select></label></div>
      <QueryPanel state={query} retry={query.retry} isEmpty={(page) => page.items.length === 0} emptyText="Không có cảnh báo trong phạm vi đã chọn.">
        {(page) => (
          <div className="alert-list">
            {page.items.map((alert) => (
              <article className="alert-card" key={alert.alertId} data-testid={`alert-${alert.alertId}`}>
                <div className="alert-symbol" aria-hidden="true">!</div><div className="alert-content"><div className="alert-meta"><span className="alert-label">CẢNH BÁO NGUỒN</span><span>{alert.alertId}</span></div><h2>{alert.description}</h2><p>{alert.metric} · {formatNumber(alert.value)} {alert.unit} · Giá trị/tham chiếu do Backend cung cấp: {formatNumber(alert.threshold)} {alert.unit}</p><div className="alert-footer"><span>{alert.buildingId} · {alert.deviceId}</span><span>Đo {formatDateTime(alert.eventTime)} · Phát hiện {formatDateTime(alert.detectedAt)}</span><AppLink className="text-link" to={`/devices/${encodeURIComponent(alert.deviceId)}/history`}>Xem lịch sử liên quan →</AppLink></div></div>
              </article>
            ))}
          </div>
        )}
      </QueryPanel>
    </section>
  )
}
