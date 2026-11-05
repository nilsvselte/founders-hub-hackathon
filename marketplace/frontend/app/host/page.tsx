"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useAccount } from "../account";
import { api, money, photo } from "../market";
import type { Room } from "../market";
import { osloInstant } from "../oslo-time";
import { LiveRoomLink } from "../demo-room";
import { ghostMinutes } from "../room-status";
import type { Span } from "../room-status";
import styles from "./host.module.css";

type Listing = Room & {
  published: boolean;
  last_occupancy?: { occupied: boolean; changed_at: string } | null;
  current_booking?: (Span & { reference: string }) | null;
  active_block?: (Span & { id: string }) | null;
};
type Release = { created: boolean; opening_id?: string | null; reason?: string | null };
const kinds = ["Studio", "Workshop", "Meeting room", "Boardroom"];

const REFRESH_MS = 12_000;
const osloClock = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const osloDay = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Oslo", day: "numeric", month: "short" });

function clock(value: string, now: number) {
  const time = new Date(value);
  const sameDay = osloDay.format(time) === osloDay.format(new Date(now));
  return sameDay ? osloClock.format(time) : `${osloDay.format(time)} ${osloClock.format(time)}`;
}

function RoomStatus({ room, now }: { room: Listing; now: number }) {
  const booking = room.current_booking ?? room.active_block ?? null;
  const sensor = room.last_occupancy;
  const ghost = ghostMinutes(booking, sensor, now);
  return (
    <div className={styles.status} aria-live="polite">
      <span className={booking ? styles.booked : styles.free}>
        {room.current_booking ? "Booked" : room.active_block ? "Blocked" : "Free now"}
        {booking && <> until <time dateTime={booking.end_at}>{clock(booking.end_at, now)}</time></>}
      </span>
      <span className={sensor ? (sensor.occupied ? styles.occupied : styles.vacant) : styles.noSensor}>
        {sensor
          ? <>{sensor.occupied ? "Occupied" : "Empty"} since <time dateTime={sensor.changed_at}>{clock(sensor.changed_at, now)}</time></>
          : "No sensor"}
      </span>
      {ghost !== null && <strong className={styles.ghost} role="status">⚠ {room.current_booking ? "Booked" : "Blocked"} but empty for {ghost} min</strong>}
    </div>
  );
}

function failureMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function parseOsloTime(value: FormDataEntryValue | null) {
  const [date, time] = String(value ?? "").split("T");
  return osloInstant({ date, time });
}

