import { useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useServerNow } from '../api/hooks'
import { formatTime } from '../lib/time'
import styles from './Layout.module.css'
import { Logo } from './Logo'

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
        <Link to="/" className={styles.brand}>
          <Logo />
          Pacific Spaceport
        </Link>
        <nav className={styles.nav} aria-label="Main">
          <NavLink to="/" end className={navClass}>
            Charter a ship
          </NavLink>
          <NavLink to="/fleet" className={navClass}>
            Fleet dashboard
          </NavLink>
        </nav>
        {/* The server's clock, as last heard: it is what "today" and "past" are judged by.
            Always in the bar, so its space is held while loading and a failure is said. */}
        <p className={styles.clock}>
          {serverNow.data ? (
            <>
              <span className={styles.clockLabel}>Spaceport time</span>
              <time dateTime={serverNow.data} title="Central Time, the spaceport's clock">
                {formatTime(serverNow.data)} CT
              </time>
            </>
          ) : (
            serverNow.isError && 'Spaceport time unavailable'
          )}
        </p>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  )
}
