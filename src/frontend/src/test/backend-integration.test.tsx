import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HttpDashboardRepository } from '../api/httpRepository'
import { DevicesPage } from '../features/devices/DevicesPage'

const apiUrl = import.meta.env.VITE_TEST_API_URL

describe.runIf(Boolean(apiUrl))('Frontend against real Backend and PostgreSQL', () => {
  it('renders seeded devices and reads the other API endpoints', async () => {
    const repository = new HttpDashboardRepository(apiUrl)
    render(<DevicesPage repository={repository} initialBuildingId="BLD-A" />)
    const card = await screen.findByTestId('device-A-01')
    expect(within(card).getByText(/BLD-A/)).toBeInTheDocument()
    expect(within(card).getByText('Chưa xác định')).toBeInTheDocument()
    expect(await screen.findByTestId('device-A-02')).toBeInTheDocument()
    expect(screen.queryByTestId('device-B-01')).not.toBeInTheDocument()

    const range = { start: '2026-10-27T00:00:00Z', end: '2026-10-27T01:00:00Z' }
    const [summary, readings, alerts] = await Promise.all([
      repository.getSummary({ range }),
      repository.getReadings({ deviceId: 'A-01', metric: 'power_kw', range, limit: 100 }),
      repository.getAlerts({ buildingId: 'BLD-A' }),
    ])
    expect(summary.items.map((item) => item.buildingId)).toEqual(['BLD-A', 'BLD-B'])
    expect(summary.items[0].energyKwh).toBeNull()
    expect(readings.items).toEqual([])
    expect(alerts.items).toEqual([])
  })
})
