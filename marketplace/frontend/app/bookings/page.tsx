"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAccount } from "../account";
import { GoogleCalendarLink } from "../google-calendar-link";
import type { CalendarOffer } from "../google-calendar";
import { api, money } from "../market";

type Booking = {
  id: string;
  room_name: string | null;
  status: "waiting" | "offered" | "confirmed" | "expired";
  booking_reference: string | null;
  earliest_start: string;
  latest_end: string;
  duration_minutes: number;
  party_size: number;
  offer: (CalendarOffer & { price_ore: number }) | null;
};

const labels = { waiting: "On standby", offered: "Offer ready", confirmed: "Confirmed", expired: "Expired" };
const date = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});
const time = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit" });

export default function BookingsPage() {
  const { account, loading } = useAccount();
  const renterId = account?.role === "renter" ? account.id : undefined;
  const [result, setResult] = useState<{ owner: string; rows?: Booking[]; error?: string }>();

  useEffect(() => {
    if (!renterId) return;
    const controller = new AbortController();
    api<Booking[]>("standby-requests", { signal: controller.signal })
      .then((rows) => { if (!controller.signal.aborted) setResult({ owner: renterId, rows }); })
      .catch((failure) => {
        if (!controller.signal.aborted) setResult({
          owner: renterId,
          error: failure instanceof Error ? failure.message : "Couldn’t load your bookings.",
        });
      });
    return () => controller.abort();
  }, [renterId]);

  const current = result && result.owner === renterId ? result : undefined;

  return (
    <main className="booking-page">
      <p className="identity-kicker">Your account</p>
      <h1>My bookings</h1>
      <p className="identity-intro">Track standby requests and confirmed reservations. <Link href="/account/preferences">Your preferences</Link></p>
      {loading ? <p role="status">Checking your account…</p> : !account ? (
        <p><Link className="identity-primary" href="/sign-in?next=%2Fbookings">Sign in to see your bookings</Link></p>
      ) : account.role === "host" ? (
        <p><Link className="identity-primary" href="/host">Go to your host dashboard</Link></p>
      ) : !current ? <p role="status">Loading your bookings…</p> : current.error ? (
        <p className="identity-error" role="alert">{current.error}</p>
      ) : current.rows?.length ? (
        <ul className="booking-list">
          {current.rows.map((booking) => (
            <li key={booking.id}>
              <Link className="booking-row" href={`/bookings/${booking.id}`}>
                <div className="booking-row-main">
                  <span className={`booking-status booking-status-${booking.status}`}>{labels[booking.status]}</span>
                  <h2>{booking.offer?.room_name ?? booking.room_name ?? "Flexible room request"}</h2>
                  <p>{booking.offer
                    ? `${date.format(new Date(booking.offer.start_at))}–${time.format(new Date(booking.offer.end_at))} Oslo time`
                    : `${date.format(new Date(booking.earliest_start))} Oslo time · ${booking.duration_minutes} min · ${booking.party_size} guests`}</p>
                  {booking.booking_reference && <p className="booking-reference">{booking.booking_reference}</p>}
                </div>
                <div className="booking-row-tail">
                  {booking.offer && <strong>{money(booking.offer.price_ore)}</strong>}
                  <span aria-hidden="true">↗</span>
                </div>
              </Link>
              <GoogleCalendarLink booking={booking} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="booking-empty">
          <h2>No bookings yet</h2>
          <p>When you request a room, its status will show up here.</p>
          <Link className="identity-primary" href="/">Browse rooms <span aria-hidden="true">→</span></Link>
        </div>
      )}
    </main>
  );
}
