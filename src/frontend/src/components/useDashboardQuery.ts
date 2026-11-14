import { useCallback, useEffect, useState } from 'react'
import { RepositoryError } from '../api/repository'

export interface QueryState<T> {
  data?: T
  loading: boolean
  refreshing: boolean
  error?: RepositoryError
}

export function useDashboardQuery<T>(key: string, load: () => Promise<T>) {
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<QueryState<T> & { key: string }>({ key, loading: true, refreshing: false })

  useEffect(() => {
    let active = true
    setState((current) => ({
      key,
      data: current.key === key ? current.data : undefined,
      loading: current.key !== key || current.data === undefined,
      refreshing: current.key === key && current.data !== undefined,
      error: undefined,
    }))
    void load().then((data) => {
      if (active) setState({ key, data, loading: false, refreshing: false })
    }).catch((error: unknown) => {
      if (!active) return
      const repositoryError = error instanceof RepositoryError
        ? error
        : new RepositoryError('Không thể tải dữ liệu. Vui lòng thử lại.', 'NETWORK_ERROR', 'unknown')
      setState((current) => ({
        key,
        data: current.key === key ? current.data : undefined,
        loading: false,
        refreshing: false,
        error: repositoryError,
      }))
    })
    return () => { active = false }
  }, [key, load, revision])

  const retry = useCallback(() => setRevision((current) => current + 1), [])
  const current = state.key === key ? state : { key, loading: true, refreshing: false }
  return { ...current, retry }
}
