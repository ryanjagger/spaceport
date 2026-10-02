import { useEffect, useRef, useState } from 'react'
import { NoResponseError, type Booking, type Ship } from '../api/client'
import { bookingDate, useCancelBooking, useRefreshSchedule } from '../api/hooks'
import { formatDate, formatTimeWithHint, isAfter } from '../lib/time'
import styles from './BookingDetails.module.css'
import { errorMessage, ui } from './ui'

interface Props {
  booking: Booking
  ship: Ship | undefined
  serverNow: string
  onClose: () => void
  onCancelled: (booking: Booking) => void
}

/**
 * A modal <dialog>: the browser moves focus into it when it opens, keeps it there,
 * closes it on Escape, and returns focus to the booking that opened it.
 */
export function BookingDetails({ booking, ship, serverNow, onClose, onCancelled }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cancelBooking = useCancelBooking()
  const refreshSchedule = useRefreshSchedule()

  useEffect(() => {
    const element = dialog.current
    if (element && !element.open) element.showModal()
  }, [])

  // The button is a convenience; the server makes the real decision and may answer 409.
  const canCancel = booking.status === 'active' && isAfter(booking.startTime, serverNow)
  const date = bookingDate(booking)

  function cancel() {
    setError(null)
    cancelBooking.mutate(booking, {
      onSuccess: (cancelled) => {
        refreshSchedule(booking.shipId, date)
        onCancelled(cancelled)
      },
      onError: (failure) => {
        setConfirming(false)
        setError(
          failure instanceof NoResponseError
            ? "We couldn't confirm whether this booking was cancelled. Its details have been refreshed; check them before trying again."
            : errorMessage(failure),
        )
        // Refreshes the list this panel reads from, so it shows the booking's real state.
        refreshSchedule(booking.shipId, date)
      },
    })
  }

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      onClose={onClose}
      aria-labelledby="details-title"
    >
      <h2 id="details-title">{ship?.name ?? `Ship ${booking.shipId}`}</h2>
      <dl className={styles.facts}>
        <dt>Pilot</dt>
        <dd>{booking.pilotName}</dd>
        <dt>Date</dt>
        <dd>{formatDate(date)}</dd>
        <dt>Departs</dt>
        <dd>{formatTimeWithHint(booking.startTime)}</dd>
        <dt>Returns</dt>
        <dd>{formatTimeWithHint(booking.endTime)}</dd>
        <dt>Status</dt>
        <dd>
          {booking.status === 'cancelled'
            ? 'Cancelled'
            : canCancel
              ? 'Upcoming'
              : 'Started or finished'}
        </dd>
      </dl>

      <div role="status" aria-live="polite">
        {error && <p className={`${ui.notice} ${ui.error}`}>{error}</p>}
      </div>

      <div className={styles.actions}>
        {canCancel && !confirming && (
          // autoFocus on this pair keeps keyboard focus on the step that replaces the last one.
          <button type="button" className={ui.button} autoFocus onClick={() => setConfirming(true)}>
            Cancel booking
          </button>
        )}
        {canCancel && confirming && (
          <>
            <p className={styles.confirm}>Cancel this booking? Its time becomes available again.</p>
            <button
              type="button"
              className={`${ui.button} ${ui.danger}`}
              autoFocus
              disabled={cancelBooking.isPending}
              onClick={cancel}
            >
              {cancelBooking.isPending ? 'Cancelling…' : 'Yes, cancel booking'}
            </button>
            <button
              type="button"
              className={ui.button}
              disabled={cancelBooking.isPending}
              onClick={() => setConfirming(false)}
            >
              Keep booking
            </button>
          </>
        )}
        <button
          type="button"
          className={`${ui.button} ${styles.close}`}
          onClick={() => dialog.current?.close()}
        >
          Close
        </button>
      </div>
    </dialog>
  )
}
