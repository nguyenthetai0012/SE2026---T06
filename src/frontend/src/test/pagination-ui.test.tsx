import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DevicesPage } from '../features/devices/DevicesPage'
import { AlertsPage } from '../features/alerts/AlertsPage'
import { HistoryPage } from '../features/history/HistoryPage'
import { MockDashboardRepository } from '../mocks/mockRepository'
import { dashboardFixture } from '../mocks/fixtures'
import { RepositoryError } from '../api/repository'

function repositoryWithTwoAlerts() {
  const first = dashboardFixture.alerts.data[0]
  return new MockDashboardRepository({
    ...dashboardFixture,
    alerts: {
      ...dashboardFixture.alerts,
      data: [first, { ...first, alert_id: 'alert-0002' }],
    },
  })
}

describe('Dashboard pagination controls', () => {
  it('keeps the building filter when a device page fails and is retried', async () => {
    const user = userEvent.setup()
    const repository = repositoryWithTwoAlerts()
    const original = repository.getDevices.bind(repository)
    let fail = true
    const get = vi.spyOn(repository, 'getDevices').mockImplementation(async (query) => {
      if (query.cursor && fail) {
        fail = false
        throw new RepositoryError('Lỗi thử nghiệm', 'TEST', 'test')
      }
      return original({ ...query, limit: 1 })
    })
    render(<DevicesPage repository={repository} />)
    await screen.findByTestId('device-A-01')
    await user.selectOptions(screen.getByLabelText('Lọc theo tòa nhà'), 'BLD-A')
    await screen.findByTestId('device-A-01')
    await user.click(screen.getByRole('button', { name: 'Trang tiếp' }))
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }))
    await screen.findByTestId('device-A-02')
    expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ buildingId: 'BLD-A', cursor: '1' }))
    await user.selectOptions(screen.getByLabelText('Lọc theo tòa nhà'), 'BLD-B')
    await screen.findByTestId('device-B-01')
    expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ buildingId: 'BLD-B', cursor: null }))
    expect(screen.getByText('Trang 1')).toBeInTheDocument()
  })

  it('keeps alert filters through pagination, error and retry', async () => {
    const user = userEvent.setup()
    const repository = repositoryWithTwoAlerts()
    const original = repository.getAlerts.bind(repository)
    let fail = true
    const get = vi.spyOn(repository, 'getAlerts').mockImplementation(async (query) => {
      if (query.cursor && fail) {
        fail = false
        throw new RepositoryError('Lỗi thử nghiệm', 'TEST', 'test')
      }
      return original({ ...query, limit: 1 })
    })
    render(<AlertsPage repository={repository} />)
    await screen.findByTestId('alert-alert-0001')
    await user.selectOptions(screen.getByLabelText('Lọc cảnh báo theo tòa nhà'), 'BLD-A')
    await user.selectOptions(screen.getByLabelText('Lọc cảnh báo theo thiết bị'), 'A-01')
    await waitFor(() => expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ buildingId: 'BLD-A', deviceId: 'A-01', cursor: null })))
    await screen.findByTestId('alert-alert-0001')
    await user.click(screen.getByRole('button', { name: 'Trang tiếp' }))
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }))
    await screen.findByTestId('alert-alert-0002')
    expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ buildingId: 'BLD-A', deviceId: 'A-01', cursor: '1' }))
    await user.click(screen.getByRole('button', { name: 'Trang trước' }))
    await screen.findByTestId('alert-alert-0001')
    expect(screen.getByText('Trang 1')).toBeInTheDocument()
  })

  it('keeps history range on retry and resets cursor when metric changes', async () => {
    const user = userEvent.setup()
    const repository = repositoryWithTwoAlerts()
    const original = repository.getReadings.bind(repository)
    let fail = true
    const get = vi.spyOn(repository, 'getReadings').mockImplementation(async (query) => {
      if (query.cursor && fail) {
        fail = false
        throw new RepositoryError('Lỗi thử nghiệm', 'TEST', 'test')
      }
      return original({ ...query, limit: 1 })
    })
    render(<HistoryPage repository={repository} deviceId="A-01" />)
    await screen.findByRole('table', { name: /bảng dữ liệu cảm biến/i })
    const range = repository.getDefaultHistoryRange()
    await user.click(screen.getByRole('button', { name: 'Trang tiếp' }))
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }))
    await screen.findByRole('table', { name: /bảng dữ liệu cảm biến/i })
    expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ deviceId: 'A-01', metric: 'power_kw', range, cursor: '1' }))
    await user.selectOptions(screen.getByLabelText('Chọn thông số'), 'energy_kwh')
    await waitFor(() => expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ deviceId: 'A-01', metric: 'energy_kwh', range, cursor: null })))
    expect(screen.getByText('Trang 1')).toBeInTheDocument()
  })
})
