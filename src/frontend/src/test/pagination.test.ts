import { describe, expect, it } from 'vitest'
import { MockDashboardRepository } from '../mocks/mockRepository'
import { dashboardFixture } from '../mocks/fixtures'
import { HttpDashboardRepository } from '../api/httpRepository'

describe('cursor pagination', () => {
  it('paginates filtered mock devices without losing their building', async () => {
    const repository = new MockDashboardRepository(dashboardFixture)
    const first = await repository.getDevices({ buildingId: 'BLD-A', limit: 1 })
    expect(first.meta.nextCursor).not.toBeNull()
    const second = await repository.getDevices({ buildingId: 'BLD-A', limit: 1, cursor: first.meta.nextCursor })
    expect(second.items[0].buildingId).toBe('BLD-A')
    expect(second.items[0].deviceId).not.toBe(first.items[0].deviceId)
  })

  it('sends the device filter, limit and opaque cursor to the API', async () => {
    let requested = ''
    const fetcher: typeof fetch = async (input) => {
      requested = String(input)
      return new Response(JSON.stringify({ data: [], meta: { generated_at: '2026-01-01T00:00:00Z', next_cursor: null } }), { status: 200 })
    }
    await new HttpDashboardRepository('/api/v1', fetcher).getDevices({ buildingId: 'BLD-A', limit: 1, cursor: 'opaque+cursor' })
    const url = new URL(requested, 'http://localhost')
    expect(url.searchParams.get('building_id')).toBe('BLD-A')
    expect(url.searchParams.get('limit')).toBe('1')
    expect(url.searchParams.get('cursor')).toBe('opaque+cursor')
  })
})
