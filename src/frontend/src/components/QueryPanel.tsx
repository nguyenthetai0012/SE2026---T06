import { useState, type FormEvent, type ReactNode } from 'react'
import type { QueryState } from './useDashboardQuery'
import { localInputToUtc, utcToLocalInput } from '../api/format'

interface QueryPanelProps<T> {
  state: QueryState<T>
  retry: () => void
  isEmpty: (data: T) => boolean
  emptyText: string
  children: (data: T) => ReactNode
}

export function QueryPanel<T>({ state, retry, isEmpty, emptyText, children }: QueryPanelProps<T>) {
  if (state.loading && state.data === undefined) {
    return <div className="state-card" role="status" aria-live="polite"><span className="spinner" />Đang tải dữ liệu…</div>
  }

  if (state.error && state.data === undefined) {
    return (
      <div className="state-card state-error" role="alert">
        <div><strong>Không tải được dữ liệu</strong><p>{state.error.message}</p><small>Mã yêu cầu: {state.error.requestId}</small></div>
        <button className="button button-primary" type="button" onClick={retry}>Thử tải lại</button>
      </div>
    )
  }

  if (state.data === undefined) return null

  return (
    <>
      {state.error && (
        <div className="inline-error" role="alert">
          Không cập nhật được dữ liệu mới. Đang giữ kết quả tải thành công lúc trước. {state.error.message}
          <button type="button" className="button button-small" onClick={retry}>Thử lại</button>
        </div>
      )}
      {state.refreshing && <div className="refresh-note" role="status">Đang cập nhật…</div>}
      {!state.error && !state.refreshing && <div className="query-refresh"><button type="button" className="button button-small" onClick={retry}>Tải mới</button></div>}
      {isEmpty(state.data)
        ? <div className="state-card state-empty" role="status"><span className="empty-mark">—</span><strong>Không có dữ liệu</strong><p>{emptyText}</p></div>
        : children(state.data)}
    </>
  )
}

export function PageTitle({ id, eyebrow, title, description, action }: { id?: string; eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="page-title-row">
      <div><p className="eyebrow">{eyebrow}</p><h1 id={id}>{title}</h1><p className="page-description">{description}</p></div>
      {action}
    </div>
  )
}

export function TimeRangeForm({
  initial,
  onApply,
}: {
  initial: { start: string; end: string }
  onApply: (range: { start: string; end: string }) => void
}) {
  const [start, setStart] = useState(() => utcToLocalInput(initial.start))
  const [end, setEnd] = useState(() => utcToLocalInput(initial.end))
  const [error, setError] = useState('')

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const startUtc = localInputToUtc(start)
    const endUtc = localInputToUtc(end)
    if (!startUtc || !endUtc || startUtc >= endUtc) {
      setError('Thời điểm bắt đầu phải sớm hơn thời điểm kết thúc.')
      return
    }
    setError('')
    onApply({ start: startUtc, end: endUtc })
  }

  return (
    <form className="range-form" onSubmit={apply}>
      <label> Từ <input aria-label="Từ thời điểm" type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} /> </label>
      <label> Đến <input aria-label="Đến thời điểm" type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} /> </label>
      <span className="timezone-hint">Giờ Việt Nam (UTC+7)</span>
      <button className="button button-primary" type="submit">Áp dụng</button>
      {error && <p className="field-error" role="alert">{error}</p>}
    </form>
  )
}
