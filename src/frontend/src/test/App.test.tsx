import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderDashboard } from './testUtils'

describe('Dashboard mock-first UI', () => {
  it('AC-01/AC-12: shows distinct building summaries with their own IDs, ranges and values', async () => {
    renderDashboard()
    const buildingA = await screen.findByTestId('summary-BLD-A')
    const buildingB = screen.getByTestId('summary-BLD-B')
    expect(within(buildingA).getByText('Tòa nhà A')).toBeInTheDocument()
    expect(within(buildingA).getByText('0,5')).toBeInTheDocument()
    expect(within(buildingA).getByText(/dữ liệu chưa đầy đủ/i)).toBeInTheDocument()
    expect(within(buildingB).getByText('0,1')).toBeInTheDocument()
    expect(within(buildingB).getByText(/2 khoảng đo/i)).toBeInTheDocument()
  })

  it('AC-02/AC-05/AC-11: distinguishes online, offline, unknown and disabled states', async () => {
    renderDashboard('normal', '/devices')
    await screen.findByTestId('device-A-01')
    expect(within(screen.getByTestId('device-A-02')).getByText('Ngoại tuyến')).toBeInTheDocument()
    expect(within(screen.getByTestId('device-X-01')).getByText('Chưa xác định')).toBeInTheDocument()
    expect(within(screen.getByTestId('device-B-02')).getByText('Đã tắt')).toBeInTheDocument()
    expect(within(screen.getByTestId('device-A-01')).getByText('Đang hoạt động')).toBeInTheDocument()
  })

  it('AC-03/AC-06/AC-10: shows ordered history rows and source late/out-of-order flags', async () => {
    renderDashboard('normal', '/devices/A-01/history')
    await screen.findByRole('table', { name: /bảng dữ liệu cảm biến/i })
    expect(screen.getByText('Đến trễ')).toBeInTheDocument()
    expect(screen.getAllByText('Sai thứ tự nhận').length).toBeGreaterThan(0)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('11 kW')
    expect(rows[1]).toHaveTextContent('Đến trễ')
  })

  it('AC-04: displays alerts with their linked device and source values', async () => {
    renderDashboard('normal', '/alerts')
    const alert = await screen.findByTestId('alert-alert-0001')
    expect(within(alert).getByText(/BLD-A · A-01/)).toBeInTheDocument()
    expect(within(alert).getByText(/10,1 kW/)).toBeInTheDocument()
    expect(within(alert).getByRole('link', { name: /xem lịch sử liên quan/i })).toHaveAttribute('href', '/devices/A-01/history')
  })

  it('AC-07: exposes a loading state before a delayed response resolves', async () => {
    renderDashboard('delayed', '/devices')
    expect(screen.getByRole('status')).toHaveTextContent('Đang tải dữ liệu')
    expect(await screen.findByTestId('device-A-01', {}, { timeout: 2500 })).toBeInTheDocument()
  })

  it('AC-08: represents an empty successful query separately from a failure', async () => {
    renderDashboard('empty', '/alerts')
    expect(await screen.findByText('Không có dữ liệu')).toBeInTheDocument()
    expect(screen.queryByText('Không tải được dữ liệu')).not.toBeInTheDocument()
  })

  it('AC-09: retries the same mock query and preserves the screen scope', async () => {
    const user = userEvent.setup()
    renderDashboard('error-once', '/alerts')
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }))
    expect(await screen.findByTestId('alert-alert-0001')).toBeInTheDocument()
  })

  it('AC-11: a query failure is reported as a load error, never as offline status', async () => {
    renderDashboard('error-once', '/devices')
    const error = await screen.findByRole('alert')
    expect(error).toHaveTextContent('Không tải được dữ liệu')
    expect(screen.queryByText('Ngoại tuyến')).not.toBeInTheDocument()
  })

  it('AC-12: navigation keeps building and device identity consistent across screens', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByTestId('summary-BLD-A')
    await user.click(screen.getAllByRole('link', { name: /xem thiết bị/i })[0])
    expect(await screen.findByTestId('device-A-01')).toBeInTheDocument()
    expect(screen.queryByTestId('device-B-01')).not.toBeInTheDocument()
  })

  it('keeps a prior response visible with an update error after refresh fails', async () => {
    const user = userEvent.setup()
    renderDashboard('error-refresh', '/alerts')
    expect(await screen.findByTestId('alert-alert-0001')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Tải mới' }))
    expect(await screen.findByText(/không cập nhật được dữ liệu mới/i)).toBeInTheDocument()
    expect(screen.getByTestId('alert-alert-0001')).toBeInTheDocument()
  })
})
