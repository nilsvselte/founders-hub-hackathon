"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useAccount } from "../../account";
import { api } from "../../market";
import styles from "./preferences.module.css";

type MeetingType = "client_meeting" | "workshop" | "interview" | "team_day" | "board_meeting" | "offsite";

type About = {
  team_name: string;
  what_we_do: string;
  usual_party_size: number | null;
  home_area: string;
  home_lat: number | null;
  home_lon: number | null;
  meeting_types: MeetingType[];
  agent_notes: string;
};

type RoomPreferences = {
  max_hourly_ore: number | null;
  room_kinds: string[];
  equipment: string[];
  preferred_venues: string[];
  avoid_venues: string[];
  max_travel_minutes: number | null;
  wishes: string;
};

type AgentSettings = {
  allow_notifications: boolean;
  notification_channels: ("in_app" | "email")[];
  suggest_for_unroomed_meetings: boolean;
  suggestion_lead_days: 1 | 3 | 7;
  min_attendees_to_suggest: number;
  skip_online_meetings: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
};

type Saved = { about: About; preferences: RoomPreferences; agent: AgentSettings; updated_at: string | null };
type CatalogOptions = { room_kinds: string[]; equipment: string[]; venues: { id: string; name: string; city: string }[] };

const meetingTypes: { value: MeetingType; label: string }[] = [
  { value: "client_meeting", label: "Client meeting" },
  { value: "workshop", label: "Workshop" },
  { value: "interview", label: "Interview" },
  { value: "team_day", label: "Team day" },
  { value: "board_meeting", label: "Board meeting" },
  { value: "offsite", label: "Offsite" },
];

const leadTimes = [{ value: 1, label: "1 day ahead" }, { value: 3, label: "3 days ahead" }, { value: 7, label: "1 week ahead" }] as const;

// Used only when the catalog can't be loaded, so the form still works.
const fallbackOptions: CatalogOptions = {
  room_kinds: ["Boardroom", "Meeting room", "Phone pod", "Quiet room", "Studio", "Workshop"],
  equipment: ["screen", "video conferencing", "whiteboard"],
  venues: [],
};

function message(failure: unknown) {
  return failure instanceof Error ? failure.message : "Something went wrong. Please try again.";
}

