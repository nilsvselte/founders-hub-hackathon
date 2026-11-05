"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api, money, photo } from "../../market";
import type { Room } from "../../market";
import QuotePreview from "../../quote-preview";
import Standby from "../../standby";
import { factsForVenue } from "../../venue-facts";

export default function RoomDetail({ roomId, searchDate, guests }: { roomId: string; searchDate?: string; guests?: number }) {
  const [room, setRoom] = useState<Room | null>(null);
  const [failure, setFailure] = useState<"missing" | "temporary" | null>(null);
  const [retry, setRetry] = useState(0);
  const params = useSearchParams();
  const browseParams = new URLSearchParams();
  for (const name of ["location", "date", "guests", "category"]) {
    const value = params.get(name);
    if (value) browseParams.set(name, value);
  }
  const browseHref = browseParams.size ? `/marketplace?${browseParams}` : "/marketplace";
  const roomPhoto = photo(room?.image_key);
  const venue = room ? factsForVenue(room.venue) : undefined;

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setFailure("temporary");
    }, 12_000);
    api<Room>(`rooms/${encodeURIComponent(roomId)}`, { signal: controller.signal })
      .then((listing) => {
        if (!controller.signal.aborted) setRoom(listing);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setFailure(error instanceof ApiError && error.status === 404 ? "missing" : "temporary");
        }
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [roomId, retry]);

  return (
    <main className="room-detail">
      <Link className="room-back" href={browseHref}><span aria-hidden="true">←</span> Browse rooms</Link>
      {failure ? (
        <section className="room-unavailable">
          <h1>{failure === "missing" ? "Room unavailable" : "Couldn’t load this room"}</h1>
          {failure === "missing" ? (
            <p>This listing is no longer available. Browse rooms to find another space.</p>
          ) : (
            <>
              <p>Check your connection and try again.</p>
              <button className="button secondary" type="button" onClick={() => {
                setFailure(null);
                setRetry((value) => value + 1);
              }}>Try again</button>
            </>
          )}
        </section>
      ) : !room ? (
        <p className="status-note" role="status">Loading room…</p>
      ) : (
        <>
          <div className="room-heading">
            <p className="room-kicker">{room.kind}</p>
            <h1>{room.name}</h1>
            <p>{room.venue} · {room.city}</p>
          </div>
          <div className="room-hero room-detail-photo room-photo-frame">
            {roomPhoto ? (
              <Image src={roomPhoto.src} alt="" width={1200} height={800} sizes="(max-width: 700px) 100vw, 1200px" priority />
            ) : (
              <span className="room-photo-placeholder">Photo unavailable</span>
            )}
            {roomPhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
          </div>
          <div className="room-details">
            <section className="room-overview">
              <h2>About this space</h2>
              <p>{room.description}</p>
              <dl className="room-facts">
                <div className="room-fact"><dt>Capacity</dt><dd>Up to {room.capacity} {room.capacity === 1 ? "person" : "people"}</dd></div>
                <div className="room-fact"><dt>Base hourly rate</dt><dd>{money(room.hourly_rate_ore)}</dd></div>
              </dl>
              {room.equipment.length > 0 && (
                <>
                  <h3>What’s included</h3>
                  <ul className="room-amenities">
                    {room.equipment.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </>
              )}
              {venue && (
                <div className="room-venue-note">
                  <h3>How it’s booked today</h3>
                  <p>{venue.bookedToday}</p>
                  <Link href={`/venues#${venue.id}`}>More about {venue.name} <span aria-hidden="true">→</span></Link>
                </div>
              )}
              <QuotePreview room={room} searchDate={searchDate} />
            </section>
            <aside className="room-reservation">
              <Standby room={room} searchDate={searchDate} guests={guests} browseQuery={browseParams.toString()} />
            </aside>
          </div>
        </>
      )}
    </main>
  );
}
