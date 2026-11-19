import { useEffect, useState, type AnchorHTMLAttributes, type MouseEvent } from 'react'

export type Route =
  | { page: 'overview' }
  | { page: 'devices'; buildingId?: string }
  | { page: 'history'; deviceId: string }
  | { page: 'alerts' }

export function parseRoute(pathname: string, search = ''): Route {
  if (pathname === '/devices') {
    return { page: 'devices', buildingId: new URLSearchParams(search).get('building_id') ?? undefined }
  }
  const historyMatch = pathname.match(/^\/devices\/([^/]+)\/history$/)
  if (historyMatch) return { page: 'history', deviceId: decodeURIComponent(historyMatch[1]) }
  if (pathname === '/alerts') return { page: 'alerts' }
  return { page: 'overview' }
}

export function navigate(to: string): void {
  window.history.pushState(null, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.pathname, window.location.search))
  useEffect(() => {
    const update = () => setRoute(parseRoute(window.location.pathname, window.location.search))
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])
  return route
}

export function AppLink({ to, children, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { to: string }) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    props.onClick?.(event)
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    navigate(to)
  }
  return (
    <a href={to} {...props} onClick={handleClick}>
      {children}
    </a>
  )
}