function capitalise(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function toggle<T>(list: T[], value: T) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function numberOrNull(value: string) {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function PreferencesPage() {
  const { account, loading } = useAccount();

  return (
    <main className={styles.page}>
      <p className="identity-kicker">Your account</p>
      <h1 className={styles.title}>Your preferences</h1>
      <p className={styles.intro}>The booking agent uses these to pick rooms for meetings in your calendar.</p>
      {loading ? <p className={styles.state} role="status">Checking your account…</p> : !account ? (
        <p className={styles.state}><Link className="identity-primary" href="/sign-in?next=%2Faccount%2Fpreferences">Sign in to set your preferences</Link></p>
      ) : account.role === "host" ? (
        <p className={styles.state}>Preferences are for renter accounts. <Link href="/host">Go to your host dashboard</Link></p>
      ) : (
        <PreferencesForm key={account.id} />
      )}
    </main>
  );
}

function PreferencesForm() {
  const [saved, setSaved] = useState<Saved>();
  const [draft, setDraft] = useState<Saved>();
  const [options, setOptions] = useState<CatalogOptions>();
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState("");
  // The price field holds NOK as typed; it's converted to øre on save.
  const [priceNok, setPriceNok] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api<Saved>("me/preferences", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setSaved(data);
        setDraft(data);
        setPriceNok(data.preferences.max_hourly_ore ? String(data.preferences.max_hourly_ore / 100) : "");
      })
      .catch((failure) => { if (!controller.signal.aborted) setLoadError(message(failure)); });
    api<CatalogOptions>("catalog/options", { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setOptions(data); })
      .catch(() => { if (!controller.signal.aborted) setOptions(fallbackOptions); });
    return () => controller.abort();
  }, [attempt]);

  const dirty = useMemo(() => {
    if (!saved || !draft) return false;
    const savedPrice = saved.preferences.max_hourly_ore ? String(saved.preferences.max_hourly_ore / 100) : "";
    return JSON.stringify(saved) !== JSON.stringify(draft) || priceNok !== savedPrice;
  }, [saved, draft, priceNok]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const setAbout = useCallback(<K extends keyof About>(key: K, value: About[K]) => {
    setStatus("idle");
    setDraft((current) => current && { ...current, about: { ...current.about, [key]: value } });
  }, []);
  const setPrefs = useCallback(<K extends keyof RoomPreferences>(key: K, value: RoomPreferences[K]) => {
    setStatus("idle");
    setDraft((current) => current && { ...current, preferences: { ...current.preferences, [key]: value } });
  }, []);

  const setAgent = useCallback(<K extends keyof AgentSettings>(key: K, value: AgentSettings[K]) => {
    setStatus("idle");
    setDraft((current) => current && { ...current, agent: { ...current.agent, [key]: value } });
  }, []);

  if (loadError) return (
    <div className={styles.state}>
      <p className="identity-error" role="alert">Couldn’t load your preferences. {loadError}</p>
      <button type="button" className={styles.secondary} onClick={() => { setLoadError(""); setAttempt((n) => n + 1); }}>Try again</button>
    </div>
  );
  if (!draft || !options) return <p className={styles.state} role="status">Loading your preferences…</p>;

  const { about, preferences, agent } = draft;
  const suggestionsOff = !agent.suggest_for_unroomed_meetings;
  const notificationsOff = !agent.allow_notifications;
  // Keep saved values visible even if the catalog no longer lists them.
  const kindOptions = [...new Set([...options.room_kinds, ...preferences.room_kinds])];
  const equipmentOptions = [...new Set([...options.equipment, ...preferences.equipment])];

  function venueChoice(id: string) {
    return preferences.preferred_venues.includes(id) ? "prefer" : preferences.avoid_venues.includes(id) ? "avoid" : "";
  }

  function setVenue(id: string, choice: string) {
    setPrefs("preferred_venues", choice === "prefer" ? [...new Set([...preferences.preferred_venues, id])] : preferences.preferred_venues.filter((v) => v !== id));
    setPrefs("avoid_venues", choice === "avoid" ? [...new Set([...preferences.avoid_venues, id])] : preferences.avoid_venues.filter((v) => v !== id));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    const nok = numberOrNull(priceNok);
    if (priceNok.trim() !== "" && (nok === null || nok <= 0)) {
      setStatus("error");
      setSaveError("Enter a price above 0 NOK, or leave it empty.");
      return;
    }
    if ((about.home_lat === null) !== (about.home_lon === null)) {
      setStatus("error");
      setSaveError("Give both latitude and longitude, or neither.");
      return;
    }
    if (!agent.quiet_hours_start !== !agent.quiet_hours_end) {
      setStatus("error");
      setSaveError("Give quiet hours both a start and an end, or leave both empty.");
      return;
    }
    setStatus("saving");
    setSaveError("");
    try {
      const body = { about, agent, preferences: { ...preferences, max_hourly_ore: nok === null ? null : Math.round(nok * 100) } };
      const next = await api<Saved>("me/preferences", { method: "PUT", body: JSON.stringify(body) });
      setSaved(next);
      setDraft(next);
      setPriceNok(next.preferences.max_hourly_ore ? String(next.preferences.max_hourly_ore / 100) : "");
      setStatus("saved");
    } catch (failure) {
      setStatus("error");
      setSaveError(`Couldn’t save. ${message(failure)}`);
    }
  }

  return (
    <form className={styles.form} onSubmit={(event) => void save(event)} noValidate>
      <Group title="About you" note="Context for the agent. Your name and email are never shared with it.">
        <label className={styles.field}>Team or company
          <input value={about.team_name} maxLength={100} onChange={(e) => setAbout("team_name", e.target.value)} placeholder="Fjordline Analytics" autoComplete="organization" />
        </label>
        <label className={styles.field}>What you do
          <textarea value={about.what_we_do} maxLength={300} rows={2} onChange={(e) => setAbout("what_we_do", e.target.value)} placeholder="Four-person data consultancy; we meet clients in town most weeks." />
        </label>
        <div className={styles.pair}>
          <label className={styles.field}>Usual meeting size
            <input type="number" inputMode="numeric" min={1} max={100} value={about.usual_party_size ?? ""} onChange={(e) => setAbout("usual_party_size", numberOrNull(e.target.value))} placeholder="4" />
          </label>
          <label className={styles.field}>Home or office area
            <input value={about.home_area} maxLength={100} onChange={(e) => setAbout("home_area", e.target.value)} placeholder="Solsiden, Trondheim" />
          </label>
        </div>
        <details className={styles.disclosure} open={about.home_lat !== null || undefined}>
          <summary>Add a map point for travel times</summary>
          <p className={styles.help}>A rough point is enough, like a street corner. The agent sees it rounded to about 1 km.</p>
          <div className={styles.pair}>
            <label className={styles.field}>Latitude
              <input type="number" inputMode="decimal" step="any" min={-90} max={90} value={about.home_lat ?? ""} onChange={(e) => setAbout("home_lat", numberOrNull(e.target.value))} placeholder="63.434" />
            </label>
            <label className={styles.field}>Longitude
              <input type="number" inputMode="decimal" step="any" min={-180} max={180} value={about.home_lon ?? ""} onChange={(e) => setAbout("home_lon", numberOrNull(e.target.value))} placeholder="10.410" />
            </label>
          </div>
        </details>
        <Chips legend="Typical meetings">
          {meetingTypes.map(({ value, label }) => (
            <Chip key={value} label={label} checked={about.meeting_types.includes(value)} onChange={() => setAbout("meeting_types", toggle(about.meeting_types, value))} />
          ))}
        </Chips>
        <label className={styles.field}>Notes for the agent
          <textarea value={about.agent_notes} maxLength={1000} rows={3} onChange={(e) => setAbout("agent_notes", e.target.value)} placeholder="Client meetings need a proper table and a screen. Internal syncs can be anywhere quiet." />
        </label>
      </Group>

      <Group title="Room preferences" note="Price, equipment and avoided venues are hard limits. The rest helps rank rooms.">
        <div className={styles.pair}>
          <label className={styles.field}>Max price per hour
            <span className={styles.suffix}>
              <input type="number" inputMode="decimal" min={1} step="any" value={priceNok} onChange={(e) => { setStatus("idle"); setPriceNok(e.target.value); }} placeholder="450" />
              <span aria-hidden="true">NOK</span>
            </span>
          </label>
          <label className={styles.field}>Max travel time
            <span className={styles.suffix}>
              <input type="number" inputMode="numeric" min={1} max={240} value={preferences.max_travel_minutes ?? ""} onChange={(e) => setPrefs("max_travel_minutes", numberOrNull(e.target.value))} placeholder="15" />
              <span aria-hidden="true">min</span>
            </span>
          </label>
        </div>
        <Chips legend="Room types you like">
          {kindOptions.map((kind) => (
            <Chip key={kind} label={kind} checked={preferences.room_kinds.includes(kind)} onChange={() => setPrefs("room_kinds", toggle(preferences.room_kinds, kind))} />
          ))}
        </Chips>
        <Chips legend="Must-have equipment">
          {equipmentOptions.map((item) => (
            <Chip key={item} label={capitalise(item)} checked={preferences.equipment.includes(item)} onChange={() => setPrefs("equipment", toggle(preferences.equipment, item))} />
          ))}
        </Chips>
        {options.venues.length > 0 && (
          <fieldset className={styles.venues}>
            <legend>Venues</legend>
            <ul>
              {options.venues.map((venue) => (
                <li key={venue.id}>
                  <span className={styles.venueName}>{venue.name}<span>{venue.city}</span></span>
                  <select aria-label={`Preference for ${venue.name}`} value={venueChoice(venue.id)} onChange={(e) => setVenue(venue.id, e.target.value)}>
                    <option value="">No preference</option>
                    <option value="prefer">Prefer</option>
                    <option value="avoid">Avoid</option>
                  </select>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
        <label className={styles.field}>Other wishes
          <textarea value={preferences.wishes} maxLength={1000} rows={2} onChange={(e) => setPrefs("wishes", e.target.value)} placeholder="Quiet rooms with daylight. No phone pods for client meetings." />
        </label>
      </Group>

      <Group title="Agent and notifications" note="The agent only suggests rooms. It never books without your yes.">
        <Toggle label="Suggest rooms for meetings without one" help="When a calendar meeting has no room, the agent may suggest some." checked={agent.suggest_for_unroomed_meetings} onChange={(on) => setAgent("suggest_for_unroomed_meetings", on)} />
        <fieldset className={styles.dependent} disabled={suggestionsOff}>
          <legend className="sr-only">Suggestion settings</legend>
          <div className={styles.pair}>
            <label className={styles.field}>Suggest
              <select value={agent.suggestion_lead_days} onChange={(e) => setAgent("suggestion_lead_days", Number(e.target.value) as AgentSettings["suggestion_lead_days"])}>
                {leadTimes.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className={styles.field}>Only for meetings of at least
              <span className={styles.suffix}>
                <input type="number" inputMode="numeric" min={1} max={100} value={agent.min_attendees_to_suggest} onChange={(e) => setAgent("min_attendees_to_suggest", numberOrNull(e.target.value) ?? 1)} />
                <span aria-hidden="true">people</span>
              </span>
            </label>
          </div>
          <Toggle label="Skip online meetings" help="Meetings with a video link don’t need a room." checked={agent.skip_online_meetings} onChange={(on) => setAgent("skip_online_meetings", on)} />
        </fieldset>
        <Toggle label="Notify me" help="Let the agent tell you when it has a suggestion. Nothing is sent yet; this saves your choice." checked={agent.allow_notifications} onChange={(on) => setAgent("allow_notifications", on)} />
        <fieldset className={styles.dependent} disabled={notificationsOff}>
          <legend className="sr-only">Notification settings</legend>
          <Chips legend="Notify me by">
            <Chip label="In the app" checked={agent.notification_channels.includes("in_app")} onChange={() => setAgent("notification_channels", toggle(agent.notification_channels, "in_app"))} />
            <Chip label="Email" checked={agent.notification_channels.includes("email")} onChange={() => setAgent("notification_channels", toggle(agent.notification_channels, "email"))} />
          </Chips>
          <div className={styles.pair}>
            <label className={styles.field}>Quiet from
              <input type="time" value={agent.quiet_hours_start?.slice(0, 5) ?? ""} onChange={(e) => setAgent("quiet_hours_start", e.target.value || null)} />
            </label>
            <label className={styles.field}>Quiet until
              <input type="time" value={agent.quiet_hours_end?.slice(0, 5) ?? ""} onChange={(e) => setAgent("quiet_hours_end", e.target.value || null)} />
            </label>
          </div>
          <p className={styles.help}>No notifications between these times, Oslo time. Leave empty for none.</p>
        </fieldset>
      </Group>

      <div className={styles.actions}>
        <button type="submit" className="identity-primary" disabled={status === "saving"}>Save preferences</button>
        <span className={status === "error" ? "identity-error" : styles.status} role={status === "error" ? "alert" : "status"}>
          {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : status === "error" ? saveError : dirty ? "Unsaved changes" : ""}
        </span>
      </div>
    </form>
  );
}

function Group({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  const id = `group-${title.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <section className={styles.group} aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      <p className={styles.help}>{note}</p>
      <div className={styles.fields}>{children}</div>
    </section>
  );
}

function Toggle({ label, help, checked, onChange }: { label: string; help: string; checked: boolean; onChange: (on: boolean) => void }) {
  return (
    <label className={styles.toggle}>
      <span>{label}<small>{help}</small></span>
      <input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

function Chips({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className={styles.chips}>
      <legend>{legend}</legend>
      <div>{children}</div>
    </fieldset>
  );
}

function Chip({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className={styles.chip}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      {label}
    </label>
  );
}
