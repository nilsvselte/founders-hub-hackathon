"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { api, money } from "./market";
import type { Room } from "./market";
import { dayMs, osloDateTime, osloInstant, upcomingRoomStart } from "./oslo-time";
import styles from "./quote-preview.module.css";

type Quote = {
  price_ore: number;
  hourly_rate_ore: number;
  base_hourly_rate_ore: number;
  reason: string;
};

const presets = [
  { id: "business", label: "Weekday morning", time: "11:00" },
  { id: "evening", label: "Weekday evening", time: "18:00" },
  { id: "weekend", label: "Weekend", time: "11:00" },
] as const;
type Preset = (typeof presets)[number];
type Selection = { date: string; time: string; preset?: Preset["id"] };
type QuoteRequest = { path: string };
type QuoteResult = { request: QuoteRequest; quote: Quote } | { request: QuoteRequest; error: string };

function nextPreset(preset: Preset): Selection {
  const now = Date.now();
  const today = Date.parse(`${osloDateTime(now).date}T00:00:00Z`);
  for (let offset = 0; offset <= 7; offset += 1) {
    const day = new Date(today + offset * dayMs);
    const isWeekend = day.getUTCDay() === 0 || day.getUTCDay() === 6;
    if (isWeekend !== (preset.id === "weekend")) continue;
    const choice = { date: day.toISOString().slice(0, 10), time: preset.time, preset: preset.id };
    const instant = osloInstant(choice);
    if (instant && instant.getTime() > now) return choice;
  }
  return { date: "", time: "" };
}

export default function QuotePreview({ room, searchDate }: { room: Room; searchDate?: string }) {
  const headingId = useId();
  const [selection, setSelection] = useState<Selection>({ date: "", time: "" });
  const [duration, setDuration] = useState(60);
  const [result, setResult] = useState<QuoteResult | null>(null);
  const [retry, setRetry] = useState(0);
  const instant = osloInstant(selection);
  const past = instant !== null && instant.getTime() <= Date.now();
  const startAt = past ? undefined : instant?.toISOString();
  const query = startAt ? new URLSearchParams({ start_at: startAt, duration_minutes: String(duration) }) : null;
  const path = query ? `rooms/${encodeURIComponent(room.id)}/quote?${query}` : null;
  const request = useMemo(() => path ? { path } : null, [path]);
  const visibleResult = result?.request === request ? result : null;

  useEffect(() => {
    const start = upcomingRoomStart(searchDate);
    setSelection(start ? osloDateTime(start.getTime()) : nextPreset(presets[0]));
  }, [searchDate]);

  useEffect(() => {
    if (!request) return;
    const controller = new AbortController();
    let timeout: number | undefined;
    const timer = window.setTimeout(() => {
      timeout = window.setTimeout(() => {
        controller.abort();
        setResult({ request, error: "The price estimate took too long." });
      }, 8_000);
      api<Quote>(request.path, { signal: controller.signal })
        .then((quote) => {
          if (!controller.signal.aborted) setResult({ request, quote });
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) {
            setResult({
              request,
              error: error instanceof Error ? error.message : "Couldn’t load a price estimate.",
            });
          }
        })
        .finally(() => window.clearTimeout(timeout));
    }, 140);

    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [request, retry]);

  return (
    <section className={styles.preview} aria-labelledby={headingId}>
      <div className={styles.intro}>
        <h2 id={headingId}>Price estimate</h2>
        <p>Compare rates for different times. All times are in Oslo.</p>
      </div>
      <div className={styles.presets} role="group" aria-label="Compare prices by time">
        {presets.map((preset) => (
          <button
            type="button"
            key={preset.id}
            aria-pressed={selection.preset === preset.id}
            onClick={() => setSelection(nextPreset(preset))}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <div className={styles.fields}>
        <label>
          Date
          <input
            type="date"
            value={selection.date}
            onChange={(event) => setSelection({ date: event.target.value, time: selection.time })}
          />
        </label>
        <label>
          Start time
          <input
            type="time"
            value={selection.time}
            onChange={(event) => setSelection({ date: selection.date, time: event.target.value })}
          />
        </label>
        <label>
          Duration
          <select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
            {[30, 60, 90, 120, 180].map((minutes) => <option key={minutes} value={minutes}>{minutes} min</option>)}
          </select>
        </label>
      </div>
      <div className={styles.result} aria-live="polite" aria-atomic="true">
        {visibleResult && "quote" in visibleResult ? (
          <>
            <p className={styles.total}><strong>{money(visibleResult.quote.price_ore)}</strong> <span>estimated total</span></p>
            <p>{visibleResult.quote.reason}</p>
          </>
        ) : visibleResult && "error" in visibleResult ? (
          <p className={styles.error}>
            {visibleResult.error}{" "}
            <button type="button" onClick={() => { setResult(null); setRetry((value) => value + 1); }}>Try again</button>
          </p>
        ) : request ? (
          <p>Updating estimate…</p>
        ) : past ? (
          <p>Choose a start time in the future.</p>
        ) : (
          <p>{selection.date && selection.time ? "Choose a valid Oslo time." : "Choose a date and start time."}</p>
        )}
      </div>
      <p className={styles.note}>An estimate doesn’t reserve the room. Your offer shows the final price.</p>
    </section>
  );
}
