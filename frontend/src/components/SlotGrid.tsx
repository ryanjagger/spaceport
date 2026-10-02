import type { Slot } from '../api/client'
import { formatTime, withLocalHint } from '../lib/time'
import styles from './SlotGrid.module.css'

// Shown as text on the button, not in a tooltip, so touch and keyboard users see it.
const REASON_LABEL = { past: 'Past', booked: 'Booked', buffer: 'Refuel' } as const

interface Props {
  slots: Slot[]
  selectedStart: string | null
  onSelect: (slot: Slot) => void
}

export function SlotGrid({ slots, selectedStart, onSelect }: Props) {
  return (
    <ul className={styles.grid} aria-label="Start times">
      {slots.map((slot) => {
        const { local } = withLocalHint(slot.start)
        const selected = slot.start === selectedStart
        const className = [
          styles.slot,
          selected && styles.selected,
          slot.reason && styles[slot.reason],
        ]
          .filter(Boolean)
          .join(' ')

        return (
          <li key={slot.start}>
            <button
              type="button"
              className={className}
              disabled={!slot.available}
              aria-pressed={slot.available ? selected : undefined}
              onClick={() => onSelect(slot)}
            >
              <span className={styles.time}>{formatTime(slot.start)}</span>
              <span className={styles.status}>
                {slot.reason ? REASON_LABEL[slot.reason] : `to ${formatTime(slot.end)}`}
              </span>
              {local && <span className={styles.local}>{local}</span>}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
