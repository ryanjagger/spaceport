/**
 * The only place the app formats or reasons about time.
 *
 * Every time shown is spaceport time (America/Chicago), for every user, wherever
 * their browser is. Calendar dates travel as plain 'YYYY-MM-DD' strings; instants
 * travel as the ISO strings the API returned and are never rebuilt here.
 */

export const SPACEPORT_TZ = 'America/Chicago'

const MINUTES_OPEN = 6 * 60
const MINUTES_CLOSE = 22 * 60

type Zone = string | undefined // undefined = the browser's own time zone

// Building an Intl.DateTimeFormat is slow next to using one, and a slot grid formats
// about 150 times per render, so each format is built once per zone and reused.
function perZone(options: Intl.DateTimeFormatOptions) {
  const built = new Map<Zone, Intl.DateTimeFormat>()
  return (timeZone: Zone) => {
    let format = built.get(timeZone)
    if (!format) {
      format = new Intl.DateTimeFormat('en-US', { ...options, timeZone })
      built.set(timeZone, format)
    }
    return format
  }
}

const wallClockFormat = perZone({
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
const clockTimeFormat = perZone({ hour: 'numeric', minute: '2-digit' })
const weekdayFormat = perZone({ weekday: 'short' })

function wallClock(iso: string, timeZone: Zone) {
  const parts = wallClockFormat(timeZone).formatToParts(new Date(iso))
  const get = (type: string) => parts.find((p) => p.type === type)!.value
  return {
    date: `${get('year')}-${get('month')}-${get('day')}`,
    minutes: Number(get('hour')) * 60 + Number(get('minute')),
  }
}

function clockTime(iso: string, timeZone: Zone): string {
  return clockTimeFormat(timeZone).format(new Date(iso))
}

function weekday(iso: string, timeZone: Zone): string {
  return weekdayFormat(timeZone).format(new Date(iso))
}

/** The Central calendar date of an instant, e.g. "today" from the server's clock. */
export function centralDate(iso: string): string {
  return wallClock(iso, SPACEPORT_TZ).date
}

/** "8:00 AM" in spaceport time. */
export function formatTime(iso: string): string {
  return clockTime(iso, SPACEPORT_TZ)
}

/** "8:00 AM – 9:00 AM CT" */
export function formatRange(start: string, end: string): string {
  return `${formatTime(start)} – ${formatTime(end)} CT`
}

/**
 * A time for display, plus the viewer's own time when their browser is not on
 * Central: { central: "8:00 AM CT", local: "3:00 PM your time" }. When the two
 * fall on different dates both get a weekday: "Fri 9:00 PM CT" / "Sat 11:00 AM your time".
 */
export function withLocalHint(iso: string): { central: string; local: string | null } {
  const here = wallClock(iso, undefined)
  const there = wallClock(iso, SPACEPORT_TZ)
  if (here.date === there.date && here.minutes === there.minutes) {
    return { central: `${formatTime(iso)} CT`, local: null }
  }
  if (here.date === there.date) {
    return { central: `${formatTime(iso)} CT`, local: `${clockTime(iso, undefined)} your time` }
  }
  return {
    central: `${weekday(iso, SPACEPORT_TZ)} ${formatTime(iso)} CT`,
    local: `${weekday(iso, undefined)} ${clockTime(iso, undefined)} your time`,
  }
}

/** "8:00 AM CT (3:00 PM your time)" */
export function formatTimeWithHint(iso: string): string {
  const { central, local } = withLocalHint(iso)
  return local ? `${central} (${local})` : central
}

/** Where an instant sits on the 6:00 AM–10:00 PM axis, from 0 to 1 (clamped). */
export function dayFraction(iso: string): number {
  const { minutes } = wallClock(iso, SPACEPORT_TZ)
  const fraction = (minutes - MINUTES_OPEN) / (MINUTES_CLOSE - MINUTES_OPEN)
  return Math.min(1, Math.max(0, fraction))
}

/** A span of minutes as a fraction of the operating day. */
export function minutesFraction(minutes: number): number {
  return minutes / (MINUTES_CLOSE - MINUTES_OPEN)
}

// Plain-date helpers. A date string is pinned to noon UTC so that no time zone,
// the browser's included, can push it onto a neighbouring day.
function atNoonUtc(date: string): Date {
  return new Date(`${date}T12:00:00Z`)
}

const dateFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC',
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

/** "Fri, Oct 2, 2026" */
export function formatDate(date: string): string {
  return dateFormat.format(atNoonUtc(date))
}

export function addDays(date: string, days: number): string {
  const moved = atNoonUtc(date)
  moved.setUTCDate(moved.getUTCDate() + days)
  return moved.toISOString().slice(0, 10)
}

/** "30 minutes", "1 hour", "1.5 hours" */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} minutes`
  const hours = minutes / 60
  return hours === 1 ? '1 hour' : `${hours} hours`
}

/** "30-minute", "1-hour", "1.5-hour" — as in "a 1-hour charter". */
export function formatDurationAdjective(minutes: number): string {
  return minutes < 60 ? `${minutes}-minute` : `${minutes / 60}-hour`
}

/** Whether one instant is strictly after another (e.g. a booking's start vs the server's now). */
export function isAfter(iso: string, otherIso: string): boolean {
  return new Date(iso).getTime() > new Date(otherIso).getTime()
}
