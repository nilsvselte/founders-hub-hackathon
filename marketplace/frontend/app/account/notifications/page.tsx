"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAccount } from "../../account";
import { api } from "../../market";
import { disablePush, enablePush, getPushState } from "../../push-client";
import styles from "../preferences/preferences.module.css";

type Settings = { room_booked: boolean; occupied_unbooked: boolean; booked_empty: boolean; offer_ready: boolean };
type Kind = keyof Settings;
type DeviceState = "unsupported" | "needs-install" | "denied" | "off" | "on";

const hostKinds: { key: Kind; label: string }[] = [
  { key: "room_booked", label: "A room gets booked" },
  { key: "occupied_unbooked", label: "People in a room that isn't booked" },
  { key: "booked_empty", label: "A booked room is still empty after 10 min" },
];
const bookerKinds: { key: Kind; label: string }[] = [
  { key: "offer_ready", label: "A room frees up for my standby request" },
];

const deviceText: Record<DeviceState, string> = {
  on: "On for this device",
  off: "Off for this device",
  denied: "Blocked on this device. Allow notifications for standbyroom in your phone's settings, then come back.",
  "needs-install": "On iPhone, tap Share → Add to Home Screen, then open standbyroom from your home screen to turn notifications on.",
  unsupported: "This browser can't show notifications. Try the installed app on your phone.",
};

function message(failure: unknown) {
  return failure instanceof Error ? failure.message : "Something went wrong. Please try again.";
}

export default function NotificationsPage() {
  const { account, loading } = useAccount();

  return (
    <main className={styles.page}>
      <p className="identity-kicker">Your account</p>
      <h1 className={styles.title}>Notifications</h1>
      {loading ? <p className={styles.state} role="status">Checking your account…</p> : !account ? (
        <p className={styles.state}><Link className="identity-primary" href="/sign-in?next=%2Faccount%2Fnotifications">Sign in to set notifications</Link></p>
      ) : (
        <div className={styles.form}>
          <DeviceRow />
          <KindToggles key={account.id} isHost={account.role === "host"} />
          {account.role === "renter" && <p className={styles.help}><Link href="/account/preferences">Room preferences</Link></p>}
        </div>
      )}
    </main>
  );
}

function DeviceRow() {
  const [state, setState] = useState<DeviceState>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    getPushState().then((s) => { if (live) setState(s); }).catch(() => { if (live) setState("unsupported"); });
    return () => { live = false; };
  }, []);

  async function turnOn() {
    setBusy(true); setError("");
    try { setState(await enablePush()); } catch (failure) { setError(message(failure)); } finally { setBusy(false); }
  }

  async function turnOff() {
    setBusy(true); setError("");
    try { await disablePush(); setState("off"); } catch (failure) { setError(message(failure)); } finally { setBusy(false); }
  }

  return (
    <section className={styles.group} aria-labelledby="device-heading">
      <h2 id="device-heading">This device</h2>
      <p className={styles.help} role="status">{state ? deviceText[state] : "Checking this device…"}</p>
      {(state === "off" || state === "on") && (
        <div className={styles.actions} style={{ marginTop: 16 }}>
          {state === "off" ? (
            <button type="button" className="identity-primary" disabled={busy} onClick={() => void turnOn()}>{busy ? "Turning on…" : "Turn on notifications"}</button>
          ) : (
            <button type="button" className={styles.secondary} disabled={busy} onClick={() => void turnOff()}>{busy ? "Turning off…" : "Turn off"}</button>
          )}
        </div>
      )}
      {error && <p className="identity-error" role="alert" style={{ marginTop: 8 }}>{error}</p>}
    </section>
  );
}

function KindToggles({ isHost }: { isHost: boolean }) {
  const [settings, setSettings] = useState<Settings>();
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api<Settings>("notifications/settings", { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setSettings(data); })
      .catch((failure) => { if (!controller.signal.aborted) setLoadError(message(failure)); });
    return () => controller.abort();
  }, [attempt]);

  async function change(key: Kind, on: boolean) {
    if (!settings) return;
    const before = settings;
    setSettings({ ...settings, [key]: on });
    setStatus("saving");
    try {
      setSettings(await api<Settings>("notifications/settings", { method: "PUT", body: JSON.stringify({ [key]: on }) }));
      setStatus("saved");
    } catch (failure) {
      setSettings(before);
      setSaveError(`Couldn't save. ${message(failure)}`);
      setStatus("error");
    }
  }

  if (loadError) {
    return (
      <div className={styles.state}>
        <p className="identity-error" role="alert">{loadError}</p>
        <button type="button" className={styles.secondary} onClick={() => { setLoadError(""); setAttempt((n) => n + 1); }}>Try again</button>
      </div>
    );
  }
  if (!settings) return <p className={styles.help} role="status">Loading your notification settings…</p>;

  // An account has one role, so it sees one group.
  const groups = isHost
    ? [{ id: "host", title: "Your rooms", kinds: hostKinds }]
    : [{ id: "booker", title: "Your standby requests", kinds: bookerKinds }];

  return (
    <>
      {groups.map((group) => (
        <section key={group.id} className={styles.group} aria-labelledby={`${group.id}-heading`}>
          <h2 id={`${group.id}-heading`}>{group.title}</h2>
          <div className={styles.fields}>
            {group.kinds.map(({ key, label }) => (
              <label key={key} className={styles.toggle}>
                <span>{label}</span>
                <input type="checkbox" role="switch" checked={settings[key]} onChange={(e) => void change(key, e.target.checked)} />
              </label>
            ))}
          </div>
        </section>
      ))}
      <p className={status === "error" ? "identity-error" : styles.status} role={status === "error" ? "alert" : "status"}>
        {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : status === "error" ? saveError : ""}
      </p>
    </>
  );
}
