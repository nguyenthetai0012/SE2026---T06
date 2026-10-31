export function formatDateTime(value: string | null): string {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Thời gian không hợp lệ'
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(date)
}

export function formatNumber(value: number, maximumFractionDigits = 3): string {
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits }).format(value)
}

export function utcToLocalInput(value: string): string {
  const date = new Date(value)
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date)
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? '00'
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`
}

export function localInputToUtc(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) return null
  const date = new Date(`${value}:00+07:00`)
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}
