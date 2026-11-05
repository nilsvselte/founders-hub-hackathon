"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAccount } from "../account";
import { api } from "../market";
import styles from "./agent.module.css";

function TokenPanel() {
  const [state, setState] = useState<"active" | "inactive" | "error">();
  const [attempt, setAttempt] = useState(0);
  const [operation, setOperation] = useState<"create" | "revoke">();
  const [token, setToken] = useState<string>();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api<{ active: boolean }>("auth/agent-token", { signal: controller.signal }).then(
      ({ active }) => { if (!controller.signal.aborted) setState(active ? "active" : "inactive"); },
      () => { if (!controller.signal.aborted) setState("error"); },
    );
    return () => controller.abort();
  }, [attempt]);

  function retry() {
    setState(undefined);
    setAttempt((current) => current + 1);
  }

  async function changeToken(action: "create" | "revoke") {
    if (operation) return;
    setOperation(action);
    setToken(undefined);
    setError("");
    setNotice("");
    try {
      if (action === "create") {
        const result = await api<{ token: string }>("auth/agent-token", { method: "POST" });
        setState("active");
        setToken(result.token);
        setNotice("Token ready to copy.");
      } else {
        await api("auth/agent-token", { method: "DELETE" });
        setState("inactive");
        setNotice("Token revoked.");
      }
    } catch {
      setError("Couldn’t update your token. Try again.");
      retry();
    } finally {
      setOperation(undefined);
    }
  }

  async function copyToken() {
    if (!token) return;
    try {
      await navigator.clipboard.writeText(token);
      setNotice("Token copied.");
    } catch {
      setNotice("Select and copy the token manually.");
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="assistant-token">
      <h2 id="assistant-token">Marketplace token</h2>
      <p className={styles.muted}>Your local assistant uses this token to see your room preferences and manage bookings you approve.</p>
      {!state ? <p role="status">Checking your token…</p> : state === "error" ? (
        <>
          <p className="identity-error" role="alert">Couldn’t check your token.</p>
          <button type="button" className="button secondary" onClick={retry}>Try again</button>
        </>
      ) : (
        <>
          <p>{state === "active" ? "Token active. Creating a replacement revokes the current token." : "No active token."}</p>
          <div className={styles.actions}>
            <button type="button" className="identity-primary" disabled={!!operation} onClick={() => void changeToken("create")}>
              {operation === "create" ? "Creating…" : state === "active" ? "Replace token" : "Create token"}
            </button>
            {state === "active" ? (
              <button type="button" className="button secondary" disabled={!!operation} onClick={() => void changeToken("revoke")}>
                {operation === "revoke" ? "Revoking…" : "Revoke token"}
              </button>
            ) : null}
          </div>
        </>
      )}
      {token ? (
        <div className={`identity-form ${styles.token}`}>
          <label>
            Copy this token now. It’s shown once.
            <input aria-label="New marketplace token" value={token} readOnly autoComplete="off" spellCheck={false} />
          </label>
          <div className={styles.actions}>
            <button type="button" className="button secondary" onClick={() => void copyToken()}>Copy token</button>
            <button type="button" className="button secondary" onClick={() => { setToken(undefined); setNotice("Token hidden."); }}>Hide token</button>
          </div>
        </div>
      ) : null}
      {error ? <p className="identity-error" role="alert">{error}</p> : null}
      <p className={styles.status} role="status">{notice}</p>
    </section>
  );
}

export function AgentSettings() {
  const { account, loading } = useAccount();

  if (loading) return <p role="status">Checking your account…</p>;
  if (!account) {
    return (
      <div className={styles.panel}>
        <h2>Set up your renter account</h2>
        <p className={styles.muted}>Sign in to create a token and save your room preferences.</p>
        <div className={styles.actions}>
          <Link className="identity-primary" href="/sign-in?next=%2Fagent">Sign in</Link>
          <Link className="button secondary" href="/register?next=%2Fagent">Create renter account</Link>
        </div>
      </div>
    );
  }
  if (account.role !== "renter") {
    return (
      <div className={styles.panel}>
        <p>Calendar assistant setup is available to renter accounts.</p>
        <Link className={styles.textLink} href="/host">Go to host dashboard <span aria-hidden="true">→</span></Link>
      </div>
    );
  }

  return (
    <div key={account.id} className={styles.settings}>
      <TokenPanel />
      <section className={styles.panel} aria-labelledby="assistant-preferences">
        <h2 id="assistant-preferences">Room preferences</h2>
        <p className={styles.muted}>Set your budget, equipment, and preferred venues to help the assistant compare rooms.</p>
        <Link className={styles.textLink} href="/account/preferences">Edit your preferences <span aria-hidden="true">→</span></Link>
      </section>
    </div>
  );
}
