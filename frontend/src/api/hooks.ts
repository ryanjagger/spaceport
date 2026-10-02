import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { centralDate } from '../lib/time'
import { api, type Booking } from './client'

const MINUTE = 60_000

/** The server's clock. "Today" always comes from here, never from the device. */
export function useServerNow() {
  return useQuery({
    queryKey: ['time'],
    queryFn: api.serverTime,
    select: (time) => time.serverNow,
    refetchInterval: MINUTE,
  })
}

export function useShips() {
  return useQuery({ queryKey: ['ships'], queryFn: api.ships, staleTime: 5 * MINUTE })
}

export function useAvailability(
  shipId: number | null,
  date: string | null,
  duration: number,
  isToday: boolean,
) {
  return useQuery({
    queryKey: ['availability', shipId, date, duration],
    queryFn: () => api.availability(shipId!, date!, duration),
    enabled: shipId !== null && date !== null,
    // Today's slots go stale as time passes; other days only change when someone books.
    refetchInterval: isToday ? MINUTE : false,
  })
}

export function useBookings(date: string | null, includeCancelled: boolean) {
  return useQuery({
    queryKey: ['bookings', date, date, includeCancelled],
    queryFn: () => api.bookings(date!, includeCancelled),
    enabled: date !== null,
  })
}

export function useNearestDates(date: string | null, includeCancelled: boolean, enabled: boolean) {
  return useQuery({
    queryKey: ['nearest-dates', date, includeCancelled],
    queryFn: () => api.nearestDates(date!, includeCancelled),
    enabled: enabled && date !== null,
  })
}

/**
 * Refetch everything a booking or cancellation on this ship and day can change:
 * its availability at every duration, the bookings lists and the nearest dates.
 * Also used after a 409 or a lost response, when what we show may be out of date.
 */
export function useRefreshSchedule() {
  const queryClient = useQueryClient()
  return (shipId: number, date: string) =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['availability', shipId, date] }),
      queryClient.invalidateQueries({ queryKey: ['bookings'] }),
      queryClient.invalidateQueries({ queryKey: ['nearest-dates'] }),
      queryClient.invalidateQueries({ queryKey: ['time'] }),
    ])
}

// Neither mutation is ever retried automatically (see main.tsx): a retry after a
// lost response could book twice or turn a success into a confusing 409.
export function useCreateBooking() {
  return useMutation({ mutationFn: api.createBooking })
}

export function useCancelBooking() {
  return useMutation({ mutationFn: (booking: Booking) => api.cancelBooking(booking.id) })
}

export function bookingDate(booking: Booking): string {
  return centralDate(booking.startTime)
}
