"use client";

// Booker's first screen: set criteria → "Find room" → ranked eligible rooms with a why line.
// Eligibility, quote and ranking come from the backend's POST /suggestions; booking reuses POST /standby-requests.
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { DemoGuestButton, useAccount } from "./account";
import { ApiError, api, money, photo } from "./market";
import type { Room } from "./market";
import { osloDateTime, osloInstant } from "./oslo-time";

type Suggestion = {
  room_id: string;
  room_name: string;
  venue: string | null;
  city: string;
  capacity: number;
  start_at: string;
  end_at: string;
  price_ore: number;
  reason: string;
};

type Criteria = {
  date: string; from: string; to: string; duration: number;
  people: number; equipment: string[]; maxPrice: number | null;
};

const formatTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Oslo", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});
const formatEnd = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

const MAX_SLOTS = 6;

function slotStarts(c: Criteria): Date[] {
  const start = osloInstant({ date: c.date, time: c.from });
  const end = osloInstant({ date: c.date, time: c.to });
  const starts: Date[] = [];
  if (!start || !end) return starts;
  const now = Date.now() + 60_000;
  for (let t = start.getTime(); t + c.duration * 60_000 <= end.getTime() && starts.length < MAX_SLOTS; t += 30 * 60_000) {
    if (t > now) starts.push(new Date(t));
  }
  return starts;
}

