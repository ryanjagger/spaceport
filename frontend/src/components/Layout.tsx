import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import styles from './Layout.module.css'

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.link} ${styles.active}` : styles.link

export function Layout() {
  const { pathname } = useLocation()

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
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  )
}
