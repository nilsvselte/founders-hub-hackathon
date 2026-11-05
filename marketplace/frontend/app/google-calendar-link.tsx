import { googleCalendarUrl } from "./google-calendar";
import type { CalendarBooking } from "./google-calendar";

export function GoogleCalendarLink({ booking }: { booking: CalendarBooking }) {
  const href = googleCalendarUrl(booking);
  if (!href) return null;

  return (
    <a
      className="button secondary booking-calendar"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Add to Google Calendar: ${booking.offer?.room_name} (opens in a new tab)`}
    >
      Add to Google Calendar <span aria-hidden="true">↗</span>
    </a>
  );
}
