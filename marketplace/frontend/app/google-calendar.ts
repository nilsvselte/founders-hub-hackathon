export type CalendarOffer = {
  room_name: string;
  room_venue?: string | null;
  room_city?: string | null;
  start_at: string;
  end_at: string;
};

export type CalendarBooking = {
  status: string;
  offer: CalendarOffer | null;
  booking_reference: string | null;
};

function calendarTimestamp(date: Date) {
  return date.toISOString().replace(/[-:]|\.\d{3}/g, "");
}

export function googleCalendarUrl({ status, offer, booking_reference }: CalendarBooking) {
  if (status !== "confirmed" || !offer) return null;

  const start = new Date(offer.start_at);
  const end = new Date(offer.end_at);
  if (!(end.getTime() > start.getTime())) return null;

  const url = new URL("https://calendar.google.com/calendar/r/eventedit");
  url.search = new URLSearchParams({
    action: "TEMPLATE",
    text: `${offer.room_name} · standbyroom`,
    dates: `${calendarTimestamp(start)}/${calendarTimestamp(end)}`,
    stz: "Europe/Oslo",
    etz: "Europe/Oslo",
    location: [offer.room_name, offer.room_venue, offer.room_city].filter(Boolean).join(", "),
    details: booking_reference ? `Booked via standbyroom.\nBooking reference: ${booking_reference}` : "Booked via standbyroom.",
  }).toString();
  return url.toString();
}
