const osloClock = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
export const dayMs = 86_400_000;

export function osloDateTime(instant: number) {
  const parts = Object.fromEntries(osloClock.formatToParts(instant).map(({ type, value }) => [type, value]));
  return { date: `${parts.year}-${parts.month}-${parts.day}`, time: `${parts.hour}:${parts.minute}` };
}

export function osloInstant({ date, time }: { date: string; time: string }) {
  if (!date || !time) return null;
  const wall = Date.parse(`${date}T${time}:00Z`);
  if (!Number.isFinite(wall)) return null;

  // Check both possible offsets around a clock change. An ambiguous time uses its first occurrence.
  for (const sample of [wall - dayMs, wall + dayMs]) {
    const local = osloDateTime(sample);
    const offset = Date.parse(`${local.date}T${local.time}:00Z`) - sample;
    const instant = wall - offset;
    const roundTrip = osloDateTime(instant);
    if (roundTrip.date === date && roundTrip.time === time) return new Date(instant);
  }
  return null;
}

export function upcomingRoomStart(date: string | undefined, now = Date.now()) {
  if (!date) return null;
  const lateMorning = osloInstant({ date, time: "11:00" });
  if (lateMorning && lateMorning.getTime() > now) return lateMorning;
  const soon = now + 30 * 60_000;
  return osloDateTime(soon).date === date ? new Date(soon) : null;
}
