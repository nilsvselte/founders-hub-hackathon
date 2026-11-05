"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, money, photo } from "./market";
import type { Room } from "./market";

const categories = ["All spaces", "Meeting room", "Studio", "Workshop", "Boardroom"];
const guestCounts = Array.from({ length: 20 }, (_, index) => index + 1);

const iconPaths = {
  search: "M15.5 15.5 20 20m-2.5-9.5a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z",
  map: "M19.5 10c0 4.6-7.5 10.5-7.5 10.5S4.5 14.6 4.5 10a7.5 7.5 0 1 1 15 0Zm-5 0a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Z",
  guests: "M16 20v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m16 0v-2a4 4 0 0 0-3-3.9M14 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm2-3.8a4 4 0 0 1 0 7.6",
  arrow: "M6 18 18 6m-9 0h9v9",
  grid: "M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z",
  meeting: "M5 8h14v8H5zM8 5v3m8-3v3M8 16v3m8-3v3",
  studio: "M3 19h18M5 15l5-7 3 4 2-3 4 6M7 5h.01",
  workshop: "m4 20 8-8m-3-6 3-3 9 9-3 3Zm-4 6 7 7",
  boardroom: "M7 5h10a4 4 0 0 1 0 14H7A4 4 0 0 1 7 5ZM9 2v3m6-3v3M9 19v3m6-3v3",
};

type IconName = keyof typeof iconPaths;

const categoryIcons: Record<string, IconName> = {
  "All spaces": "grid",
  "Meeting room": "meeting",
  Studio: "studio",
  Workshop: "workshop",
  Boardroom: "boardroom",
};

function Icon({ name }: { name: IconName }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={iconPaths[name]} />
    </svg>
  );
}

function RoomCard({ room }: { room: Room }) {
  const roomPhoto = photo(room.image_key);

  return (
    <article className="room-card">
      <Link href={`/rooms/${encodeURIComponent(room.id)}`} className="room-card-link">
        <div className="room-card-photo">
          {roomPhoto ? (
            <Image src={roomPhoto.src} alt="" fill sizes="(max-width: 560px) 92vw, (max-width: 900px) 45vw, 25vw" />
          ) : (
            <span className="room-photo-placeholder">Photo unavailable</span>
          )}
          {roomPhoto?.isVenuePhoto && <span className="room-photo-label">Venue photo</span>}
          <span className="room-card-kind">{room.kind}</span>
        </div>
        <div className="room-card-body">
          <div className="room-card-top">
            <h3 className="room-card-title">{room.name}</h3>
            <Icon name="arrow" />
          </div>
          <p className="room-card-location">{room.venue} · {room.city}</p>
          <p className="room-card-meta">Up to {room.capacity} {room.capacity === 1 ? "person" : "people"}</p>
          <p className="room-card-price"><strong>{money(room.hourly_rate_ore)}</strong> <span>/ hour</span></p>
        </div>
      </Link>
    </article>
  );
}

export default function Browse() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [retry, setRetry] = useState(0);
  const [location, setLocation] = useState("");
  const [guests, setGuests] = useState("");
  const [filters, setFilters] = useState({ location: "", guests: 0 });
  const [category, setCategory] = useState("All spaces");

  useEffect(() => {
    const controller = new AbortController();
    api<Room[]>("rooms", { signal: controller.signal }).then((list) => {
      if (controller.signal.aborted) return;
      setRooms(list);
      setLoadState("ready");
    }).catch(() => {
      if (!controller.signal.aborted) setLoadState("error");
    });
    return () => controller.abort();
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
  const matches = rooms.filter((room) => {
    const locationText = `${room.city} ${room.venue} ${room.name}`.toLocaleLowerCase();
    const matchesCategory = category === "All spaces"
      || (category.startsWith("venue:") ? room.venue === category.slice(6) : room.kind === category);
    return locationText.includes(searchTerm)
      && room.capacity >= filters.guests
      && matchesCategory;
  }).sort((first, second) => Number(Boolean(photo(second.image_key))) - Number(Boolean(photo(first.image_key))));
  const isFiltered = !!filters.location || filters.guests > 0 || category !== "All spaces";
  const cities = [...new Set(rooms.map((room) => room.city))].sort();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({ location: location.trim(), guests: Number(guests) });
  }

  function reset() {
    setLocation("");
    setGuests("");
    setFilters({ location: "", guests: 0 });
    setCategory("All spaces");
  }

  return (
    <>
      <form className="browse-search" role="search" aria-label="Find rooms" onSubmit={submit}>
        <label className="browse-field">
          <Icon name="map" />
          <span>
            <span>Where</span>
            <input list="room-cities" placeholder="Any city or venue" value={location} onChange={(event) => setLocation(event.target.value)} />
            <datalist id="room-cities">{cities.map((city) => <option key={city} value={city} />)}</datalist>
          </span>
        </label>
        <label className="browse-field">
          <Icon name="guests" />
          <span>
            <span>Guests</span>
            <select value={guests} onChange={(event) => setGuests(event.target.value)}>
              <option value="">Any group size</option>
              {guestCounts.map((count) => <option key={count} value={count}>{count} {count === 1 ? "guest" : "guests"}</option>)}
            </select>
          </span>
        </label>
        <button className="browse-search-button" type="submit"><Icon name="search" /> <span>Search</span></button>
      </form>

      <div className="browse-categories" role="group" aria-label={useVenueFilters ? "Venue" : "Room type"}>
        {options.map(({key, label, icon}) => (
          <button className="browse-category" key={key} type="button" aria-pressed={category === key} onClick={() => setCategory(key)}>
            <Icon name={icon} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <section className="browse-results" aria-labelledby="results-title" aria-busy={loadState === "loading"}>
        <div className="browse-results-heading">
          <div>
            <h2 id="results-title">{isFiltered ? "Search results" : "Explore rooms"}</h2>
            <p className="browse-count" aria-live="polite">
              {loadState === "ready" && `${matches.length} ${matches.length === 1 ? "space" : "spaces"}`}
            </p>
          </div>
          {isFiltered && <button type="button" className="browse-reset" onClick={reset}>Clear filters</button>}
        </div>
        {loadState === "loading" && <p className="browse-empty" role="status">Finding rooms…</p>}
        {loadState === "error" && (
          <div className="browse-empty">
            <p role="alert">Rooms are temporarily unavailable.</p>
            <button type="button" className="browse-reset" onClick={() => { setLoadState("loading"); setRetry(retry + 1); }}>Try again</button>
          </div>
        )}
        {loadState === "ready" && (matches.length ? (
          <div className="room-grid">{matches.map((room) => <RoomCard key={room.id} room={room} />)}</div>
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
