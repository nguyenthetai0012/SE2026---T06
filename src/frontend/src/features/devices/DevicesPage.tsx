import { useCallback, useState } from 'react'
import type { DashboardRepository } from '../../api/repository'
import type { Device } from '../../api/models'
import { formatDateTime } from '../../api/format'
import { AppLink } from '../../app/navigation'
import { PageTitle, QueryPanel } from '../../components/QueryPanel'
import { useDashboardQuery } from '../../components/useDashboardQuery'

const statusText: Record<Device['status'], string> = {
  online: 'Đang hoạt động',
  offline: 'Ngoại tuyến',
  unknown: 'Chưa xác định',
  disabled: 'Đã tắt',
}

export function DevicesPage({ repository, initialBuildingId }: { repository: DashboardRepository; initialBuildingId?: string }) {
  const [buildingId, setBuildingId] = useState(initialBuildingId ?? '')
  const load = useCallback(() => repository.getDevices({ buildingId: buildingId || undefined }), [repository, buildingId])
  const query = useDashboardQuery(`devices:${buildingId}`, load)

  return (
    <section aria-labelledby="devices-title">
      <PageTitle id="devices-title" eyebrow="THIẾT BỊ" title="Danh mục thiết bị" description="Trạng thái do nguồn dữ liệu cung cấp. Lỗi tải danh sách không làm thay đổi trạng thái thiết bị." />
      <div className="toolbar"><label className="filter-label">Tòa nhà <select aria-label="Lọc theo tòa nhà" value={buildingId} onChange={(event) => setBuildingId(event.target.value)}><option value="">Toàn khuôn viên</option><option value="BLD-A">Tòa nhà A</option><option value="BLD-B">Tòa nhà B</option></select></label><span className="timezone-hint">Trạng thái và độ mới là hai thông tin riêng</span></div>
      <QueryPanel state={query} retry={query.retry} isEmpty={(page) => page.items.length === 0} emptyText="Không có thiết bị trong phạm vi đang chọn.">
        {(page) => (
          <div className="device-grid">
            {page.items.map((device) => (
              <article className="device-card" key={device.deviceId} data-testid={`device-${device.deviceId}`}>
                <div className="device-heading"><span className={`device-indicator status-${device.status}`} aria-hidden="true" /><div><h2>{device.name}</h2><p>{device.deviceId} · {device.buildingId}</p></div><span className={`status-pill status-${device.status}`}>{statusText[device.status]}</span></div>
                <div className="device-meta"><span>Lần liên lạc gần nhất</span><strong>{formatDateTime(device.lastSeen)}</strong></div>
                <div className="device-meta"><span>Độ mới dữ liệu</span><strong className={device.isDataStale ? 'text-warning' : ''}>{device.isDataStale ? 'Dữ liệu cũ' : 'Trong hạn'}</strong></div>
                <div className="device-card-footer"><span>Chu kỳ đề xuất: {device.periodSeconds}s</span><AppLink className="text-link" to={`/devices/${encodeURIComponent(device.deviceId)}/history`}>Mở lịch sử <span aria-hidden="true">→</span></AppLink></div>
              </article>
            ))}
          </div>
        )}
      </QueryPanel>
    </section>
  )
}
