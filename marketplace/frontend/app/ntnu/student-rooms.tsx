"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useAccount } from "../account";
import { api, ApiError } from "../market";
import styles from "./ntnu.module.css";

type Mode = "live" | "demo";
type Status = { configured: boolean; connected: boolean; connectable: boolean; label?: string; demo_available: boolean };
type Room = { proposal_id: string; id: string; name: string; capacity: number; building: string; campus: string; start: string; end: string };
type Search = { mode: Mode; provider: string; message: string; rooms: Room[]; request: { date?: string; start_time?: string; duration_minutes?: number; party_size?: number; campus?: string } };
type Confirmation = { mode: Mode; confirmed: boolean; booking_id: string; room: string; start: string; end: string };
type Booking = { id: string; name: string; rooms?: { id: string; name?: string }[]; start?: string; end?: string; dates?: { date: string }; tid?: string };
type ChatMessage = { role: "user" | "assistant"; text: string };

const example = "Find a group room for 6 people in Realfagbygget tomorrow at 08:00 for 1 hour.";
const initial: ChatMessage = { role: "assistant", text: "A place for your next study session. Tell me your campus, when you need a room, for how long, and how many people are coming." };

function Arrow({ direction = "right" }: { direction?: "right" | "up" }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={direction === "up" ? { transform: "rotate(-90deg)" } : undefined}><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function time(value: string) {
  return new Date(value).toLocaleTimeString("en-GB", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit" });
}

function day(value: string) {
  return new Date(value).toLocaleDateString("en-GB", { timeZone: "Europe/Oslo", weekday: "short", day: "numeric", month: "short" });
}

function RoomSketch() {
  return <svg className={styles.sketch} viewBox="0 0 310 190" fill="none" aria-hidden="true">
    <path d="m22 111 133-75 133 75-133 75-133-75Z" fill="var(--accent-tint)" stroke="var(--line)" />
    <path d="M22 111V39l133-30 133 30v72M155 9v81M22 39l133 51 133-51" stroke="var(--control-line)" />
    <path d="m104 104 51-29 51 29-51 30-51-30Z" fill="var(--paper)" stroke="var(--accent)" strokeWidth="1.5" />
    <path d="M104 104v20m102-20v20m-51 10v19" stroke="var(--accent)" strokeWidth="1.5" />
    <path d="m77 96 18-10 15 9-18 10-15-9Zm127-18 18 10-15 9-18-10 15-9Zm-83 67 18-10 15 9-18 10-15-9Zm72-10 18-10 15 9-18 10-15-9Z" stroke="var(--ink-soft)" />
    <path d="m47 57 34 13v28L47 85V57Zm177 9 35-14v29l-35 14V66Z" stroke="var(--line)" />
    <circle cx="263" cy="22" r="15" fill="var(--accent)" /><path d="m257 22 4 4 8-9" stroke="var(--page)" strokeWidth="1.6" />
  </svg>;
}

function Experience({ mode, changeMode }: { mode: Mode; changeMode: (mode: Mode) => void }) {
  const { account } = useAccount();
  const [status, setStatus] = useState<Status>();
  const [statusError, setStatusError] = useState("");
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([initial]);
  const [draft, setDraft] = useState("");
  const [result, setResult] = useState<Search>();
  const [selected, setSelected] = useState<Room>();
  const [confirmation, setConfirmation] = useState<Confirmation>();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [bookingError, setBookingError] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>();
  const demo = mode === "demo";

  useEffect(() => {
    const controller = new AbortController();
    api<Status>(`ntnu/status?mode=${mode}`, { signal: controller.signal }).then(
      (next) => {
        if (controller.signal.aborted) return;
        setStatus(next); setStatusError(""); setNeedsSignIn(false);
      },
      (failure) => {
        if (controller.signal.aborted) return;
        setNeedsSignIn(failure instanceof ApiError && failure.status === 401);
        setStatusError(failure instanceof ApiError && failure.status === 401 ? "Sign in to connect your NTNU account." : "Couldn’t check the NTNU connection.");
      },
    );
    return () => controller.abort();
  }, [mode, attempt]);

  async function loadBookings() {
    setBookingError("");
    try {
      const data = await api<{ bookings: Booking[] }>(`ntnu/bookings?mode=${mode}`);
      setBookings(data.bookings);
    } catch {
      setBookingError("Couldn’t load your NTNU bookings. Check again before retrying a booking.");
    }
  }

  useEffect(() => {
    if (status?.connected) void loadBookings();
    // Each Experience is recreated when its account or mode changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.connected]);

  async function connect() {
    setBusy("connect"); setError("");
    try {
      const data = await api<{ url: string }>("ntnu/connect", { method: "POST" });
      window.location.assign(data.url);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Couldn’t start NTNU sign-in.");
      setBusy(undefined);
    }
  }

  async function send(event?: FormEvent, prompt = draft) {
    event?.preventDefault();
    if (!prompt.trim() || busy || !status?.connected) return;
    setBusy("search"); setError(""); setDraft(""); setSelected(undefined); setConfirmation(undefined);
    setResult(undefined);
    setMessages((current) => [...current, { role: "user", text: prompt }]);
    try {
      const data = await api<Search>("ntnu/agent", { method: "POST", body: JSON.stringify({ mode, message: prompt }) });
      setResult(data);
      setMessages((current) => [...current, { role: "assistant", text: data.message }]);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The assistant couldn’t complete that search.");
      setDraft(prompt);
    } finally {
      setBusy(undefined);
    }
  }

  async function book() {
    if (!selected || busy) return;
    setBusy("book"); setError("");
    try {
      const data = await api<Confirmation>("ntnu/book", { method: "POST", body: JSON.stringify({ mode, proposal_id: selected.proposal_id }) });
      if (!data.confirmed || data.mode !== mode) throw new Error("No confirmed reservation was returned. Check your bookings before retrying.");
      setConfirmation(data); setSelected(undefined); setResult(undefined);
      await loadBookings();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The booking result is uncertain. Check your bookings.");
    } finally { setBusy(undefined); }
  }

  async function cancel(bookingId: string) {
    if (busy) return;
    setBusy(bookingId); setBookingError("");
    try {
      await api("ntnu/cancel", { method: "POST", body: JSON.stringify({ mode, booking_id: bookingId }) });
      if (confirmation?.booking_id === bookingId) setConfirmation(undefined);
      await loadBookings();
    } catch (failure) {
      setBookingError(failure instanceof Error ? failure.message : "Couldn’t confirm cancellation.");
    } finally { setBusy(undefined); }
  }

  return <main className={styles.page}>
    <header className={styles.hero}>
      <div>
        <p className={styles.eyebrow}><span className={styles.square} /> NTNU / STUDENT ROOMS</p>
        <h1>A little less searching.<br /><em>A lot more studying.</em></h1>
        <p className={styles.lead}>Your study group. Your campus. A room that fits.<br className={styles.desktopBreak} /> Tell the assistant what you need, and take it from there.</p>
      </div>
      <div className={styles.heroArt}><RoomSketch /><span>Make room for a good idea.</span></div>
    </header>

    <div className={styles.modeBar}>
      <div className={styles.modeSwitch} role="group" aria-label="Booking mode">
        <button type="button" aria-pressed={!demo} disabled={!!busy} onClick={() => changeMode("live")}>NTNU rooms</button>
        <button type="button" aria-pressed={demo} disabled={!!busy} onClick={() => changeMode("demo")}>Try the demo <Arrow /></button>
      </div>
      <p className={styles.modeLabel}><span className={status?.connected ? styles.dotGood : styles.dot} />{demo ? "Demo · sample rooms only" : status?.connected ? "Your NTNU account is connected" : "Student connection in preparation"}</p>
    </div>

    {demo && <p className={styles.demoNotice}>You’re trying a guided demo with sample rooms. No real NTNU rooms are booked.</p>}
    {!demo && !status?.connected && <section className={styles.connection} aria-label="Your NTNU connection">
      <div className={styles.connectionIcon} aria-hidden="true">N</div>
      <div><h2>{needsSignIn ? "Your account, your campus." : "Connect once. Find your space."}</h2>
        <p>{statusError || (status && !status.configured ? "NTNU sign-in and booking are being connected. Explore the experience with the demo while we get things ready." : status ? "Connect your own NTNU account to search and manage the rooms you can book." : "Checking the NTNU connection…")}</p></div>
      {needsSignIn ? <Link className="button primary" href="/sign-in?next=%2Fntnu">Sign in <Arrow /></Link> : status?.configured && status.connectable ? <button className="button primary" onClick={() => void connect()} disabled={!!busy}>Connect NTNU <Arrow /></button> : statusError ? <button className="button secondary" onClick={() => setAttempt((value) => value + 1)}>Try again</button> : <button className="button secondary" disabled>NTNU sign-in coming soon</button>}
    </section>}
    {demo && statusError && <p className={styles.error} role="alert">{statusError} <button onClick={() => setAttempt((value) => value + 1)}>Try again</button></p>}

    <div className={styles.workspace}>
      <section className={styles.assistant} aria-labelledby="ntnu-assistant-heading">
        <header className={styles.panelHead}><div><span className={styles.agentGlyph} aria-hidden="true">✳</span><div><h2 id="ntnu-assistant-heading">Your campus assistant</h2><p>{demo ? "Guided demo" : "NTNU room finder"}</p></div></div><span className={styles.smallLabel}>01 / ASK</span></header>
        <div className={styles.messages} role="log" aria-label="Room assistant conversation" aria-live="polite" aria-relevant="additions">
          {messages.map((message, index) => <div className={message.role === "user" ? styles.userMessage : styles.assistantMessage} key={index}><span>{message.role === "user" ? "YOU" : "ASSISTANT"}</span><p>{message.text}</p></div>)}
          {busy === "search" && <p className={styles.searching} role="status">Checking your request and looking for rooms…</p>}
        </div>
        {messages.length === 1 && <div className={styles.suggestions}><p>Not sure where to start?</p><button type="button" disabled={!status?.connected || !!busy} onClick={() => void send(undefined, example)}>6 people · Realfagbygget · tomorrow at 08:00 <Arrow /></button></div>}
        <form className={styles.composer} onSubmit={(event) => void send(event)}>
          <label className={styles.composerLabel} htmlFor="ntnu-message">What does your study group need?</label>
          <div><textarea id="ntnu-message" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="A group room for 6, tomorrow at 08:00 for an hour…" rows={2} maxLength={2000} disabled={!status?.connected || !!busy} /><button type="submit" aria-label="Send room request" disabled={!draft.trim() || !status?.connected || !!busy}><Arrow direction="up" /></button></div>
          <p>Times are in Oslo time. You review the room before booking.</p>
        </form>
        {error && <p className={styles.error} role="alert">{error}</p>}
      </section>

      <aside className={styles.rightColumn}>
        {confirmation ? <section className={styles.confirmation} role="status"><span className={styles.confirmIcon} aria-hidden="true">✓</span><p className={styles.eyebrow}>{demo ? "DEMO RESERVATION" : "BOOKING CONFIRMED"}</p><h2>You’ve got a room.</h2><h3>{confirmation.room}</h3><p>{day(confirmation.start)} · {time(confirmation.start)}–{time(confirmation.end)}</p><p className={styles.reference}>Reference: {confirmation.booking_id}</p>{demo && <p className={styles.muted}>This is a sample reservation, not an NTNU booking.</p>}</section> : selected ? <section className={styles.review} aria-labelledby="review-heading"><p className={styles.eyebrow}>03 / REVIEW</p><h2 id="review-heading">Make it yours.</h2><h3>{selected.name}</h3><p>{selected.building}</p><dl><div><dt>When</dt><dd>{day(selected.start)}</dd></div><div><dt>Time</dt><dd>{time(selected.start)}–{time(selected.end)}</dd></div><div><dt>Room capacity</dt><dd>{selected.capacity} people</dd></div><div><dt>Campus</dt><dd>{selected.campus}</dd></div></dl><button className="button primary" disabled={!!busy} onClick={() => void book()}>{busy === "book" ? "Checking and booking…" : demo ? "Confirm demo booking" : "Confirm booking"}<Arrow /></button><p className={styles.muted}>{demo ? "Only sample availability will change." : "Availability is checked again before the reservation is confirmed."}</p></section> : <section className={styles.how}><p className={styles.eyebrow}>SPACE TO THINK</p><h2>One less thing<br />on the group chat.</h2><ol><li><span>01</span><div><h3>Tell us the plan.</h3><p>Campus, time, group size. Just ask.</p></div></li><li><span>02</span><div><h3>Find your fit.</h3><p>Compare rooms that match your session.</p></div></li><li><span>03</span><div><h3>Get back to studying.</h3><p>Review, book, and meet your group.</p></div></li></ol><div className={styles.note}><span aria-hidden="true">↗</span><p>Already using TP?<br /><a href="https://tp.educloud.no/ntnu/app/rombestilling/" target="_blank" rel="noreferrer">Open NTNU room booking</a></p></div></section>}
      </aside>
    </div>

    {result && result.rooms.length > 0 && <section className={styles.results} aria-labelledby="room-results"><div className={styles.resultsHead}><div><p className={styles.eyebrow}>02 / CHOOSE</p><h2 id="room-results">Room for your group.</h2></div><p>{result.rooms.length} {demo ? "sample " : ""}rooms · {result.request.party_size} people</p></div><div className={styles.roomGrid}>{result.rooms.map((room, index) => <article className={selected?.proposal_id === room.proposal_id ? `${styles.room} ${styles.selected}` : styles.room} key={room.proposal_id}><div className={styles.roomVisual}><span>{String(index + 1).padStart(2, "0")}</span><RoomSketch /><p>{demo ? "SAMPLE ROOM" : "GROUP ROOM"}</p></div><div className={styles.roomBody}><p className={styles.smallLabel}>{room.campus}</p><h3>{room.name}</h3><p>{room.building} · up to {room.capacity} people</p><div className={styles.roomTime}>{day(room.start)}<span>{time(room.start)}–{time(room.end)}</span></div><button className="button secondary" disabled={!!busy} aria-pressed={selected?.proposal_id === room.proposal_id} onClick={() => { setSelected(room); setConfirmation(undefined); }}>{selected?.proposal_id === room.proposal_id ? "Selected" : "Review this room"}<Arrow /></button></div></article>)}</div></section>}

    <section className={styles.bookings} aria-labelledby="ntnu-bookings"><div className={styles.resultsHead}><div><p className={styles.eyebrow}>YOUR STUDY SESSIONS</p><h2 id="ntnu-bookings">{demo ? "Demo bookings" : "My NTNU bookings"}</h2></div>{status?.connected && <button className="button secondary" disabled={!!busy} onClick={() => void loadBookings()}>Refresh</button>}</div>{bookingError && <p className={styles.error} role="alert">{bookingError}</p>}{bookings.length ? <ul>{bookings.map((booking) => <li key={booking.id}><div><h3>{booking.name}</h3><p>{booking.start ? `${day(booking.start)} · ${time(booking.start)}–${booking.end ? time(booking.end) : ""}` : `${booking.dates?.date ?? ""} ${booking.tid ?? ""}`}</p><span className={styles.reference}>{booking.id}</span></div><button className="button secondary" disabled={!!busy} onClick={() => void cancel(booking.id)}>{busy === booking.id ? "Cancelling…" : "Cancel booking"}</button></li>)}</ul> : <p className={styles.empty}>{status?.connected ? "No reservations here yet. Start with a room request above." : "Your reservations will appear here when you connect your NTNU account."}</p>}</section>
    <footer className={styles.footer}><span>standbyroom <span aria-hidden="true">/</span> NTNU</span><p>An experimental feature for student study sessions.</p></footer>
  </main>;
}

export default function StudentRooms() {
  const { account } = useAccount();
  const [mode, setMode] = useState<Mode>("live");
  return <Experience key={`${mode}:${account?.id ?? "anonymous"}`} mode={mode} changeMode={setMode} />;
}
