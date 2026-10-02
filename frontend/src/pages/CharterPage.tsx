import { CalendarBlankIcon, CaretDownIcon, RocketLaunchIcon } from '@phosphor-icons/react'
import { useRef, useState, type FormEvent } from 'react'
import { NoResponseError, type Slot } from '../api/client'
import {
  useBookings,
  useCreateBooking,
  useFleetAvailability,
  useRefreshSchedule,
  useServerNow,
  useShips,
} from '../api/hooks'
import { DayLanes } from '../components/DayLanes'
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
  addDays,
  centralDate,
  formatDate,
  formatDuration,
  formatDurationAdjective,
  formatRange,
  formatTime,
  formatTimeWithHint,
  isWithinOperatingDay,
  withLocalHint,
} from '../lib/time'
import styles from './CharterPage.module.css'

const DURATIONS = Array.from({ length: 16 }, (_, i) => (i + 1) * 30) // 30 minutes to 8 hours

// Wide enough for the charter panel to sit beside the start times (see the stylesheet).
const SIDE_BY_SIDE = '(min-width: 861px)'

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

  // Every ship's answer for the day, so the lanes can say how many starts each has open.
  const shipIds = ships.data?.map((s) => s.id) ?? []
  const fleet = useFleetAvailability(shipIds, date, duration, date === today)
  const availability = fleet[ship ? shipIds.indexOf(ship.id) : -1]
  const bookings = useBookings(date, false, date === today)
  const createBooking = useCreateBooking()
  const refreshSchedule = useRefreshSchedule()

  const openCounts = new Map<number, number>()
  fleet.forEach((answer, i) => {
    if (answer.data) openCounts.set(shipIds[i], answer.data.slots.filter((s) => s.available).length)
  })

  // The selection only counts while the current response still offers it, so a
  // slot that was taken or slipped into the past deselects itself on refresh.
  const slot =
    availability?.data?.slots.find((s) => s.start === selectedStart && s.available) ?? null
  const hasName = pilotName.trim() !== ''
  const canBook = slot !== null && hasName && !createBooking.isPending
  // A pick the latest response no longer offers: named in the panel, not dropped silently.
  const lostStart = selectedStart !== null && availability?.data && !slot ? selectedStart : null
  const noneOpen = availability?.data?.slots.every((s) => !s.available) ?? false

  const dayHeading = useRef<HTMLHeadingElement>(null)
  const pilotInput = useRef<HTMLInputElement>(null)

  // Changing what is being looked at clears the slot but keeps the pilot name.
  function changeView(change: () => void) {
    change()
    setSelectedStart(null)
    setNotice(null)
  }

  // The button that calls this goes away once the new day has open times, so focus
  // moves to the heading that names the day now showing.
  function tryNextDay(from: string) {
    changeView(() => setDateChoice(addDays(from, 1)))
    dayHeading.current?.focus()
  }

  function selectSlot(picked: Slot) {
    const picking = picked.start !== selectedStart
    setSelectedStart(picking ? picked.start : null)
    setNotice(null)
    // With the panel alongside, the next thing to do is name the pilot: go straight
    // there instead of tabbing past every remaining start time. On a phone this would
    // throw the keyboard up over the times, so the pinned bar waits to be tapped.
    if (picking && !hasName && window.matchMedia(SIDE_BY_SIDE).matches) {
      pilotInput.current?.focus()
    }
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
                ? "We couldn't confirm whether this booking succeeded. The times have been refreshed; check them before trying again."
                : errorMessage(error),
          })
          // A 409 means the times are out of date; a lost response means we can't tell.
          refreshSchedule(ship.id, date)
        },
      },
    )
  }

  if (serverNow.isError) {
    return <ErrorState error={serverNow.error} onRetry={() => serverNow.refetch()} />
  }
  if (ships.isError) return <ErrorState error={ships.error} onRetry={() => ships.refetch()} />
  if (!ships.data || !serverNow.data || !today || !date) {
    return <Skeleton label="Loading the fleet" />
  }
  if (!ship || !availability) return <EmptyState title="No ships available" />

  const departs = slot && withLocalHint(slot.start)

  return (
    <>
      <h1>Charter a ship</h1>
      <p className={styles.lead}>
        Welcome, dispatcher. Pick a ship, a start time and a pilot. Every time is spaceport time
        (CT).
      </p>

      <div className={styles.controls}>
        <label className={ui.field}>
          <span className={ui.label}>Date (Central)</span>
          <span className={ui.withIcon}>
            <input
              type="date"
              className={`${ui.input} ${ui.date}`}
              value={date}
              min={today}
              onChange={(e) => changeView(() => setDateChoice(e.target.value || null))}
            />
            <CalendarBlankIcon
              className={`${ui.fieldIcon} ${ui.dateIcon}`}
              size={16}
              weight="bold"
              aria-hidden
            />
          </span>
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Duration</span>
          <span className={ui.withIcon}>
            <select
              className={`${ui.input} ${ui.select}`}
              value={duration}
              onChange={(e) => changeView(() => setDuration(Number(e.target.value)))}
            >
              {DURATIONS.map((minutes) => (
                <option key={minutes} value={minutes}>
                  {formatDuration(minutes)}
                </option>
              ))}
            </select>
            <CaretDownIcon className={ui.fieldIcon} size={16} weight="bold" aria-hidden />
          </span>
        </label>
      </div>

      <section className={styles.fleet} aria-labelledby="day-heading">
        <h2 id="day-heading" ref={dayHeading} tabIndex={-1}>
          The fleet on {formatDate(date)}
        </h2>
        {bookings.isError ? (
          <ErrorState error={bookings.error} onRetry={() => bookings.refetch()} />
        ) : !bookings.data ? (
          <Skeleton rows={5} label="Loading the day" />
        ) : (
          <DayLanes
            ships={ships.data}
            bookings={bookings.data}
            openCounts={openCounts}
            selectedShipId={ship.id}
            onSelectShip={(id) => changeView(() => setShipChoice(id))}
            pick={slot}
            now={date === today && isWithinOperatingDay(serverNow.data) ? serverNow.data : null}
          />
        )}
      </section>

      <div className={styles.columns}>
        <section aria-labelledby="times-heading">
          <h2 id="times-heading">Start times for {ship.name}</h2>
          {availability.isError ? (
            <ErrorState error={availability.error} onRetry={() => availability.refetch()} />
          ) : !availability.data ? (
            <Skeleton rows={4} label="Loading start times" />
          ) : (
            <>
              <p className={styles.caption}>
                The last {formatDurationAdjective(duration)} start is{' '}
                {formatTime(availability.data.lastStart)}: the spaceport closes at 10:00 PM CT, and
                each charter needs 30 minutes clear on either side to refuel.
              </p>
              {noneOpen && (
                <div className={styles.noneOpen}>
                  <p>
                    No {formatDurationAdjective(duration)} start times{' '}
                    {date === today ? 'are left today' : 'are open on this day'} for {ship.name}.
                  </p>
                  <button type="button" className={ui.button} onClick={() => tryNextDay(date)}>
                    Try the next day
                  </button>
                </div>
              )}
              <SlotGrid
                slots={availability.data.slots}
                selectedStart={slot?.start ?? null}
                onSelect={selectSlot}
              />
            </>
          )}
        </section>

        <form
          className={styles.panel}
          data-picked={slot ? '' : undefined}
          onSubmit={submit}
          aria-labelledby="book-heading"
        >
          <h2 id="book-heading">Your charter</h2>
          <Notice notice={notice} />
          {slot && departs && (
            <>
              <div className={styles.pick}>
                <p className={styles.departs}>
                  <span className={styles.departsLabel}>Departs</span>
                  {departs.central}
                </p>
                {departs.local && <p className={styles.hint}>{departs.local}</p>}
                <dl className={styles.summary}>
                  <dt>Ship</dt>
                  <dd>{ship.name}</dd>
                  <dt>Date</dt>
                  <dd>{formatDate(date)}</dd>
                  <dt>Returns</dt>
                  <dd>{formatTimeWithHint(slot.end)}</dd>
                  <dt>Duration</dt>
                  <dd>{formatDuration(duration)}</dd>
                </dl>
              </div>
              {/* The same pick on one line, for the bar pinned to the bottom of a phone. */}
              <p className={styles.compact}>
                <strong>{ship.name}</strong> {formatRange(slot.start, slot.end)}
              </p>
            </>
          )}
          {/* Always in the page, so a pick that stops being available is announced. */}
          <div role="status">
            {!slot && (
              <p className={styles.hint}>
                {lostStart
                  ? `${formatTime(lostStart)} CT is no longer available. Pick another start time.`
                  : 'Pick an open start time to book it.'}
              </p>
            )}
          </div>
          <label className={`${ui.field} ${styles.pilot}`}>
            <span className={ui.label}>Pilot name</span>
            <input
              ref={pilotInput}
              className={ui.input}
              value={pilotName}
              maxLength={100}
              autoComplete="off"
              required
              aria-describedby="pilot-hint"
              onChange={(e) => setPilotName(e.target.value)}
            />
          </label>
          <p id="pilot-hint" className={styles.pilotHint}>
            {slot && !hasName ? 'Enter a pilot name to book.' : ''}
          </p>
          <button
            type="submit"
            className={`${ui.button} ${ui.primary} ${styles.book}`}
            disabled={!canBook}
          >
            <RocketLaunchIcon size={18} weight="bold" aria-hidden />
            {createBooking.isPending ? 'Booking…' : 'Book charter'}
          </button>
        </form>
      </div>
    </>
  )
}
