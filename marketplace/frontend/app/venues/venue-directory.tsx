"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, money } from "../market";
import type { Room } from "../market";
import { venueFacts } from "../venue-facts";
import type { VenueFacts } from "../venue-facts";
import styles from "./venues.module.css";

function VenueSection({ venue, rooms }: { venue: VenueFacts; rooms: Room[] | null }) {
  const byId = new Map((rooms ?? []).map((room) => [room.id, room]));

  return (
    <section className={styles.venue} id={venue.id} aria-labelledby={`${venue.id}-title`}>
      <div className={styles.venueHead}>
        <div className={styles.venuePhoto}>
          <Image src={venue.photo.src} alt={venue.photo.alt} width={1200} height={900} sizes="(max-width: 860px) 100vw, 45vw" />
        </div>
        <div className={styles.venueIntro}>
          <h2 id={`${venue.id}-title`}>{venue.name}</h2>
          <p className={styles.address}>{venue.address}</p>
          <p>{venue.tagline}</p>
          <div className={styles.today}>
            <strong>How rooms are booked today</strong>
            <p>{venue.bookedToday}</p>
          </div>
          <div className={styles.lists}>
            <div>
              <h3>Membership</h3>
              <ul>{venue.membership.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h3>Included</h3>
              <ul>{venue.includes.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
        </div>
      </div>

      <h3 className={styles.roomsHeading}>Rooms on standbyroom</h3>
      <div className={styles.rooms}>
        {venue.rooms.map(({ roomId, stated, inferred }) => {
          const room = byId.get(roomId);
          return (
            <article className={styles.room} key={roomId}>
              <div className={styles.roomTop}>
                <div>
                  <p className={styles.roomKind}>{room?.kind ?? "Room"}</p>
                  <h4>{room?.name ?? roomId}</h4>
                </div>
                {room && (
                  <p className={styles.roomPrice}>
                    {money(room.hourly_rate_ore)}<span> / hour, proposed</span>
                  </p>
                )}
              </div>
              {room && (
                <p className={styles.roomMeta}>
                  Up to {room.capacity} {room.capacity === 1 ? "person" : "people"}
                  {room.equipment.length > 0 && ` · ${room.equipment.join(", ")}`}
                </p>
              )}
              <p className={styles.stated}><span>Venue says</span>{stated}</p>
              {inferred && <p className={styles.inferred}><span>Our reading</span>{inferred}</p>}
              {room && (
                <Link className={styles.roomLink} href={`/rooms/${encodeURIComponent(room.id)}`}>
                  Request this room <span aria-hidden="true">→</span>
                </Link>
              )}
            </article>
          );
        })}
      </div>

      <div className={styles.footer}>
        <p><strong>Not published:</strong> {venue.notPublished.join(", ")}.</p>
        <p>
          <strong>Sources:</strong>{" "}
          {venue.sources.map((source, index) => (
            <span key={source.url}>
              {index > 0 && " · "}
              <a href={source.url} target="_blank" rel="noreferrer">{source.label}</a>
            </span>
          ))}
          {" "}(checked 5 November 2026)
        </p>
      </div>
    </section>
  );
}

export default function VenueDirectory() {
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api<Room[]>("rooms", { signal: controller.signal })
      .then((listing) => {
        if (!controller.signal.aborted) setRooms(listing);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, []);

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className="browse-kicker">Pilot venues · Trondheim</p>
        <h1>Rooms that only members can book</h1>
        <p>
          Kowork and Brighten both have meeting rooms that are included in their members’ rent. Neither sells room
          time to anyone else, and neither publishes an hourly price. standbyroom lets them sell the hours their members
          don’t use.
        </p>
        <nav className={styles.jump} aria-label="Venues">
          {venueFacts.map((venue) => <a key={venue.id} href={`#${venue.id}`}>{venue.name}</a>)}
        </nav>
      </header>
      {failed && <p className="status-note" role="status">Room listings couldn’t be loaded. Venue facts are shown without live prices.</p>}
      {venueFacts.map((venue) => <VenueSection key={venue.id} venue={venue} rooms={rooms} />)}
    </main>
  );
}
