import { useRef, useState } from 'react'
import type { Booking } from '../api/client'
import { useBookings, useNearestDates, useServerNow, useShips } from '../api/hooks'
import { BookingDetails } from '../components/BookingDetails'
import { FleetTimeline } from '../components/FleetTimeline'
import { EmptyState, ErrorState, Notice, Skeleton, ui, type NoticeMessage } from '../components/ui'
import { addDays, centralDate, formatDate, formatRange } from '../lib/time'
import styles from './FleetDashboard.module.css'

export function FleetDashboard() {
  const serverNow = useServerNow()
  const ships = useShips()

  const [dateChoice, setDateChoice] = useState<string | null>(null)
  const [showCancelled, setShowCancelled] = useState(false)
  const [opened, setOpened] = useState<Booking | null>(null)
  const [notice, setNotice] = useState<NoticeMessage | null>(null)

  const today = serverNow.data ? centralDate(serverNow.data) : null
  const date = dateChoice ?? today

  const bookings = useBookings(date, showCancelled)
  const isEmpty = bookings.data?.length === 0
  const nearest = useNearestDates(date, showCancelled, isEmpty)

  // Remember which booking opened the details so focus can go back to it on close.
  // (Safari doesn't focus a button on click, so the browser can't be relied on for this.)
  const opener = useRef<HTMLElement | null>(null)

  function open(booking: Booking, element: HTMLElement) {
    opener.current = element
    setOpened(booking)
  }

  function close() {
    setOpened(null)
    if (opener.current?.isConnected) opener.current.focus()
  }

  function goTo(day: string | null) {
    setDateChoice(day)
    setNotice(null)
  }

  // The "day with bookings" buttons go away once a day has bookings, so focus moves
  // to the heading that names the day now showing.
  const dayHeading = useRef<HTMLHeadingElement>(null)

  function jumpTo(day: string | null) {
    goTo(day)
    dayHeading.current?.focus()
  }

  if (serverNow.isError) {
    return <ErrorState error={serverNow.error} onRetry={() => serverNow.refetch()} />
  }
  if (ships.isError) return <ErrorState error={ships.error} onRetry={() => ships.refetch()} />
  if (!ships.data || !serverNow.data || !today || !date) {
    return <Skeleton label="Loading the fleet" />
  }

  const active = bookings.data?.filter((b) => b.status === 'active') ?? []
  // Read the open booking from the latest list, so a refresh after a 409 shows its real state.
  const openedNow = opened && (bookings.data?.find((b) => b.id === opened.id) ?? opened)

  return (
    <>
      <h1>Fleet dashboard</h1>

      <div className={styles.controls}>
        <button type="button" className={ui.button} onClick={() => goTo(addDays(date, -1))}>
          ← Previous day
        </button>
        <label className={ui.field}>
          <span className={ui.visuallyHidden}>Date (Central)</span>
          <input
            type="date"
            className={ui.input}
            value={date}
            onChange={(e) => goTo(e.target.value || null)}
          />
        </label>
        <button type="button" className={ui.button} onClick={() => goTo(addDays(date, 1))}>
          Next day →
        </button>
        <button
          type="button"
          className={ui.button}
          disabled={date === today}
          onClick={() => goTo(null)}
        >
          Today
        </button>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={showCancelled}
            onChange={(e) => setShowCancelled(e.target.checked)}
          />
          Show cancelled
        </label>
      </div>

      <Notice notice={notice} />

      <h2 className={styles.day} ref={dayHeading} tabIndex={-1}>
        {formatDate(date)}
        {date === today && <span className={styles.today}>Today</span>}
      </h2>

      {bookings.isError ? (
        <ErrorState error={bookings.error} onRetry={() => bookings.refetch()} />
      ) : !bookings.data ? (
        <Skeleton rows={5} label="Loading bookings" />
      ) : isEmpty ? (
        <EmptyState title="No bookings on this day">
          <button
            type="button"
            className={ui.button}
            disabled={!nearest.data?.previous}
            onClick={() => jumpTo(nearest.data!.previous)}
          >
            ← Previous day with bookings
          </button>
          <button
            type="button"
            className={ui.button}
            disabled={!nearest.data?.next}
            onClick={() => jumpTo(nearest.data!.next)}
          >
            Next day with bookings →
          </button>
        </EmptyState>
      ) : (
        <>
          <div className={styles.timeline}>
            <FleetTimeline ships={ships.data} bookings={active} onOpen={open} />
          </div>

          <section className={styles.list} aria-label="Bookings by ship">
            {ships.data.map((ship) => {
              const forShip = bookings.data.filter((b) => b.shipId === ship.id)
              return (
                <div key={ship.id} className={styles.group}>
                  <h3>{ship.name}</h3>
                  {forShip.length === 0 ? (
                    <p className={styles.none}>No bookings</p>
                  ) : (
                    <ul>
                      {forShip.map((booking) => (
                        <li key={booking.id}>
                          <button
                            type="button"
                            className={styles.entry}
                            onClick={(e) => open(booking, e.currentTarget)}
                          >
                            <span className={styles.entryTimes}>
                              {formatRange(booking.startTime, booking.endTime)}
                            </span>
                            <span>{booking.pilotName}</span>
                            {booking.status === 'cancelled' && (
                              <span className={styles.cancelled}>Cancelled</span>
                            )}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            })}
          </section>
        </>
      )}

      {openedNow && (
        <BookingDetails
          key={openedNow.id}
          booking={openedNow}
          ship={ships.data.find((s) => s.id === openedNow.shipId)}
          serverNow={serverNow.data}
          onClose={close}
          onCancelled={(cancelled) => {
            close()
            setNotice({
              kind: 'success',
              text: `Cancelled ${cancelled.pilotName}'s booking, ${formatRange(cancelled.startTime, cancelled.endTime)}. That time is available again.`,
            })
          }}
        />
      )}
    </>
  )
}
