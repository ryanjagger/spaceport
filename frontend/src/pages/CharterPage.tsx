import { useState, type FormEvent } from 'react'
import { NoResponseError, type Slot } from '../api/client'
import {
  useAvailability,
  useCreateBooking,
  useRefreshSchedule,
  useServerNow,
  useShips,
} from '../api/hooks'
import { SlotGrid } from '../components/SlotGrid'
import {
  EmptyState,
  ErrorState,
  errorMessage,
  Notice,
  Skeleton,
  ui,
  type NoticeMessage,
} from '../components/ui'
import {
  centralDate,
  formatDate,
  formatDuration,
  formatDurationAdjective,
  formatRange,
  formatTime,
  formatTimeWithHint,
} from '../lib/time'
import styles from './CharterPage.module.css'

const DURATIONS = Array.from({ length: 16 }, (_, i) => (i + 1) * 30) // 30 minutes to 8 hours

export function CharterPage() {
  const serverNow = useServerNow()
  const ships = useShips()

  const [shipChoice, setShipChoice] = useState<number | null>(null)
  const [dateChoice, setDateChoice] = useState<string | null>(null)
  const [duration, setDuration] = useState(60)
  const [selectedStart, setSelectedStart] = useState<string | null>(null)
  const [pilotName, setPilotName] = useState('')
  const [notice, setNotice] = useState<NoticeMessage | null>(null)

  // "Today" is the server's Central date. A page left open past midnight moves on with it.
  const today = serverNow.data ? centralDate(serverNow.data) : null
  const date = today && dateChoice && dateChoice >= today ? dateChoice : today
  const ship = ships.data?.find((s) => s.id === shipChoice) ?? ships.data?.[0] ?? null

  const availability = useAvailability(ship?.id ?? null, date, duration, date === today)
  const createBooking = useCreateBooking()
  const refreshSchedule = useRefreshSchedule()

  // The selection only counts while the current response still offers it, so a
  // slot that was taken or slipped into the past deselects itself on refresh.
  const slot =
    availability.data?.slots.find((s) => s.start === selectedStart && s.available) ?? null
  const canBook = slot !== null && pilotName.trim() !== '' && !createBooking.isPending

  // Changing what is being looked at clears the slot but keeps the pilot name.
  function changeView(change: () => void) {
    change()
    setSelectedStart(null)
    setNotice(null)
  }

  function selectSlot(picked: Slot) {
    setSelectedStart(picked.start === selectedStart ? null : picked.start)
    setNotice(null)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!canBook || !ship || !date) return

    createBooking.mutate(
      // The slot's own strings, exactly as the server sent them: no timestamp is built here.
      { shipId: ship.id, pilotName: pilotName.trim(), startTime: slot.start, endTime: slot.end },
      {
        onSuccess: (booking) => {
          setSelectedStart(null)
          setNotice({
            kind: 'success',
            text: `Booked ${ship.name} for ${booking.pilotName}: ${formatDate(date)}, ${formatRange(booking.startTime, booking.endTime)}.`,
          })
          refreshSchedule(ship.id, date)
        },
        onError: (error) => {
          setNotice({
            kind: 'error',
            text:
              error instanceof NoResponseError
                ? "We couldn't confirm whether this booking succeeded. The times below have been refreshed; check them before trying again."
                : errorMessage(error),
          })
          // A 409 means the grid is out of date; a lost response means we can't tell.
          refreshSchedule(ship.id, date)
        },
      },
    )
  }

  if (serverNow.isError) {
    return <ErrorState error={serverNow.error} onRetry={() => serverNow.refetch()} />
  }
  if (ships.isError) return <ErrorState error={ships.error} onRetry={() => ships.refetch()} />
  if (!ships.data || !today || !date) return <Skeleton label="Loading the fleet" />
  if (!ship) return <EmptyState title="No ships available" />

  return (
    <>
      <h1>Charter a ship</h1>

      <div className={styles.controls}>
        <label className={ui.field}>
          <span className={ui.label}>Ship</span>
          <select
            className={ui.input}
            value={ship.id}
            onChange={(e) => changeView(() => setShipChoice(Number(e.target.value)))}
          >
            {ships.data.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Date (Central)</span>
          <input
            type="date"
            className={ui.input}
            value={date}
            min={today}
            onChange={(e) => changeView(() => setDateChoice(e.target.value || null))}
          />
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Duration</span>
          <select
            className={ui.input}
            value={duration}
            onChange={(e) => changeView(() => setDuration(Number(e.target.value)))}
          >
            {DURATIONS.map((minutes) => (
              <option key={minutes} value={minutes}>
                {formatDuration(minutes)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Notice notice={notice} />

      <div className={styles.columns}>
        <section aria-labelledby="times-heading">
          <h2 id="times-heading">
            {ship.name} · {formatDate(date)}
          </h2>
          {availability.isError ? (
            <ErrorState error={availability.error} onRetry={() => availability.refetch()} />
          ) : !availability.data ? (
            <Skeleton rows={4} label="Loading start times" />
          ) : (
            <>
              <p className={styles.caption}>
                Last start {formatTime(availability.data.lastStart)} for a{' '}
                {formatDurationAdjective(duration)} charter (spaceport closes 10:00 PM CT). All
                times are spaceport time (CT).
              </p>
              <SlotGrid
                slots={availability.data.slots}
                selectedStart={slot?.start ?? null}
                onSelect={selectSlot}
              />
            </>
          )}
        </section>

        <form className={styles.panel} onSubmit={submit} aria-labelledby="book-heading">
          <h2 id="book-heading">Your charter</h2>
          {slot ? (
            <dl className={styles.summary}>
              <dt>Ship</dt>
              <dd>{ship.name}</dd>
              <dt>Date</dt>
              <dd>{formatDate(date)}</dd>
              <dt>Departs</dt>
              <dd>{formatTimeWithHint(slot.start)}</dd>
              <dt>Returns</dt>
              <dd>{formatTimeWithHint(slot.end)}</dd>
            </dl>
          ) : (
            <p className={styles.hint}>Pick an open start time to book it.</p>
          )}
          <label className={ui.field}>
            <span className={ui.label}>Pilot name</span>
            <input
              className={ui.input}
              value={pilotName}
              maxLength={100}
              autoComplete="off"
              onChange={(e) => setPilotName(e.target.value)}
            />
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={!canBook}>
            {createBooking.isPending ? 'Booking…' : 'Book charter'}
          </button>
        </form>
      </div>
    </>
  )
}
