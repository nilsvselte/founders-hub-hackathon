"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type Offer = {
  id: string;
  room_name: string;
  start_at: string;
  end_at: string;
  price_ore: number;
  expires_at: string;
  match_reason: string | null;
  match_provider: "claude" | "demo" | null;
};

type StandbyRequest = {
  id: string;
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
const formatPrice = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
const storageKey = "mesh-marketplace-active-request";

function savedRequestId() {
  try {
    return sessionStorage.getItem(storageKey);
  } catch {
    return null;
  }
}

function rememberRequest(id: string | null) {
  try {
    if (id) sessionStorage.setItem(storageKey, id);
    else sessionStorage.removeItem(storageKey);
  } catch {
    // The current request remains available in memory when storage is unavailable.
  }
}

function localInputValue(time: Date) {
  return new Date(time.getTime() - time.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, { cache: "no-store", ...options });
  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}));
    const message = typeof detail === "string" ? detail : detail?.[0]?.msg;
    throw new ApiError(message ?? "Couldn’t complete that request. Please try again.", response.status);
  }
  return response.json();
}

function describeWindow(start: string, end: string) {
  const from = new Date(start);
  const to = new Date(end);
  const fromDay = formatDay.format(from);
  const toDay = formatDay.format(to);
  return `${fromDay}, ${formatTime.format(from)}–${fromDay === toDay ? "" : `${toDay}, `}${formatTime.format(to)}`;
}

const requestPath = (id: string) => `standby-requests/${encodeURIComponent(id)}`;

export default function Standby({ venueName }: { venueName: string }) {
  const [request, setRequest] = useState<StandbyRequest | null>(null);
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [demoNote, setDemoNote] = useState("");
  const [earliest, setEarliest] = useState("");
  const [latest, setLatest] = useState("");
  const [timeZone, setTimeZone] = useState("");
  const [restoring, setRestoring] = useState(true);
  const id = request?.id;
  const status = request?.status;

  useEffect(() => {
    const now = Date.now();
    setEarliest(localInputValue(new Date(now)));
    setLatest(localInputValue(new Date(now + 120 * 60_000)));
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone.replaceAll("_", " "));
    const controller = new AbortController();
    api<{ enabled: boolean }>("demo/config", { signal: controller.signal })
      .then(({ enabled }) => setDemoEnabled(enabled))
      .catch(() => {});
    const stored = savedRequestId();
    if (stored) {
      api<StandbyRequest>(requestPath(stored), { signal: controller.signal })
        .then((previous) => {
          if (!controller.signal.aborted) setRequest(previous);
        })
        .catch((failure) => {
          if (controller.signal.aborted) return;
          if (failure instanceof ApiError && (failure.status === 404 || failure.status === 422)) {
            rememberRequest(null);
          } else {
            setError("Couldn’t reopen your saved request. Reload this page to try again.");
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setRestoring(false);
        });
    } else {
      setRestoring(false);
    }
    return () => controller.abort();
  }, []);

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
          earliest_start: start.toISOString(),
          latest_end: end.toISOString(),
          duration_minutes: duration,
          party_size: Number(data.get("party")),
          equipment: data.getAll("equipment").map(String),
          max_price_ore: Math.round(Number(data.get("budget")) * 100),
          preferences: String(data.get("preferences") ?? "").trim(),
        }),
      });
      rememberRequest(next.id);
      setRequest(next);
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
      const result = await api<{ created: boolean; reason: string | null }>("demo/release", { method: "POST" });
      setDemoNote(result.created ? "Demo room released. Checking for a match…" : (result.reason ?? "No new room was released."));
      setRequest(await api<StandbyRequest>(requestPath(id)));
    });
  }

  function reset() {
    rememberRequest(null);
    setRequest(null);
    const now = Date.now();
    setEarliest(localInputValue(new Date(now)));
    setLatest(localInputValue(new Date(now + 120 * 60_000)));
    setError("");
    setPollError(false);
    setDemoNote("");
  }

  const offer = request?.offer;

  return (
    <div className="booking-grid">
      <section className="panel request-panel" aria-labelledby="request-title">
        <div className="panel-heading">
          <p className="step">01 <span>Request</span></p>
          <h2 id="request-title">What do you need?</h2>
          <p>Set a window that works for your group.</p>
        </div>
        {request ? (
          <div className="request-summary">
            <dl>
              <div><dt>Window</dt><dd>{describeWindow(request.earliest_start, request.latest_end)} Oslo time</dd></div>
              <div><dt>Duration</dt><dd>{request.duration_minutes} minutes</dd></div>
              <div><dt>People</dt><dd>{request.party_size}</dd></div>
              <div><dt>Max total price</dt><dd>{formatPrice.format(request.max_price_ore / 100)} NOK</dd></div>
              {request.equipment.length > 0 && <div><dt>Equipment</dt><dd>{request.equipment.join(", ")}</dd></div>}
              {request.preferences && <div><dt>Preferences</dt><dd>{request.preferences}</dd></div>}
            </dl>
            <button type="button" className="button secondary" onClick={reset} disabled={!!busy}>Start a new request</button>
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
                <input type="number" name="party" defaultValue="4" min="1" max="50" required />
              </label>
              <label>
                Max total price <span className="unit">NOK</span>
                <input type="number" name="budget" defaultValue="500" min="1" max="100000" required />
              </label>
              <label className="equipment">
                <span>Equipment</span>
                <span className="equipment-option"><input name="equipment" type="checkbox" value="screen" defaultChecked /> Screen required</span>
              </label>
              <label className="form-wide">
                Matching preferences <span className="unit">optional</span>
                <input name="preferences" maxLength={500} placeholder="e.g. Earlier is better if possible" />
              </label>
            </div>
          </fieldset>
          <button type="submit" className="button primary" disabled={!!busy || restoring || !earliest || !latest}>
            {busy === "submit" ? "Submitting…" : "Join standby list"}
            <span aria-hidden="true">→</span>
          </button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        )}
      </section>
      <section className="panel status-panel" aria-labelledby="status-title">
        <div className="panel-heading">
          <p className="step">02 <span>Standby</span></p>
          <h2 id="status-title">Your room offer</h2>
          <p>Review a match and book if it works for you.</p>
        </div>
        <div aria-live="polite" aria-atomic="true" className="status-body">
          {!status && (restoring
            ? <EmptyState icon="…" title="Checking standby status">One moment while we check for a saved request.</EmptyState>
            : <EmptyState icon="↗" title="Offers appear here">Join the standby list to start looking for a room.</EmptyState>)}
          {status === "waiting" && <EmptyState icon="…" title="Looking for a room">We’ll check new openings against your request. Keep this page open to see an offer.</EmptyState>}
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
              <div className="offer-top">
                <div>
                  <p className="offer-label">{status === "confirmed" ? "Booked room" : "Room available"}</p>
                  <h3>{offer.room_name}</h3>
                </div>
                <p className="price">{formatPrice.format(offer.price_ore / 100)} <span>NOK</span></p>
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
            <p>Simulate a room becoming available at {venueName}.</p>
            <button type="button" className="button secondary" onClick={release} disabled={!!busy}>
              {busy === "release" ? "Releasing…" : "Release demo room"}
            </button>
            {demoNote && <p className="status-note" role="status">{demoNote}</p>}
          </div>
        )}
      </section>
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
