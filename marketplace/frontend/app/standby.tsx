"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useAccount } from "./account";
import { ApiError, api, money, photo } from "./market";
import type { Room } from "./market";
import { upcomingRoomStart } from "./oslo-time";

type Offer = {
  id: string;
  room_name: string;
  room_photo: string | null;
  start_at: string;
  end_at: string;
  price_ore: number;
  expires_at: string;
  match_reason: string | null;
  match_provider: "claude" | "demo" | null;
};

type StandbyRequest = {
  id: string;
  room_id: string | null;
  status: "waiting" | "offered" | "confirmed" | "expired";
  offer: Offer | null;
  booking_reference: string | null;
  earliest_start: string;
  latest_end: string;
  duration_minutes: number;
  party_size: number;
  equipment: string[];
  max_price_ore: number;
  preferences: string;
};

type Action = "submit" | "accept" | "retry" | "release";

const formatDay = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo", weekday: "short", day: "numeric", month: "short",
});
const formatTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function localInputValue(time: Date) {
  return new Date(time.getTime() - time.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function describeWindow(start: string, end: string) {
  const from = new Date(start);
  const to = new Date(end);
  const fromDay = formatDay.format(from);
  const toDay = formatDay.format(to);
  return `${fromDay}, ${formatTime.format(from)}–${fromDay === toDay ? "" : `${toDay}, `}${formatTime.format(to)}`;
}

const requestPath = (id: string) => `standby-requests/${encodeURIComponent(id)}`;

type StandbyProps = {
  room: Room; requestId?: never; searchDate?: string; guests?: number; browseQuery?: string;
} | {
  requestId: string; room?: never; searchDate?: never; guests?: never; browseQuery?: never;
};

export default function Standby(props: StandbyProps) {
  const { account, loading } = useAccount();
  const query = new URLSearchParams(props.browseQuery);
  if (props.searchDate) query.set("date", props.searchDate);
  if (props.guests) query.set("guests", String(props.guests));
  const returnTo = props.room
    ? `/rooms/${encodeURIComponent(props.room.id)}${query.size ? `?${query}` : ""}`
    : `/bookings/${encodeURIComponent(props.requestId)}`;

  if (loading) return <p className="status-note" role="status">Checking your account…</p>;
  if (!account) {
    return (
      <section className="room-access">
        <h2>{props.room ? "Request this room" : "View your booking"}</h2>
        <p>Use your renter account to send requests and manage bookings.</p>
        <Link className="button primary" href={`/sign-in?next=${encodeURIComponent(returnTo)}`}>Sign in to continue <span aria-hidden="true">→</span></Link>
        <Link className="room-back" href={`/register?next=${encodeURIComponent(returnTo)}`}>Create a renter account</Link>
      </section>
    );
  }
  if (account.role !== "renter") {
    return (
      <section className="room-access">
        <h2>{props.room ? "Request this room" : "View your booking"}</h2>
        <p>Room requests are available to renter accounts.</p>
        <Link className="button secondary" href="/host">Open host dashboard</Link>
      </section>
    );
  }
  return <BookingFlow key={`${account.id}:${returnTo}`} {...props} />;
}

function BookingFlow({ room, requestId, searchDate, guests }: StandbyProps) {
  const router = useRouter();
  const [request, setRequest] = useState<StandbyRequest | null>(null);
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [demoNote, setDemoNote] = useState("");
  const [earliest, setEarliest] = useState("");
  const [latest, setLatest] = useState("");
  const [timeZone, setTimeZone] = useState("");
  const [restoring, setRestoring] = useState(Boolean(requestId));
  const id = request?.id;
  const status = request?.status;

  useEffect(() => {
    const start = upcomingRoomStart(searchDate)?.getTime() ?? Date.now();
    setEarliest(localInputValue(new Date(start)));
    setLatest(localInputValue(new Date(start + 120 * 60_000)));
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone.replaceAll("_", " "));
  }, [searchDate]);

  useEffect(() => {
    if (!requestId) return;
    const controller = new AbortController();
    api<{ enabled: boolean }>("demo/config", { signal: controller.signal })
      .then(({ enabled }) => setDemoEnabled(enabled))
      .catch(() => {});
    api<StandbyRequest>(requestPath(requestId), { signal: controller.signal })
      .then((previous) => {
        if (!controller.signal.aborted) setRequest(previous);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError("We couldn’t open this booking. It may not be available to your account.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setRestoring(false);
      });
    return () => controller.abort();
  }, [requestId]);

  useEffect(() => {
    if (!id || busy || (status !== "waiting" && status !== "offered")) return;
    const controller = new AbortController();
    let timer: number;

    async function poll(requestId: string) {
      try {
        const next = await api<StandbyRequest>(requestPath(requestId), { signal: controller.signal });
        if (controller.signal.aborted) return;
        setRequest(next);
        setPollError(false);
      } catch {
        if (controller.signal.aborted) return;
        setPollError(true);
      }
      timer = window.setTimeout(() => void poll(requestId), 2_000);
    }

    timer = window.setTimeout(() => void poll(id), 2_000);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [id, status, busy]);

  async function act(action: Action, run: () => Promise<void>) {
    setError("");
    setBusy(action);
    try {
      await run();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!room || busy || request) return;
    const data = new FormData(event.currentTarget);
    const start = new Date(earliest);
    const end = new Date(latest);
    const duration = Number(data.get("duration"));
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end.getTime() - start.getTime() < duration * 60_000) {
      setError("Choose a time window long enough for your meeting.");
      return;
    }
    setDemoNote("");
    setPollError(false);
    void act("submit", async () => {
      const next = await api<StandbyRequest>("standby-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: room.id,
          earliest_start: start.toISOString(),
          latest_end: end.toISOString(),
          duration_minutes: duration,
          party_size: Number(data.get("party")),
          equipment: data.getAll("equipment").map(String),
          max_price_ore: Math.round(Number(data.get("budget")) * 100),
          preferences: String(data.get("preferences") ?? "").trim(),
        }),
      });
      setRequest(next);
      router.push(`/bookings/${encodeURIComponent(next.id)}`);
    });
  }

  function accept(offer: Offer) {
    if (!id) return;
    void act("accept", async () => {
      const path = requestPath(id);
      try {
        setRequest(await api<StandbyRequest>(`${path}/offers/${encodeURIComponent(offer.id)}/accept`, { method: "POST" }));
      } catch (failure) {
        if (failure instanceof ApiError && (failure.status === 409 || failure.status === 410)) {
          const next = await api<StandbyRequest>(path);
          setRequest(next);
          if (next.status === "confirmed") return;
        }
        throw failure;
      }
    });
  }

  function retry() {
    if (!id) return;
    void act("retry", async () => {
      setRequest(await api<StandbyRequest>(`${requestPath(id)}/retry`, { method: "POST" }));
    });
  }

  function release() {
    if (!id) return;
    void act("release", async () => {
      const result = await api<{ created: boolean; reason: string | null }>("demo/release", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: request?.room_id ?? undefined }),
      });
      setDemoNote(result.created ? "Demo room released. Checking for a match…" : (result.reason ?? "No new room was released."));
      setRequest(await api<StandbyRequest>(requestPath(id)));
    });
  }

  const offer = request?.offer;
  const offerPhoto = photo(offer?.room_photo);
  if (requestId && !request) {
    if (restoring) return <p className="status-note" role="status">Loading your booking…</p>;
    return (
      <section className="booking-detail-error">
        <p className="error" role="alert">{error || "Booking unavailable."}</p>
        <Link className="button secondary" href="/bookings">Back to your bookings</Link>
      </section>
    );
  }

  return (
    <div className={requestId ? "booking-grid" : "booking-grid booking-create"}>
      <section className="panel request-panel" aria-labelledby="request-title">
        <div className="panel-heading">
          <h2 id="request-title">{request ? "Your request" : "Request this room"}</h2>
          {!request && <p>Choose a time window and a budget for your meeting.</p>}
        </div>
        {request ? (
          <div className="request-summary">
            <dl>
              <div><dt>Window</dt><dd>{describeWindow(request.earliest_start, request.latest_end)} Oslo time</dd></div>
              <div><dt>Duration</dt><dd>{request.duration_minutes} minutes</dd></div>
              <div><dt>People</dt><dd>{request.party_size}</dd></div>
              <div><dt>Max total price</dt><dd>{money(request.max_price_ore)}</dd></div>
              {request.equipment.length > 0 && <div><dt>Equipment</dt><dd>{request.equipment.join(", ")}</dd></div>}
              {request.preferences && <div><dt>Preferences</dt><dd>{request.preferences}</dd></div>}
            </dl>
            {requestId && <Link className="button secondary" href={request.room_id ? `/rooms/${encodeURIComponent(request.room_id)}` : "/"}>Start a new request</Link>}
          </div>
        ) : (
        <form onSubmit={submit}>
          <fieldset disabled={!!busy || restoring}>
            <legend className="sr-only">Meeting details</legend>
            <div className="form-grid">
              <label>
                Earliest start
                <input type="datetime-local" name="earliest" value={earliest} onChange={(event) => setEarliest(event.target.value)} required />
              </label>
              <label>
                Latest end
                <input type="datetime-local" name="latest" value={latest} onChange={(event) => setLatest(event.target.value)} required />
              </label>
              <p className="time-note">Input times use your local time{timeZone ? ` (${timeZone})` : ""}.</p>
              <label>
                Duration
                <select name="duration" defaultValue="30">
                  {[15, 30, 45, 60, 90].map((minutes) => <option value={minutes} key={minutes}>{minutes} minutes</option>)}
                </select>
              </label>
              <label>
                People
                <input type="number" name="party" defaultValue={Math.min(guests ?? 4, room?.capacity ?? 4)} min="1" max={room?.capacity ?? 50} required />
              </label>
              <label>
                Max total price <span className="unit">NOK</span>
                <input type="number" name="budget" defaultValue={Math.ceil((room?.hourly_rate_ore ?? 50000) / 100)} min="1" max="100000" required />
              </label>
              {room?.equipment.includes("screen") && (
                <label className="equipment">
                  <span>Equipment</span>
                  <span className="equipment-option"><input name="equipment" type="checkbox" value="screen" defaultChecked /> Screen required</span>
                </label>
              )}
              <label className="form-wide">
                Matching preferences <span className="unit">optional</span>
                <input name="preferences" maxLength={500} placeholder="e.g. Earlier is better if possible" />
              </label>
            </div>
          </fieldset>
          <button type="submit" className="button primary" disabled={!!busy || restoring || !earliest || !latest}>
            {busy === "submit" ? "Submitting…" : "Send request"}
            <span aria-hidden="true">→</span>
          </button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        )}
      </section>
      {requestId && <section className="panel status-panel" aria-labelledby="status-title">
        <div className="panel-heading">
          <h2 id="status-title">Booking status</h2>
        </div>
        <div aria-live="polite" aria-atomic="true" className="status-body">
          {status === "waiting" && <EmptyState icon="…" title="Waiting for an opening">We’ll check new openings against your request. You can return here from your bookings.</EmptyState>}
          {status === "expired" && <EmptyState icon="↻" title="This request has expired">Start a new request to choose another time.</EmptyState>}
          {status === "confirmed" && (
            <div className="confirmed">
              <span className="status-icon" aria-hidden="true">✓</span>
              <div>
                <h3>Booking confirmed</h3>
                {request?.booking_reference && <p>Booking reference <strong>{request.booking_reference}</strong></p>}
              </div>
            </div>
          )}
          {offer && (status === "offered" || status === "confirmed") && (
            <div className="offer">
              <div className="offer-photo room-photo-frame">
                {offerPhoto ? (
                  <Image src={offerPhoto.src} alt="" width={800} height={450} sizes="(max-width: 680px) 100vw, 500px" />
                ) : (
                  <span className="room-photo-placeholder">Photo unavailable</span>
                )}
                {offerPhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
              </div>
              <div className="offer-top">
                <div>
                  <p className="offer-label">{status === "confirmed" ? "Booked room" : "Room available"}</p>
                  <h3>{offer.room_name}</h3>
                </div>
                <p className="price">{money(offer.price_ore)}</p>
              </div>
              <p className="offer-time">{describeWindow(offer.start_at, offer.end_at)} <span>Oslo time</span></p>
              {status === "offered" && <p className="hold">Held until {formatTime.format(new Date(offer.expires_at))} Oslo time</p>}
              {offer.match_reason && (
                <p className="match-note">
                  {offer.match_provider && <strong>{offer.match_provider === "claude" ? "Matched by Claude" : "Demo match"}. </strong>}
                  {offer.match_reason}
                </p>
              )}
            </div>
          )}
        </div>
        {error && request && <p className="error" role="alert">{error}</p>}
        {pollError && (status === "waiting" || status === "offered") && <p className="status-note" role="status">Connection interrupted. Retrying automatically…</p>}
        {status === "offered" && offer && (
          <button type="button" className="button primary" onClick={() => accept(offer)} disabled={!!busy}>
            {busy === "accept" ? "Booking…" : "Accept and book"}
            <span aria-hidden="true">→</span>
          </button>
        )}
        {status === "waiting" && !demoEnabled && (
          <button type="button" className="button secondary" onClick={retry} disabled={!!busy}>
            {busy === "retry" ? "Checking…" : "Check for another opening"}
          </button>
        )}
        {demoEnabled && status === "waiting" && (
          <div className="demo">
            <strong>Demo controls</strong>
            <p>Simulate the host releasing an opening for this room.</p>
            <button type="button" className="button secondary" onClick={release} disabled={!!busy}>
              {busy === "release" ? "Releasing…" : "Release demo room"}
            </button>
            {demoNote && <p className="status-note" role="status">{demoNote}</p>}
          </div>
        )}
      </section>}
    </div>
  );
}

function EmptyState({ icon, title, children }: { icon: string; title: string; children: string }) {
  return (
    <div className="empty-state">
      <span className="status-icon" aria-hidden="true">{icon}</span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
