"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, money, photo } from "./market";
import type { Room } from "./market";
import { osloDateTime } from "./oslo-time";

const categories = ["All spaces", "Meeting room", "Studio", "Workshop", "Boardroom", "Event space"];
const maximumGuests = 100;
const emptySearch = { location: "", date: "", guests: 0 };
const allSpaces = "All spaces";
type Search = typeof emptySearch;
const displayDate = new Intl.DateTimeFormat("en-GB", {
  timeZone: "UTC",
  day: "numeric",
  month: "short",
});

const iconPaths = {
  search: "M15.5 15.5 20 20m-2.5-9.5a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z",
  map: "M19.5 10c0 4.6-7.5 10.5-7.5 10.5S4.5 14.6 4.5 10a7.5 7.5 0 1 1 15 0Zm-5 0a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Z",
  calendar: "M7 3v4m10-4v4M4 10h16M6 5h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z",
  guests: "M16 20v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m16 0v-2a4 4 0 0 0-3-3.9M14 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm2-3.8a4 4 0 0 1 0 7.6",
  grid: "M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z",
  meeting: "M5 8h14v8H5zM8 5v3m8-3v3M8 16v3m8-3v3",
  studio: "M3 19h18M5 15l5-7 3 4 2-3 4 6M7 5h.01",
  workshop: "m4 20 8-8m-3-6 3-3 9 9-3 3Zm-4 6 7 7",
  boardroom: "M7 5h10a4 4 0 0 1 0 14H7A4 4 0 0 1 7 5ZM9 2v3m6-3v3M9 19v3m6-3v3",
  event: "M4 20V9l8-5 8 5v11M4 20h16M9 20v-5h6v5M8 11h.01M12 11h.01M16 11h.01",
};

type IconName = keyof typeof iconPaths;

const categoryIcons: Record<string, IconName> = {
  "All spaces": "grid",
  "Meeting room": "meeting",
  Studio: "studio",
  Workshop: "workshop",
  Boardroom: "boardroom",
  "Event space": "event",
};

function Icon({ name }: { name: IconName }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={iconPaths[name]} />
    </svg>
  );
}

