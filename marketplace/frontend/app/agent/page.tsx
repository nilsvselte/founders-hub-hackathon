import type { Metadata } from "next";
import Link from "next/link";
import { AgentSettings } from "./agent-settings";
import styles from "./agent.module.css";

export const metadata: Metadata = { title: "Calendar assistant · standbyroom" };

const setupCommand = "claude mcp add --transport stdio standbyroom -- uv --directory /absolute/path/to/repo/marketplace/agent run --locked --env-file .env python -m mcp_server.server";

export default function AgentPage() {
  return (
    <main className={`booking-page ${styles.page}`}>
      <div className={styles.intro}>
        <p className="identity-kicker">Book with Claude</p>
        <h1>Calendar assistant</h1>
        <p>Ask Claude to find rooms for upcoming meetings without a location. You review each room, time, and price before booking.</p>
        <Link className={styles.textLink} href="/standby">Make a manual standby request <span aria-hidden="true">→</span></Link>
      </div>

      <section className={styles.panel} aria-labelledby="assistant-setup">
        <h2 id="assistant-setup">Connect your assistant</h2>
        <ol className={styles.steps}>
          <li>Enable the <a href="https://support.claude.com/en/articles/10166901-use-google-workspace-connectors">Google Calendar connector in Claude</a>.</li>
          <li>Create a marketplace token below. Put it in your local <code>marketplace/agent/.env</code> as <code>MARKETPLACE_API_TOKEN</code>.</li>
          <li>Add the standbyroom tools to Claude, then ask it to find a room for an upcoming meeting.</li>
        </ol>
        <details className={styles.details}>
          <summary>Claude Code setup command</summary>
          <p>Run this from a terminal after replacing the example path with your checkout. The local tools default to <code>http://127.0.0.1:8001</code>. Set <code>MARKETPLACE_API_URL</code> in the same file if your backend uses a different address.</p>
          <pre className={styles.command}><code>{setupCommand}</code></pre>
        </details>
        <p className={styles.muted}>Calendar access lives in Claude. The marketplace uses the meeting time, headcount, and an optional rough area to look for rooms.</p>
      </section>

      <AgentSettings />
    </main>
  );
}
