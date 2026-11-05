"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api } from "./market";

export type AccountRole = "renter" | "host";
export type Account = { id: string; name: string; email: string; role: AccountRole };

type AccountContextValue = {
  account: Account | null;
  loading: boolean;
  refresh: () => Promise<Account | null>;
  setAccount: (account: Account | null) => void;
};

const AccountContext = createContext<AccountContextValue | null>(null);

export function AccountProvider({ children }: { children: ReactNode }) {
  const [account, updateAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const revision = useRef(0);

  const setAccount = useCallback((next: Account | null) => {
    revision.current += 1;
    updateAccount(next);
    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    const version = ++revision.current;
    const current = await api<Account>("auth/me").catch(() => null);
    if (version === revision.current) {
      updateAccount(current);
      setLoading(false);
    }
    return current;
  }, []);

  useEffect(() => {
    void refresh();
    return () => { revision.current += 1; };
  }, [refresh]);

  return (
    <AccountContext.Provider value={{ account, loading, refresh, setAccount }}>
      {children}
    </AccountContext.Provider>
  );
}

export function useAccount() {
  const context = useContext(AccountContext);
  if (!context) throw new Error("AccountProvider is required");
  return context;
}

export function MarketHeader() {
  const { account, loading, setAccount } = useAccount();
  const router = useRouter();
  const pathname = usePathname();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  const primaryPath = account?.role === "host" ? "/host" : "/bookings";

  async function signOut() {
    setError("");
    setSigningOut(true);
    try {
      await api("auth/logout", { method: "POST" });
      setAccount(null);
      router.replace("/");
    } catch {
      setError("Couldn’t sign out. Please try again.");
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <header className="market-header">
      <div className="market-header-inner">
        <Link className="market-wordmark" href="/" aria-label="Roomline marketplace">
          <span className="market-mark" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M4.5 19.5v-15h15v10m-15-3h9v8m0-5h6m-6 5h6" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" strokeLinecap="round" />
            </svg>
          </span>
          Roomline
        </Link>
        <nav className="market-nav" aria-label="Marketplace">
          <Link href="/" aria-current={pathname === "/" ? "page" : undefined}>Browse rooms</Link>
          {account ? (
            <Link href={primaryPath} aria-current={pathname.startsWith(primaryPath) ? "page" : undefined}>
              {account.role === "host" ? "Host dashboard" : "My bookings"}
            </Link>
          ) : !loading ? (
            <Link href="/register?role=host">Rent out a room</Link>
          ) : null}
        </nav>
        <div className="market-session">
          {account ? (
            <>
              <span className="market-user" title={account.name}>{account.name.trim().split(/\s+/)[0]}</span>
              <button className="market-signout" type="button" onClick={() => void signOut()} disabled={signingOut}>
                {signingOut ? "Signing out…" : "Sign out"}
              </button>
            </>
          ) : !loading ? (
            <Link className="market-login" href="/sign-in">Sign in</Link>
          ) : null}
          {error && <span className="identity-error" role="alert">{error}</span>}
        </div>
      </div>
    </header>
  );
}

function safeNext(value?: string) {
  if (!value?.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u0020]/.test(value)) {
    return undefined;
  }
  const origin = "https://roomline.invalid";
  const url = new URL(value, origin);
  if (url.origin !== origin || url.pathname.startsWith("//")) return undefined;
  return url.pathname + url.search + url.hash;
}

function isHostDestination(path?: string) {
  return path === "/host" || (path?.startsWith("/host/") ?? false);
}

function destination(account: Account, next?: string) {
  const path = next?.split(/[?#]/, 1)[0];
  if (account.role === "host") return next && isHostDestination(path) ? next : "/host";
  return next && !isHostDestination(path) && path !== "/sign-in" && path !== "/register" ? next : "/";
}

export function AccountForm({
  mode,
  next: rawNext,
  initialRole = "renter",
}: {
  mode: "login" | "register";
  next?: string;
  initialRole?: AccountRole;
}) {
  const register = mode === "register";
  const { account, loading, setAccount } = useAccount();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const next = safeNext(rawNext);
  const [roleChoice, setRoleChoice] = useState<{ entry: string; role: AccountRole }>();
  const entry = `${initialRole}:${next ?? ""}`;
  const entryRole = isHostDestination(next?.split(/[?#]/, 1)[0]) ? "host" : initialRole;
  const role = roleChoice?.entry === entry ? roleChoice.role : entryRole;
  const alternateNext = next ?? (register && role === "host" ? "/host" : undefined);
  const alternate = `${register ? "/sign-in" : "/register"}${alternateNext ? `?next=${encodeURIComponent(alternateNext)}` : ""}`;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const credentials = {
        email: String(form.get("email") ?? "").trim(),
        password: String(form.get("password") ?? ""),
      };
      const current = await api<Account>(`auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(register ? { ...credentials, name: String(form.get("name") ?? "").trim(), role } : credentials),
      });
      setAccount(current);
      router.replace(destination(current, next));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Couldn’t complete that request. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="identity-page">
      <section className="identity-card" aria-labelledby="identity-title">
        <p className="identity-kicker">Your account</p>
        <h1 id="identity-title">{register ? "Create an account" : "Welcome back"}</h1>
        <p className="identity-intro">{register ? "Choose how you’ll use Roomline." : "Sign in to manage rooms and reservations."}</p>
        {loading ? <p role="status">Checking your account…</p> : account ? (
          <>
            <p>You’re signed in as <strong>{account.name}</strong>.</p>
            <Link href={destination(account, next)} className="identity-primary">Continue <span aria-hidden="true">→</span></Link>
          </>
        ) : (
          <>
            <form className="identity-form" onSubmit={(event) => void submit(event)}>
              {register && (
                <>
                  <fieldset className="identity-roles">
                    <legend>I want to</legend>
                    <label><input type="radio" name="role" value="renter" checked={role === "renter"} onChange={() => setRoleChoice({ entry, role: "renter" })} /> Book rooms</label>
                    <label><input type="radio" name="role" value="host" checked={role === "host"} onChange={() => setRoleChoice({ entry, role: "host" })} /> Host rooms</label>
                  </fieldset>
                  <label>Full name<input name="name" autoComplete="name" maxLength={100} required /></label>
                </>
              )}
              <label>Email address<input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
              <label>
                Password
                <input name="password" type="password" autoComplete={register ? "new-password" : "current-password"} minLength={register ? 12 : undefined} maxLength={128} required />
                {register && <small>Use at least 12 characters.</small>}
              </label>
              {error && <p className="identity-error" role="alert">{error}</p>}
              <button className="identity-primary" type="submit" disabled={busy}>
                {busy ? (register ? "Creating account…" : "Signing in…") : register ? "Create account" : "Sign in"}
                <span aria-hidden="true">→</span>
              </button>
            </form>
            <p className="identity-switch">
              {register ? "Already have an account?" : "New to Roomline?"}{" "}
              <Link href={alternate}>{register ? "Sign in" : "Create an account"}</Link>
            </p>
          </>
        )}
      </section>
    </main>
  );
}
