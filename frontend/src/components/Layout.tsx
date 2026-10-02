import { NavLink, Outlet } from 'react-router-dom'
import styles from './Layout.module.css'

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.link} ${styles.active}` : styles.link

export function Layout() {
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
