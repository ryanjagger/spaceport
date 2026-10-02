import { CheckCircleIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { useEffect, useRef, type ReactNode } from 'react'
import styles from './ui.module.css'

export interface NoticeMessage {
  kind: 'success' | 'error'
  text: string
}

/**
 * Success and error messages. The live region is always in the page, so screen
 * readers announce a message when it appears.
 *
 * A new message also takes focus. The action that caused it has often disabled or
 * removed the control that was focused, and on a narrow screen that control can be
 * a long scroll away; focusing the message brings it into view and gives keyboard
 * users somewhere to carry on from.
 */
export function Notice({ notice }: { notice: NoticeMessage | null }) {
  const message = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    message.current?.focus()
  }, [notice])

  return (
    <div role="status" aria-live="polite">
      {notice && (
        <p ref={message} tabIndex={-1} className={`${styles.notice} ${styles[notice.kind]}`}>
          {/* The icon repeats what the colour says, for anyone who can't tell them apart. */}
          {notice.kind === 'success' ? (
            <CheckCircleIcon className={styles.noticeIcon} size={20} weight="fill" aria-hidden />
          ) : (
            <WarningCircleIcon className={styles.noticeIcon} size={20} weight="fill" aria-hidden />
          )}
          <span>{notice.text}</span>
        </p>
      )}
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