function ListingThumbnail({ imageKey }: { imageKey: string }) {
  const roomPhoto = photo(imageKey);
  return (
    <div
      className={`${styles.thumb} room-photo-frame`}
      style={roomPhoto ? { backgroundImage: `url("${roomPhoto.src}")` } : undefined}
      aria-hidden={roomPhoto?.isVenuePhoto ? undefined : true}
    >
      {roomPhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
    </div>
  );
}

export default function HostPage() {
  const { account, loading } = useAccount();

  if (loading) return <main className={styles.page}><p role="status">Loading host workspace…</p></main>;

  if (account?.role !== "host") return (
    <main className={styles.page}>
      <div className={styles.access}>
        <p className={styles.kicker}>For hosts</p>
        <h1>Host workspace</h1>
        <p>{account ? "A host account is needed to list and manage rooms." : "Sign in as a host to manage your room listings and open up available time."}</p>
        <div className={styles.accessActions}>
          {!account && <Link className={styles.primary} href="/sign-in?next=%2Fhost">Host sign in</Link>}
          <Link className={styles.secondary} href="/register?role=host&next=%2Fhost">Create a host account</Link>
        </div>
      </div>
    </main>
  );

  return <HostDashboard key={account.id} />;
}

function HostDashboard() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loadingListings, setLoadingListings] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editor, setEditor] = useState<Listing | "new" | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const editorHeading = useRef<HTMLHeadingElement>(null);
  const mutationInFlight = useRef(false);
  const releaseAttempts = useRef(new Map<string, { duration: number; id: string }>());

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const controller = new AbortController();
    api<Listing[]>("host/rooms", { signal: controller.signal })
      .then((rooms) => {
        if (!controller.signal.aborted) setListings(rooms);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setLoadError(failureMessage(failure));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingListings(false);
      });
    // Live status: refresh bookings and sensor state quietly; keep old data on a failed refresh.
    const timer = window.setInterval(() => {
      setNow(Date.now());
      if (mutationInFlight.current || document.hidden) return;
      api<Listing[]>("host/rooms", { signal: controller.signal })
        .then((rooms) => {
          if (!controller.signal.aborted && !mutationInFlight.current) setListings(rooms);
        })
        .catch(() => {});
    }, REFRESH_MS);
    return () => {
      window.clearInterval(timer);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (editor) editorHeading.current?.focus();
  }, [editor]);

  async function perform(key: string, operation: () => Promise<void>) {
    if (mutationInFlight.current) return;
    mutationInFlight.current = true;
    setBusy(key);
    setNotice("");
    setError("");
    try {
      await operation();
    } catch (failure) {
      setError(failureMessage(failure));
    } finally {
      mutationInFlight.current = false;
      setBusy("");
    }
  }

  function replaceListing(room: Listing) {
    setListings((previous) => previous.map((listing) => listing.id === room.id ? room : listing));
  }

  function openEditor(listing: Listing | "new") {
    setNotice("");
    setError("");
    setEditor(listing);
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) ?? "").trim();
    const details = {
      name: value("name"), city: value("city"), venue: value("venue"),
      kind: value("kind"), description: value("description"), capacity: Number(value("capacity")),
      equipment: value("equipment").split(",").map((item) => item.trim()).filter(Boolean),
      hourly_rate_ore: Math.round(Number(value("rate")) * 100),
    };
    if (!details.name || !details.city || !details.venue || !details.description) {
      setError("Enter a room name, venue, city, and description.");
      return;
    }
    void perform("save", async () => {
      const current = editor === "new" ? null : editor;
      const path = current ? `host/rooms/${encodeURIComponent(current.id)}` : "host/rooms";
      const room = await api<Listing>(path, {
        method: current ? "PATCH" : "POST",
        body: JSON.stringify(current ? { details } : details),
      });
      if (current) replaceListing(room);
      else setListings((previous) => [room, ...previous]);
      setEditor(null);
      setNotice(current ? "Listing details updated." : "Draft created. Publish it when you're ready.");
    });
  }

  function togglePublication(room: Listing) {
    void perform(room.id, async () => {
      const next = await api<Listing>(`host/rooms/${encodeURIComponent(room.id)}`, {
        method: "PATCH", body: JSON.stringify({ published: !room.published }),
      });
      replaceListing(next);
      setNotice(next.published ? `${next.name} is now on the marketplace.` : `${next.name} is now a draft.`);
    });
  }

  function release(event: FormEvent<HTMLFormElement>, room: Listing) {
    event.preventDefault();
    const duration_minutes = Number(new FormData(event.currentTarget).get("duration"));
    void perform(room.id, async () => {
      const previous = releaseAttempts.current.get(room.id);
      const id = previous?.duration === duration_minutes ? previous.id : crypto.randomUUID();
      releaseAttempts.current.set(room.id, { duration: duration_minutes, id });
      const result = await api<Release>(`host/rooms/${encodeURIComponent(room.id)}/release`, {
        method: "POST", body: JSON.stringify({ duration_minutes, release_id: id }),
      });
      if (!result.created && !(result.reason === "duplicate_release" && result.opening_id)) {
        throw new Error("The time could not be released. Try again.");
      }
      releaseAttempts.current.delete(room.id);
      setNotice(result.created
        ? `${room.name} is open for ${duration_minutes} minutes, including turnover time.`
        : `The release for ${room.name} was already recorded.`);
    });
  }

  function scheduleBlock(event: FormEvent<HTMLFormElement>, room: Listing) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const start = parseOsloTime(values.get("start"));
    const end = parseOsloTime(values.get("end"));
    void perform(`block-${room.id}`, async () => {
      if (!start || !end) throw new Error("Choose valid start and end times in Oslo time.");
      if (end <= start) throw new Error("The block must end after it starts.");
      if (end.getTime() <= Date.now()) throw new Error("The block must end in the future.");
      await api(`host/rooms/${encodeURIComponent(room.id)}/blocks`, {
        method: "POST", body: JSON.stringify({ starts_at: start.toISOString(), ends_at: end.toISOString() }),
      });
      form.reset();
      setNotice(`Block scheduled for ${room.name}. Press Release room on its device when the room is free.`);
    });
  }

  const selected = editor && editor !== "new" ? editor : null;

  return (
    <main className={styles.page}>
      <header className={styles.heading}>
        <div>
          <p className={styles.kicker}>Host workspace</p>
          <h1>Your rooms</h1>
          <p>Manage listings and release time when a room becomes available.</p>
          <LiveRoomLink />
        </div>
        <button type="button" className={styles.primary} disabled={!!busy || loadingListings || !!loadError} onClick={() => openEditor("new")}>＋ Add a room</button>
      </header>

      {notice && <p className={styles.notice} role="status">{notice}</p>}
      {(error || loadError) && <p className={styles.error} role="alert">{error || loadError}</p>}

      <div className={editor ? styles.withEditor : styles.content}>
        {editor && (
          <section className={styles.editor} aria-labelledby="listing-editor">
            <p className={styles.kicker}>{selected ? "Listing details" : "New listing"}</p>
            <h2 id="listing-editor" ref={editorHeading} tabIndex={-1}>{selected ? `Edit ${selected.name}` : "Add a room"}</h2>
            <form className={styles.form} key={selected?.id ?? "new"} onSubmit={save}>
              <label>Room name<input name="name" defaultValue={selected?.name} maxLength={100} required placeholder="The Library" /></label>
              <label>Venue<input name="venue" defaultValue={selected?.venue} maxLength={100} required placeholder="Møllehuset" /></label>
              <label>City<input name="city" defaultValue={selected?.city} maxLength={80} required placeholder="Oslo" /></label>
              <label>Room type<select name="kind" defaultValue={selected?.kind ?? "Meeting room"}>{kinds.map((kind) => <option key={kind}>{kind}</option>)}</select></label>
              <label>Capacity<input name="capacity" type="number" defaultValue={selected?.capacity ?? 8} min="1" max="100" step="1" required /></label>
              <label>Hourly rate (NOK)<input name="rate" type="number" defaultValue={selected ? selected.hourly_rate_ore / 100 : 450} min="1" max="100000" step="0.01" required /></label>
              <label className={styles.full}>Equipment <span>separate items with commas</span><input name="equipment" defaultValue={selected?.equipment.join(", ")} maxLength={200} placeholder="Screen, whiteboard, video conferencing" /></label>
              <label className={styles.full}>Description<textarea name="description" defaultValue={selected?.description} rows={3} maxLength={800} required placeholder="What should people know about this room?" /></label>
              <div className={`${styles.actions} ${styles.full}`}>
                <button type="submit" className={styles.primary} disabled={!!busy}>{busy === "save" ? "Saving…" : selected ? "Save changes" : "Create draft"}</button>
                <button type="button" className={styles.secondary} disabled={!!busy} onClick={() => setEditor(null)}>Cancel</button>
              </div>
            </form>
          </section>
        )}

        <section className={styles.listings} aria-label="Your listings">
          {loadingListings && <p role="status">Loading your rooms…</p>}
          {loadError && <button className={styles.secondary} type="button" onClick={() => window.location.reload()}>Reload rooms</button>}
          {!loadingListings && !loadError && listings.length === 0 && (
            <div className={styles.empty}>
              <span className={styles.emptyMark} aria-hidden="true">✳</span>
              <div>
                <h2>No rooms listed yet</h2>
                <p>Add room details first. You can publish the listing when it's ready.</p>
              </div>
            </div>
          )}
          {listings.map((room) => (
            <article className={styles.room} key={room.id}>
              <ListingThumbnail imageKey={room.image_key} />
              <div className={styles.roomInfo}>
                <div className={styles.roomMeta}>
                  <span>{room.kind}</span>
                  <span className={room.published ? styles.published : styles.draft}>{room.published ? "Published" : "Draft"}</span>
                </div>
                <h2>{room.name}</h2>
                <p>{room.venue} · {room.city}</p>
                <p>{room.capacity} guests · {money(room.hourly_rate_ore)} / hour</p>
                <RoomStatus room={room} now={now} />
                <div className={styles.actions}>
                  <button className={styles.secondary} type="button" disabled={!!busy} onClick={() => openEditor(room)}>Edit listing</button>
                  <button className={styles.secondary} type="button" disabled={!!busy} onClick={() => togglePublication(room)}>{room.published ? "Unpublish" : "Publish"}</button>
                  {room.published && <Link className={styles.preview} href={`/rooms/${encodeURIComponent(room.id)}`}>View listing ↗</Link>}
                </div>
                {room.published && (
                  <details className={styles.block}>
                    <summary>Schedule a room block</summary>
                    <p>Reserve this time for existing use. Press Release room on the room’s device to offer any remaining time. Times are in Oslo time.</p>
                    <form className={styles.form} onSubmit={(event) => scheduleBlock(event, room)}>
                      <label>Block starts<input name="start" type="datetime-local" required /></label>
                      <label>Block ends<input name="end" type="datetime-local" required /></label>
                      <div className={styles.full}>
                        <button type="submit" className={styles.primary} disabled={!!busy}>{busy === `block-${room.id}` ? "Scheduling…" : "Schedule block"}</button>
                      </div>
                    </form>
                  </details>
                )}
              </div>
              {room.published && (
                <form className={styles.release} onSubmit={(event) => release(event, room)}>
                  <label>Available from now<select name="duration" defaultValue="60" aria-label={`Available time for ${room.name}`}>
                    <option value="30">30 minutes</option><option value="60">1 hour</option><option value="120">2 hours</option><option value="240">4 hours</option><option value="480">8 hours</option>
                  </select></label>
                  <button type="submit" className={styles.primary} disabled={!!busy}>Release time</button>
                </form>
              )}
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
