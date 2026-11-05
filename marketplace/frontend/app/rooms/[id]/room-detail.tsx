"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, money, photo } from "../../market";
import type { Room } from "../../market";
import Standby from "../../standby";

export default function RoomDetail({ roomId }: { roomId: string }) {
  const [room, setRoom] = useState<Room | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api<Room>(`rooms/${encodeURIComponent(roomId)}`, { signal: controller.signal })
      .then((listing) => {
        if (!controller.signal.aborted) setRoom(listing);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [roomId]);

  return (
    <main className="room-detail">
      <Link className="room-back" href="/"><span aria-hidden="true">←</span> Browse rooms</Link>
      {failed ? (
        <section className="room-unavailable">
          <h1>Room unavailable</h1>
          <p>This listing couldn’t be loaded. Browse rooms to find another space.</p>
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
          <div className="room-hero room-detail-photo">
            <Image src={photo(room)} alt="" width={1200} height={800} sizes="(max-width: 700px) 100vw, 1200px" priority />
          </div>
          <div className="room-details">
            <section className="room-overview">
              <h2>About this space</h2>
              <p>{room.description}</p>
              <dl className="room-facts">
                <div className="room-fact"><dt>Capacity</dt><dd>Up to {room.capacity} {room.capacity === 1 ? "person" : "people"}</dd></div>
                <div className="room-fact"><dt>Hourly rate</dt><dd>{money(room.hourly_rate_ore)}</dd></div>
              </dl>
              {room.equipment.length > 0 && (
                <>
                  <h3>What’s included</h3>
                  <ul className="room-amenities">
                    {room.equipment.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </>
              )}
            </section>
            <aside className="room-reservation">
              <Standby room={room} />
            </aside>
          </div>
        </>
      )}
    </main>
  );
}
