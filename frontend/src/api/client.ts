export interface Ship {
  id: number
  name: string
}

export interface Booking {
  id: number
  shipId: number
  pilotName: string
  startTime: string
  endTime: string
  status: 'active' | 'cancelled'
  createdAt: string
  cancelledAt: string | null
}

export interface Slot {
  start: string
  end: string
  available: boolean
  reason: 'past' | 'booked' | 'buffer' | null
}

export interface Availability {
  shipId: number
  date: string
  timezone: string
  serverNow: string
  durationMinutes: number
  lastStart: string
  slots: Slot[]
}

export interface NearestDates {
  previous: string | null
  next: string | null
}

export interface ServerTime {
  serverNow: string
  timezone: string
}

export interface NewBooking {
  shipId: number
  pilotName: string
  startTime: string
  endTime: string
}

/** The API answered with an error. `message` is safe to show as-is. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

/** No answer at all (offline, timeout): we don't know whether the request took effect. */
export class NoResponseError extends Error {
  constructor() {
    super('The spaceport could not be reached. Check your connection and try again.')
  }
}

const GENERIC_MESSAGE = 'Something went wrong. Try again.'
const TIMEOUT_MS = 15_000

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, { ...init, signal: AbortSignal.timeout(TIMEOUT_MS) })
  } catch {
    throw new NoResponseError()
  }

  // A proxy error page is not JSON; never surface it or a raw status code.
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    throw new ApiError(response.status, error?.code ?? 'unknown', error?.message ?? GENERIC_MESSAGE)
  }
  if (body === null) throw new ApiError(response.status, 'unknown', GENERIC_MESSAGE)
  return body as T
}

function query(params: Record<string, string | number | boolean>): string {
  return new URLSearchParams(
    Object.entries(params).map(([key, value]) => [key, String(value)]),
  ).toString()
}

export const api = {
  serverTime: () => request<ServerTime>('/time'),
  ships: () => request<Ship[]>('/ships'),
  availability: (shipId: number, date: string, durationMinutes: number) =>
    request<Availability>(`/ships/${shipId}/availability?${query({ date, durationMinutes })}`),
  bookings: (date: string, includeCancelled: boolean) =>
    request<Booking[]>(`/bookings?${query({ from: date, to: date, includeCancelled })}`),
  nearestDates: (date: string, includeCancelled: boolean) =>
    request<NearestDates>(`/bookings/nearest-dates?${query({ date, includeCancelled })}`),
  createBooking: (booking: NewBooking) =>
    request<Booking>('/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(booking),
    }),
  cancelBooking: (id: number) => request<Booking>(`/bookings/${id}`, { method: 'DELETE' }),
}