export default function FindRoom({ children }: { children?: ReactNode }) {
  const { account, loading } = useAccount();
  const router = useRouter();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [criteria, setCriteria] = useState<Criteria | null>(null);
  const [today, setToday] = useState("");
  const [state, setState] = useState<"idle" | "searching" | "done" | "error">("idle");
  const [results, setResults] = useState<Suggestion[]>([]);
  const [error, setError] = useState("");
  const [booking, setBooking] = useState<string | null>(null);

  useEffect(() => {
    const now = osloDateTime(Date.now());
    setToday(now.date);
    const hour = Math.min(Number(now.time?.slice(0, 2) ?? 9) + 1, 20);
    setCriteria({
      date: now.date, from: `${String(hour).padStart(2, "0")}:00`, to: `${String(Math.min(hour + 3, 23)).padStart(2, "0")}:00`,
      duration: 30, people: 4, equipment: [], maxPrice: null,
    });
    api<Room[]>("rooms").then(setRooms).catch(() => {});
  }, []);

  const equipmentOptions = [...new Set(rooms.flatMap((room) => room.equipment ?? []))].sort().slice(0, 8);
  const photos = new Map(rooms.map((room) => [room.id, photo(room.image_key)]));

  function set<K extends keyof Criteria>(key: K, value: Criteria[K]) {
    setCriteria((current) => (current ? { ...current, [key]: value } : current));
  }

  async function find(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!criteria) return;
    setError("");
    const from = osloInstant({ date: criteria.date, time: criteria.from });
    const until = osloInstant({ date: criteria.date, time: criteria.to });
    const durationMs = criteria.duration * 60_000;
    const earliest = new Date(Math.max(from?.getTime() ?? 0, Date.now() + 60_000));
    if (!from || !until || until.getTime() - earliest.getTime() < durationMs) {
      setError("Choose a future time window at least as long as the meeting.");
      return;
    }
    setState("searching");
    try {
      const suggest = (start: Date, end: Date, duration?: number) => api<{ suggestions: Suggestion[] }>("suggestions", {
        method: "POST",
        body: JSON.stringify({
          start_at: start.toISOString(),
          end_at: end.toISOString(),
          duration_minutes: duration,
          party_size: Math.max(2, criteria.people),
          equipment: criteria.equipment,
          ...(criteria.maxPrice ? { max_price_ore: Math.round(criteria.maxPrice * 100) } : {}),
        }),
      });
      const result = await suggest(earliest, until, criteria.duration).catch(async (failure) => {
        if (!(failure instanceof ApiError && failure.status === 422)) throw failure;
        // Older API deployments accept only exact meeting times.
        const batches = await Promise.all(slotStarts(criteria).map((start) =>
          suggest(start, new Date(start.getTime() + durationMs)).catch((slotFailure) => {
            if (slotFailure instanceof ApiError && slotFailure.status === 422) return { suggestions: [] };
            throw slotFailure;
          }),
        ));
        const seen = new Set<string>();
        const suggestions = batches.flatMap((batch) => batch.suggestions)
          .filter((room) => !seen.has(room.room_id) && seen.add(room.room_id));
        return { suggestions: suggestions.slice(0, 6) };
      });
      setResults(result.suggestions);
      setState("done");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Something went wrong. Please try again.");
      setState("error");
    }
  }

  async function request(body: Record<string, unknown>, key: string) {
    setBooking(key);
    setError("");
    try {
      const next = await api<{ id: string }>("standby-requests", { method: "POST", body: JSON.stringify(body) });
      router.push(`/bookings/${encodeURIComponent(next.id)}`);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Something went wrong. Please try again.");
      setBooking(null);
    }
  }

  function book(s: Suggestion) {
    if (!criteria) return;
    void request({
      room_id: s.room_id, auto_confirm: true, earliest_start: s.start_at, latest_end: s.end_at,
      duration_minutes: criteria.duration, party_size: criteria.people, equipment: criteria.equipment,
      max_price_ore: s.price_ore, preferences: "",
    }, s.room_id);
  }

  function standby() {
    if (!criteria?.maxPrice) return;
    const earliest = osloInstant({ date: criteria.date, time: criteria.from });
    const latest = osloInstant({ date: criteria.date, time: criteria.to });
    if (!earliest || !latest) return;
    void request({
      room_id: null, auto_confirm: true,
      earliest_start: earliest.toISOString(),
      latest_end: latest.toISOString(),
      duration_minutes: criteria.duration, party_size: criteria.people, equipment: criteria.equipment,
      max_price_ore: Math.round(criteria.maxPrice * 100), preferences: "",
    }, "standby");
  }

  const standbyHref = `/standby?${new URLSearchParams({ date: criteria?.date ?? "", guests: String(criteria?.people ?? "") })}`;

  return (
    <section className="panel request-panel find-room" aria-labelledby="find-title">
      <div className="panel-heading">
        <h2 id="find-title">Find a room</h2>
        <p>Set what you need. We rank the open rooms that fit, best first. Times are Oslo time.</p>
        {children}
      </div>
      {!criteria ? <p className="status-note" role="status">Loading…</p> : (
        <form onSubmit={find}>
          <fieldset disabled={state === "searching" || !!booking}>
            <legend className="sr-only">Room criteria</legend>
            <div className="form-grid">
              <label className="form-wide">Date
                <input type="date" value={criteria.date} min={today || undefined} onChange={(e) => set("date", e.target.value)} required />
              </label>
              <label>From
                <input type="time" step={1800} value={criteria.from} onChange={(e) => set("from", e.target.value)} required />
              </label>
              <label>Until
                <input type="time" step={1800} value={criteria.to} onChange={(e) => set("to", e.target.value)} required />
              </label>
              <label>Duration
                <select value={criteria.duration} onChange={(e) => set("duration", Number(e.target.value))}>
                  {[30, 60, 90, 120, 180].map((m) => <option key={m} value={m}>{m < 60 ? `${m} min` : `${m / 60} h`}</option>)}
                </select>
              </label>
              <label>People
                <input type="number" inputMode="numeric" min={1} max={100} value={criteria.people}
                  onChange={(e) => set("people", Math.max(1, Math.min(100, Number(e.target.value) || 1)))} required />
              </label>
              <label className="form-wide">Max total price <span className="unit">NOK, optional</span>
                <input type="number" inputMode="numeric" min={1} max={100000} placeholder="Any price" value={criteria.maxPrice ?? ""}
                  onChange={(e) => set("maxPrice", e.target.value ? Number(e.target.value) : null)} />
              </label>
              {equipmentOptions.length > 0 && (
                <div className="form-wide equipment">
                  <span>Equipment</span>
                  <div className="find-room-equipment">
                    {equipmentOptions.map((item) => (
                      <label key={item} className="equipment-option">
                        <input type="checkbox" checked={criteria.equipment.includes(item)}
                          onChange={(e) => set("equipment", e.target.checked ? [...criteria.equipment, item] : criteria.equipment.filter((x) => x !== item))} />
                        {item}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </fieldset>
          {!loading && !account ? (
            <DemoGuestButton label="Find room now" />
          ) : account && account.role !== "renter" ? (
            <p className="status-note">Finding rooms needs a renter account.</p>
          ) : (
            <button type="submit" className="button primary" disabled={state === "searching"}>
              {state === "searching" ? "Finding rooms…" : "Find room"} <span aria-hidden="true">→</span>
            </button>
          )}
          {error && <p className="error" role="alert">{error}</p>}
        </form>
      )}

      {state === "done" && (
        <div className="find-room-results" aria-live="polite">
          {results.length ? (
            <ol className="find-room-list">
              {results.map((s, index) => {
                const roomPhoto = photos.get(s.room_id);
                return (
                  <li key={s.room_id} className="find-room-item">
                    <div className="find-room-photo">
                      {roomPhoto ? <Image src={roomPhoto.src} alt="" fill sizes="96px" /> : <span aria-hidden="true">{index + 1}</span>}
                    </div>
                    <div className="find-room-body">
                      <h3>{index === 0 && <span className="find-room-best">Best fit · </span>}{s.room_name}</h3>
                      <p className="find-room-meta">{[s.venue, s.city].filter(Boolean).join(" · ")} · {formatTime.format(new Date(s.start_at))}–{formatEnd.format(new Date(s.end_at))}</p>
                      <p className="find-room-why">{s.reason}</p>
                      <div className="find-room-actions">
                        <strong>{money(s.price_ore)}</strong>
                        <button type="button" className="button secondary" disabled={!!booking} onClick={() => book(s)}>
                          {booking === s.room_id ? "Booking…" : "Book"}
                        </button>
                        <Link className="find-room-details" href={`/rooms/${encodeURIComponent(s.room_id)}?date=${criteria?.date ?? ""}`}>Details</Link>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="browse-empty">
              <p>No open room fits right now.</p>
              <Link href="/#browse">Browse all listed rooms</Link>
              {criteria?.maxPrice ? (
                <button type="button" onClick={standby} disabled={!!booking}>
                  {booking === "standby" ? "Sending…" : "Leave a standby request with these criteria"}
                </button>
              ) : (
                <Link href={standbyHref}>Leave a standby request <span aria-hidden="true">→</span></Link>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
