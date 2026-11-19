import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MockDashboardRepository } from '../mocks/mockRepository'
import { dashboardFixture } from '../mocks/fixtures'
import type { MockScenario } from '../api/models'
import { App } from '../app/App'

export function renderDashboard(scenario: MockScenario = 'normal', route = '/') {
  window.history.replaceState(null, '', route)
  const repository = new MockDashboardRepository(dashboardFixture, scenario)
  return { ...render(<App repository={repository} />), repository }
}

export function renderElement(element: ReactElement) {
  return render(element)
}
