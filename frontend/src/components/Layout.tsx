import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useServerNow } from '../api/hooks'
import { formatTime } from '../lib/time'
import styles from './Layout.module.css'

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.link} ${styles.active}` : styles.link

export function Layout() {
  const { pathname } = useLocation()
  const serverNow = useServerNow()

  // Each screen gets its own tab title, so history, tabs and screen readers can tell them apart.
  useEffect(() => {
    const screen = pathname === '/fleet' ? 'Fleet dashboard' : 'Charter a ship'
    document.title = `${screen} · Pacific Spaceport`
  }, [pathname])

  return (
    <>
      <header className={styles.header}>
        <p className={styles.brand}>
          Pacific Spaceport <span>Charter desk</span>
        </p>
        <nav className={styles.nav} aria-label="Main">
          <NavLink to="/" end className={navClass}>
            Charter a ship
          </NavLink>
          <NavLink to="/fleet" className={navClass}>
            Fleet dashboard
          </NavLink>
        </nav>
        {/* The server's clock, as last heard: it is what "today" and "past" are judged by. */}
        {serverNow.data && (
          <p className={styles.clock}>
            Spaceport time <strong>{formatTime(serverNow.data)} CT</strong>
          </p>
        )}
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  )
}
