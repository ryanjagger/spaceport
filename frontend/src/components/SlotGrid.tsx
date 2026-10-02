import type { Slot } from '../api/client'
import { centralMinutes, formatHour, formatTime, withLocalHint } from '../lib/time'
import styles from './SlotGrid.module.css'

// Shown as text on the button, not in a tooltip, so touch and keyboard users see it.
// The buffer reason covers both sides of a booking: a start inside the refuel gap after
// one, and a start whose charter would end too close to the next. Either way the time
// is needed for refuelling, so the label has to read true in both places.
const REASON_LABEL = { past: 'Past', booked: 'Booked', buffer: 'Refuel time' } as const

const PERIODS = [
  { label: 'Morning', from: 6 * 60, to: 12 * 60 },
  { label: 'Afternoon', from: 12 * 60, to: 17 * 60 },
  { label: 'Evening', from: 17 * 60, to: 22 * 60 },
]

interface Props {
  slots: Slot[]
  selectedStart: string | null
  onSelect: (slot: Slot) => void
}

/** Start times by hour, :00 beside :30. Times that have passed are summed up, not listed. */
export function SlotGrid({ slots, selectedStart, onSelect }: Props) {
  const timed = slots.map((slot) => ({ slot, minutes: centralMinutes(slot.start) }))
  const upcoming = timed.filter(({ slot }) => slot.reason !== 'past')
  if (upcoming.length === 0) return null

  return (
    <>
      {upcoming.length < timed.length && (
        <p className={styles.passed}>
          Start times before {formatTime(upcoming[0].slot.start)} have passed.
        </p>
      )}
      <div className={styles.periods}>
        {PERIODS.map((period) => {
          const inPeriod = upcoming.filter(
            ({ minutes }) => minutes >= period.from && minutes < period.to,
          )
          if (inPeriod.length === 0) return null
          const hours = [...new Set(inPeriod.map(({ minutes }) => minutes - (minutes % 60)))]

          return (
            <section key={period.label} aria-label={`${period.label} start times`}>
              <h3 className={styles.period}>{period.label}</h3>
              <ul className={styles.hours}>
                {hours.map((hour) => (
                  <li key={hour} className={styles.hour}>
                    <span className={styles.hourLabel} aria-hidden="true">
                      {formatHour(hour)}
                    </span>
                    {inPeriod
                      .filter(({ minutes }) => minutes - (minutes % 60) === hour)
                      .map(({ slot, minutes }) => {
                        const { local } = withLocalHint(slot.start)
                        const selected = slot.start === selectedStart
                        const className = [
                          styles.slot,
                          minutes % 60 !== 0 && styles.half,
                          selected && styles.selected,
                          slot.reason && styles[slot.reason],
                        ]
                          .filter(Boolean)
                          .join(' ')

                        return (
                          <button
                            key={slot.start}
                            type="button"
                            className={className}
                            disabled={!slot.available}
                            aria-pressed={slot.available ? selected : undefined}
                            onClick={() => onSelect(slot)}
                          >
                            <span className={styles.time}>{formatTime(slot.start)}</span>
                            <span className={styles.status}>
                              {slot.reason
                                ? REASON_LABEL[slot.reason]
                                : `to ${formatTime(slot.end)}`}
                            </span>
                            {local && <span className={styles.local}>{local}</span>}
                          </button>
                        )
                      })}
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
      </div>
    </>
  )
}
