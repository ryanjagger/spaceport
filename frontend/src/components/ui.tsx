import type { ReactNode } from 'react'
import styles from './ui.module.css'

export interface NoticeMessage {
  kind: 'success' | 'error'
  text: string
}

/**
 * Success and error messages. The live region is always in the page, so screen
 * readers announce a message when it appears.
 */
export function Notice({ notice }: { notice: NoticeMessage | null }) {
  return (
    <div role="status" aria-live="polite">
      {notice && <p className={`${styles.notice} ${styles[notice.kind]}`}>{notice.text}</p>}
    </div>
  )
}

export function Skeleton({ rows = 3, label }: { rows?: number; label: string }) {
  return (
    <div className={styles.skeleton} role="status">
      <span className={styles.visuallyHidden}>{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.skeletonBar} />
      ))}
    </div>
  )
}

/** Shows the API's own message, never a status code. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div className={styles.state} role="alert">
      <p className={styles.stateTitle}>{errorMessage(error)}</p>
      <button type="button" className={styles.button} onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={styles.state}>
      <p className={styles.stateTitle}>{title}</p>
      {children && <div className={styles.stateActions}>{children}</div>}
    </div>
  )
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Try again.'
}

export { styles as ui }
