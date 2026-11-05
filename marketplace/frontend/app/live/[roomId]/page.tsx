"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../market";
import { ghostMinutes } from "../../room-status";
import type { Occupancy, Span } from "../../room-status";
import styles from "./live.module.css";

type LiveRoom = {
  id: string;
  name: string;
  venue: string;
  last_occupancy: Occupancy | null;
  current_booking: Span | null;
  active_block: Span | null;
};

const POLL_MS = 2_000;
const clock = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
const hm = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

export default function LiveRoomPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const [room, setRoom] = useState<LiveRoom | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const next = await api<LiveRoom>(`public/rooms/${encodeURIComponent(roomId)}/live`);
        if (active) { setRoom(next); setError(null); }
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Connection lost");
      }
      if (active) setNow(Date.now());
    };
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => { active = false; window.clearInterval(timer); };
  }, [roomId]);

  const sensor = room?.last_occupancy ?? null;
  const booking = room?.current_booking ?? room?.active_block ?? null;
  const ghost = room ? ghostMinutes(booking, sensor, now) : null;
  const state = !sensor ? "none" : sensor.occupied ? "occupied" : "empty";

  return (
    <main className={styles.page}>
      <p className={styles.kicker}>Live room view</p>
      <h1 className={styles.name}>{room ? `${room.name} · ${room.venue}` : roomId}</h1>

      <section className={`${styles.indicator} ${styles[state]}`} aria-live="polite">
        <span className={styles.dot} aria-hidden="true" />
        <strong>{!room ? "Connecting…" : state === "occupied" ? "Someone’s in the room" : state === "empty" ? "Empty" : "No sensor"}</strong>
        {sensor && <span className={styles.meta}>Last sensor reading {clock.format(new Date(sensor.changed_at))}</span>}
      </section>

      {room && (
        <p className={`${styles.booking} ${booking ? styles.booked : styles.free}`}>
          {room.current_booking ? "Booked" : room.active_block ? "Blocked" : "Free now"}
          {booking && <> · {hm.format(new Date(booking.start_at))}–{hm.format(new Date(booking.end_at))}</>}
        </p>
      )}
      {ghost !== null && <p className={styles.ghost} role="status">⚠ {room?.current_booking ? "Booked" : "Blocked"} but empty for {ghost} min</p>}
      {error && <p className={styles.error} role="alert">{error}. Retrying…</p>}
      <p className={styles.meta}>Updated {clock.format(new Date(now))} · refreshes every 2 s</p>
    </main>
  );
}
