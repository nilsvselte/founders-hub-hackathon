export type Span = { start_at: string; end_at: string };
export type Occupancy = { occupied: boolean; changed_at: string };

/** A booking or block counts as a ghost once the room has been empty this long. */
export const GHOST_AFTER_MS = 10 * 60_000;

/** Minutes a current booking or block has sat empty, or null below the warning threshold. */
export function ghostMinutes(booking: Span | null, sensor: Occupancy | null | undefined, now: number) {
  // Empty since the later of the sensor change and the booking start.
  const emptySince = booking && sensor && !sensor.occupied
    ? Math.max(Date.parse(sensor.changed_at), Date.parse(booking.start_at)) : null;
  return emptySince !== null && now - emptySince >= GHOST_AFTER_MS
    ? Math.floor((now - emptySince) / 60_000) : null;
}