function RoomCard({ room, searchParams }: { room: Room; searchParams: string }) {
  const roomPhoto = photo(room.image_key);
  const href = `/rooms/${encodeURIComponent(room.id)}${searchParams ? `?${searchParams}` : ""}`;

  return (
    <article className="room-card">
      <Link href={href} className="room-card-link">
        <div className="room-card-photo">
          {roomPhoto ? (
            <Image src={roomPhoto.src} alt="" fill sizes="(max-width: 560px) 92vw, (max-width: 900px) 45vw, 25vw" />
          ) : (
            <span className="room-photo-placeholder">Photo unavailable</span>
          )}
          {roomPhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
        </div>
        <div className="room-card-body">
          <h2 className="room-card-title">{room.name}</h2>
          <p className="room-card-location">{room.venue} · {room.city}</p>
          <p className="room-card-meta">Up to {room.capacity} {room.capacity === 1 ? "person" : "people"}</p>
          <p className="room-card-price"><strong>{money(room.hourly_rate_ore)}</strong> <span>/ hour</span></p>
        </div>
      </Link>
    </article>
  );
}

function readSearch(params: Pick<URLSearchParams, "get">, today: string) {
  const date = params.get("date") ?? "";
  const parsedDate = new Date(date);
  const guests = Number(params.get("guests") ?? 0);
  return {
    location: (params.get("location") ?? "").trim(),
    date: /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(parsedDate.getTime())
      && parsedDate.toISOString().slice(0, 10) === date && date >= today ? date : "",
    guests: Number.isInteger(guests) && guests >= 1 && guests <= maximumGuests ? guests : 0,
  };
}

function searchQuery(search: Search, category: string) {
  const params = new URLSearchParams();
  if (search.location) params.set("location", search.location);
  if (search.date) params.set("date", search.date);
  if (search.guests) params.set("guests", String(search.guests));
  if (category !== allSpaces) params.set("category", category);
  return params.toString();
}

export default function Browse() {
  return (
    <Suspense fallback={<p className="browse-empty" role="status">Finding rooms…</p>}>
      <BrowseResults />
    </Suspense>
  );
}

function BrowseResults() {
  const params = useSearchParams();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [retry, setRetry] = useState(0);
  const [draft, setDraft] = useState(emptySearch);
  const [today, setToday] = useState("");
  const filters = readSearch(params, today);
  const { location, date, guests } = filters;
  const category = params.get("category") || allSpaces;

  useEffect(() => {
    setToday(osloDateTime(Date.now()).date);
  }, []);

  useEffect(() => setDraft({ location, date, guests }), [location, date, guests]);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setLoadState("error");
    }, 12_000);
    api<Room[]>("rooms", { signal: controller.signal }).then((list) => {
      if (controller.signal.aborted) return;
      setRooms(list);
      setLoadState("ready");
    }).catch(() => {
      if (!controller.signal.aborted) setLoadState("error");
    }).finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [retry]);

  const searchTerm = filters.location.toLocaleLowerCase();
  const availableKinds = categories.filter((kind) => kind !== "All spaces" && rooms.some((room) => room.kind === kind));
  const useVenueFilters = loadState === "ready" && availableKinds.length < 2;
  const venueNames = [...new Set(rooms.map((room) => room.venue))].sort();
  const options: Array<{ key: string; label: string; icon: IconName }> = [
    { key: "All spaces", label: "All spaces", icon: "grid" },
    ...(useVenueFilters
      ? venueNames.map((name) => ({ key: `venue:${name}`, label: name, icon: "map" as const }))
      : availableKinds.map((kind) => ({ key: kind, label: kind, icon: categoryIcons[kind] }))),
  ];
  const activeCategory = options.some(({ key }) => key === category) ? category : allSpaces;
  const matches = rooms.filter((room) => {
    const locationText = `${room.city} ${room.venue} ${room.name}`.toLocaleLowerCase();
    const matchesCategory = activeCategory === allSpaces
      || (activeCategory.startsWith("venue:") ? room.venue === activeCategory.slice(6) : room.kind === activeCategory);
    return locationText.includes(searchTerm)
      && room.capacity >= filters.guests
      && matchesCategory;
  }).sort((first, second) => Number(Boolean(photo(second.image_key))) - Number(Boolean(photo(first.image_key))));
  const isFiltered = !!filters.location || filters.guests > 0 || activeCategory !== allSpaces;
  const hasSearch = isFiltered || !!filters.date;
  const cities = [...new Set(rooms.map((room) => room.city))].sort();
  const guestLimit = Math.min(maximumGuests, Math.max(20, draft.guests, ...rooms.map(({ capacity }) => capacity)));
  const guestCounts = Array.from({ length: guestLimit }, (_, index) => index + 1);
  const searchParams = searchQuery(filters, activeCategory);
  const standbyParams = searchQuery({ ...filters, location: "" }, allSpaces);

  function updateSearch(next: Search, nextCategory: string) {
    const query = searchQuery(next, nextCategory);
    window.history.replaceState(null, "", query ? `/?${query}` : "/");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = { ...draft, location: draft.location.trim() };
    setDraft(next);
    updateSearch(next, activeCategory);
  }

  function reset() {
    setDraft(emptySearch);
    updateSearch(emptySearch, allSpaces);
  }

  return (
    <>
      <form className="browse-search" role="search" aria-label="Find rooms" onSubmit={submit}>
        <label className="browse-field">
          <Icon name="map" />
          <span>
            <span>Where</span>
            <input name="location" list="room-cities" placeholder="Any city or venue" value={draft.location}
              onChange={(event) => setDraft({ ...draft, location: event.target.value })} />
            <datalist id="room-cities">{cities.map((city) => <option key={city} value={city} />)}</datalist>
          </span>
        </label>
        <label className="browse-field browse-field-date">
          <Icon name="calendar" />
          <span>
            <span>When</span>
            <input name="date" type="date" min={today || undefined} max="9999-12-31" value={draft.date}
              onChange={(event) => setDraft({ ...draft, date: event.target.value })} />
          </span>
        </label>
        <label className="browse-field">
          <Icon name="guests" />
          <span>
            <span>Guests</span>
            <select name="guests" value={draft.guests || ""}
              onChange={(event) => setDraft({ ...draft, guests: Number(event.target.value) })}>
              <option value="">Add guests</option>
              {guestCounts.map((count) => <option key={count} value={count}>{count} {count === 1 ? "guest" : "guests"}</option>)}
            </select>
          </span>
        </label>
        <button className="browse-search-button" type="submit" aria-label="Search"><Icon name="search" /> <span>Search</span></button>
      </form>

      <div className="browse-categories" role="group" aria-label={useVenueFilters ? "Venue" : "Room type"}>
        {options.map(({key, label, icon}) => (
          <button className="browse-category" key={key} type="button" aria-pressed={activeCategory === key} onClick={() => updateSearch(filters, key)}>
            <Icon name={icon} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <section className="browse-results" aria-labelledby="results-title" aria-busy={loadState === "loading"}>
        <div className="browse-results-heading">
          <div>
            <h1 id="results-title">{isFiltered ? "Search results" : "Explore meeting rooms"}</h1>
            <p className="browse-count" aria-live="polite">
              {loadState === "ready" && `${matches.length} ${matches.length === 1 ? "room" : "rooms"}`}
              {filters.date && (
                <span className="browse-date-summary"> · Selected date: {displayDate.format(new Date(filters.date))}</span>
              )}
            </p>
          </div>
          {hasSearch && <button type="button" className="browse-reset" onClick={reset}>Clear filters</button>}
        </div>
        <p className="browse-standby">
          Flexible about the venue? <Link href={standbyParams ? `/standby?${standbyParams}` : "/standby"}>Find a room for me <span aria-hidden="true">→</span></Link>
        </p>
        {loadState === "loading" && <p className="browse-empty" role="status">Finding rooms…</p>}
        {loadState === "error" && (
          <div className="browse-empty">
            <p role="alert">Rooms are temporarily unavailable.</p>
            <button type="button" className="browse-reset" onClick={() => { setLoadState("loading"); setRetry((value) => value + 1); }}>Try again</button>
          </div>
        )}
        {loadState === "ready" && (matches.length ? (
          <div className="room-grid">{matches.map((room) => <RoomCard key={room.id} room={room} searchParams={searchParams} />)}</div>
        ) : (
          <div className="browse-empty">
            <p>{isFiltered ? "No rooms match those filters." : "There are no rooms to browse yet."}</p>
            {isFiltered && <button type="button" className="browse-reset" onClick={reset}>Show all spaces</button>}
          </div>
        ))}
      </section>
    </>
  );
}
