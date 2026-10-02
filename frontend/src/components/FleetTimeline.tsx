import type { Booking, Ship } from '../api/client'
import { dayFraction, formatRange, minutesFraction } from '../lib/time'
import styles from './FleetTimeline.module.css'

const REFUEL_MINUTES = 30
const AXIS_LABELS = ['6 AM', '8 AM', '10 AM', '12 PM', '2 PM', '4 PM', '6 PM', '8 PM', '10 PM']

const percent = (fraction: number) => `${fraction * 100}%`

interface Props {
  ships: Ship[]
  /** Active bookings only: a cancelled booking must never cover its replacement. */
  bookings: Booking[]
  onOpen: (booking: Booking, opener: HTMLElement) => void
}

export function FleetTimeline({ ships, bookings, onOpen }: Props) {
  return (
    <div className={styles.timeline}>
      <div className={styles.axis} aria-hidden="true">
        {AXIS_LABELS.map((label, i) => (
          <span key={label} style={{ left: percent(i / (AXIS_LABELS.length - 1)) }}>
            {label}
          </span>
        ))}
      </div>
      {ships.map((ship) => (
        <div key={ship.id} className={styles.row}>
          <p className={styles.ship}>{ship.name}</p>
          <div className={styles.track}>
            {bookings
              .filter((booking) => booking.shipId === ship.id)
              .map((booking) => {
                const start = dayFraction(booking.startTime)
                const end = dayFraction(booking.endTime)
                // The refuel strip stops at closing time: nothing can be booked after it.
                const refuel = Math.min(minutesFraction(REFUEL_MINUTES), 1 - end)
                const times = formatRange(booking.startTime, booking.endTime)
                return (
                  <div key={booking.id}>
                    <button
                      type="button"
                      className={styles.block}
                      style={{ left: percent(start), width: percent(end - start) }}
                      title={`${booking.pilotName}, ${times}`}
                      aria-label={`${ship.name}: ${booking.pilotName}, ${times}`}
                      onClick={(e) => onOpen(booking, e.currentTarget)}
                    >
                      <span className={styles.pilot}>{booking.pilotName}</span>
                      <span className={styles.times}>{times}</span>
                    </button>
                    {refuel > 0 && (
                      <span
                        className={styles.refuel}
                        style={{ left: percent(end), width: percent(refuel) }}
                        title="Refuel: 30 minutes"
                      />
                    )}
                  </div>
                )
              })}
          </div>
        </div>
      ))}
      <p className={styles.legend}>
        <span className={styles.legendBlock} /> Booked
        <span className={styles.legendRefuel} /> Refuel time, 30 minutes after each charter
      </p>
    </div>
  )
}
