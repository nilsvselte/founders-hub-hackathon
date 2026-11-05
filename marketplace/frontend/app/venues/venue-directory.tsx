"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, money, photo } from "../market";
import type { Room } from "../market";
import { venueFacts } from "../venue-facts";
import type { VenueFacts } from "../venue-facts";
import styles from "./venues.module.css";

function CatalogVenues({ rooms }: { rooms: Room[] }) {
  const venues = new Map<string, Room[]>();
  for (const room of rooms) {
    const listings = venues.get(room.venue) ?? [];
    listings.push(room);
    venues.set(room.venue, listings);
  }

  return (
    <section className={styles.catalog} aria-labelledby="catalog-title">
      <div className={styles.catalogHeading}>
        <h2 id="catalog-title">Venues on standbyroom</h2>
        <p>{venues.size} venues · {rooms.length} rooms</p>
      </div>
      {venues.size ? (
        <div className={styles.catalogGrid}>
          {[...venues].sort(([first], [second]) => first.localeCompare(second)).map(([name, listings]) => {
            const venuePhoto = listings.map((room) => photo(room.image_key)).find(Boolean);
            const cities = [...new Set(listings.map((room) => room.city))].join(" · ");
            return (
              <article className="room-card" key={name}>
                <Link className="room-card-link" href={`/marketplace?${new URLSearchParams({ location: name })}`}>
                  <div className="room-card-photo">
                    {venuePhoto ? (
                      <Image src={venuePhoto.src} alt="" fill sizes="(max-width: 560px) 92vw, (max-width: 860px) 45vw, 30vw" />
                    ) : <span className="room-photo-placeholder">Photo unavailable</span>}
                    {venuePhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
                  </div>
                  <div className="room-card-body">
                    <h3 className="room-card-title">{name}</h3>
                    <p className="room-card-location">{cities}</p>
                    <p className={styles.catalogLink}>View {listings.length} {listings.length === 1 ? "room" : "rooms"} <span aria-hidden="true">→</span></p>
                  </div>
                </Link>
              </article>
            );
          })}
        </div>
      ) : <p className="browse-empty">There are no venues to browse yet.</p>}
    </section>
  );
}

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
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setFailed(true);
    }, 12_000);
    api<Room[]>("rooms", { signal: controller.signal })
      .then((listing) => {
        if (!controller.signal.aborted) setRooms(listing);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [retry]);

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className="browse-kicker">Venues · Trondheim & Stjørdal</p>
        <h1>Find your next meeting space</h1>
        <p>
          Explore coworking spaces, hotels and event venues. Choose a venue to browse its rooms and request a time.
        </p>
        <nav className={styles.jump} aria-label="Pilot venue stories">
          {venueFacts.map((venue) => <a key={venue.id} href={`#${venue.id}`}>About {venue.name}</a>)}
        </nav>
      </header>
      {failed ? (
        <div className="browse-empty">
          <p role="alert">Venue listings couldn’t be loaded. Pilot venue facts are still shown below.</p>
          <button className="browse-reset" type="button" onClick={() => { setFailed(false); setRetry((value) => value + 1); }}>Try again</button>
        </div>
      ) : rooms ? <CatalogVenues rooms={rooms} /> : <p className="browse-empty" role="status">Finding venues…</p>}
      {venueFacts.map((venue) => <VenueSection key={venue.id} venue={venue} rooms={rooms} />)}
    </main>
  );
}
