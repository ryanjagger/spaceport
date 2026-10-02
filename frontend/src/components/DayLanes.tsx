import type { Booking, Ship, Slot } from '../api/client'
import { dayFraction, formatRange, formatTime, minutesFraction } from '../lib/time'
import styles from './DayLanes.module.css'
import { ui } from './ui'

const REFUEL_MINUTES = 30
const AXIS_LABELS = ['6 AM', '8 AM', '10 AM', '12 PM', '2 PM', '4 PM', '6 PM', '8 PM', '10 PM']

const percent = (fraction: number) => `${fraction * 100}%`

interface Props {
  ships: Ship[]
  /** Active bookings for the day, all ships. */
  bookings: Booking[]
  /** Open start times per ship id at the chosen duration; missing while loading or on error. */
  openCounts: Map<number, number>
  selectedShipId: number
  onSelectShip: (shipId: number) => void
  /** The start time picked on the selected ship, drawn on its lane. */
  pick: Slot | null
  /** The server's clock, when the day shown is today and the spaceport is open. */
  now: string | null
}

/**
 * The fleet's day, one lane per ship on a shared 6 AM to 10 PM scale. The lanes are a
 * radio group: choosing one chooses the ship whose start times are listed below.
 */
export function DayLanes({
  ships,
  bookings,
  openCounts,
  selectedShipId,
  onSelectShip,
  pick,
  now,
}: Props) {
  return (
    <div className={styles.lanes}>
      <div className={styles.axis} aria-hidden="true">
        {AXIS_LABELS.map((label, i) => (
          <span key={label} style={{ left: percent(i / (AXIS_LABELS.length - 1)) }}>
            {label}
          </span>
        ))}
      </div>
      <div role="radiogroup" aria-label="Ship">
        {ships.map((ship) => {
          const forShip = bookings.filter((booking) => booking.shipId === ship.id)
          const open = openCounts.get(ship.id)
          const selected = ship.id === selectedShipId
          return (
            <label key={ship.id} className={styles.lane}>
              <span className={styles.who}>
                <input
                  type="radio"
                  name="ship"
                  checked={selected}
                  onChange={() => onSelectShip(ship.id)}
                />
                <span className={styles.name}>{ship.name}</span>
                <span className={styles.count}>
                  {open === undefined
                    ? ''
                    : open === 0
                      ? 'No open starts'
                      : `${open} open ${open === 1 ? 'start' : 'starts'}`}
                </span>
              </span>
              {/* The same facts as the drawing, for anyone who can't see it. */}
              <span className={ui.visuallyHidden}>
                {forShip.length === 0
                  ? 'No bookings.'
                  : `Booked ${forShip.map((b) => formatRange(b.startTime, b.endTime)).join(', ')}, each followed by a 30-minute refuel gap.`}
              </span>
              <span className={styles.track} aria-hidden="true">
                {forShip.map((booking) => {
                  const start = dayFraction(booking.startTime)
                  const end = dayFraction(booking.endTime)
                  // The refuel gap stops at closing time: nothing can be booked after it.
                  const refuel = Math.min(minutesFraction(REFUEL_MINUTES), 1 - end)
                  return (
                    <span key={booking.id}>
                      <span
                        className={styles.block}
                        style={{ left: percent(start), width: percent(end - start) }}
                        title={`${booking.pilotName}, ${formatRange(booking.startTime, booking.endTime)}`}
                      >
                        <span className={styles.pilot}>{booking.pilotName}</span>
                      </span>
                      {refuel > 0 && (
                        <span
                          className={styles.refuel}
                          style={{ left: percent(end), width: percent(refuel) }}
                        />
                      )}
                    </span>
                  )
                })}
                {selected && pick && (
                  <span
                    className={styles.pick}
                    style={{
                      left: percent(dayFraction(pick.start)),
                      width: percent(dayFraction(pick.end) - dayFraction(pick.start)),
                    }}
                  >
                    <span className={`${styles.pilot} ${styles.pickLabel}`}>
                      {formatTime(pick.start)}
                    </span>
                  </span>
                )}
                {now && <span className={styles.now} style={{ left: percent(dayFraction(now)) }} />}
              </span>
            </label>
          )
        })}
      </div>
      <p className={styles.legend}>
        <span>
          <span className={styles.legendBlock} /> Booked
        </span>
        <span>
          <span className={styles.legendRefuel} /> Refuel time, 30 minutes after each charter
        </span>
        <span>
          <span className={styles.legendPick} /> Your pick
        </span>
        {now && (
          <span>
            <span className={styles.legendNow} /> Now
          </span>
        )}
      </p>
    </div>
  )
}
