import type { Metadata } from "next";
import Standby from "./standby";

// The venue comes from the API at request time, so the page isn't prerendered at build.
export const dynamic = "force-dynamic";

type Venue = { id: string; operator: string; name: string; location: string };

const fallbackVenue: Venue = { id: "digs", operator: "Mesh", name: "Digs", location: "Digs, Trondheim" };
// Monogram strokes for the brand mark, drawn on a 25 × 25 grid.
const brandGlyphs: Record<string, string> = {
  digs: "M7 17V8l5.5 6L18 8v9",
  kowork: "M8.5 7.5v10m8-10-6 5.5m1.5-1.5 4.5 6",
  brighten: "M8.5 7.5v10h4.5a2.6 2.6 0 0 0 0-5.2H8.5m0 0h4a2.4 2.4 0 0 0 0-4.8h-4",
};

// Venue photos shown in the hero. Venues without one get the drawn room plan.
const heroPhotos: Record<string, { src: string; alt: string }> = {
  brighten: { src: "/venues/brighten.webp", alt: "Brighten's glass-walled meeting room on Bakklandet" },
};

const apiUrl = (process.env.MARKETPLACE_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

async function loadVenue(): Promise<Venue> {
  try {
    const response = await fetch(`${apiUrl}/venue`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (response.ok) return (await response.json()) as Venue;
  } catch {
    // Fall back to the default venue so the page still renders while the API starts.
  }
  return fallbackVenue;
}

export async function generateMetadata(): Promise<Metadata> {
  const venue = await loadVenue();
  return {
    title: `${venue.operator} Meeting Rooms`,
    description: `A standby marketplace for meeting rooms at ${venue.location}.`,
  };
}

function RoomPlan() {
  return (
    <svg className="room-plan" viewBox="0 0 360 198" fill="none" aria-hidden="true">
      <defs>
        <pattern id="plan-grid" width="16" height="16" patternUnits="userSpaceOnUse">
          <path d="M16 0H0V16" stroke="currentColor" opacity=".12" />
        </pattern>
      </defs>
      <rect width="360" height="198" fill="url(#plan-grid)" />
      <path d="M23 40V24h16m282 0h16v16M23 158v16h16m282 0h16v-16" stroke="currentColor" opacity=".35" />
      <path d="M254 130v25H92V43h162v56m0 31h-31v-31c17 0 31 14 31 31Z" stroke="currentColor" strokeWidth="1.4" />
      <rect x="129" y="75" width="82" height="47" rx="10" fill="currentColor" fillOpacity=".13" stroke="currentColor" />
      <path d="M145 75V65h18v10m14 0V65h18v10m-50 47v10h18v-10m14 0v10h18v-10M129 91h-10v16h10m82-16h10v16h-10" stroke="currentColor" />
      <path d="M105 73v50" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M254 64h27m-10 34h48m-32 7h24" stroke="currentColor" opacity=".45" strokeDasharray="3 4" />
      <circle cx="290" cy="64" r="9" fill="currentColor" opacity=".19" />
      <circle cx="290" cy="64" r="3.5" fill="currentColor" />
    </svg>
  );
}

export default async function Home() {
  const venue = await loadVenue();
  return (
    <>
      <header className="masthead">
        <div className="shell masthead-inner">
          <div className="brand">
            <svg width="25" height="25" viewBox="0 0 25 25" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="23" height="23" rx="5" fill="currentColor" />
              <path d={brandGlyphs[venue.id] ?? brandGlyphs.digs} stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>{venue.operator} <span className="brand-secondary">/ Meeting rooms</span></span>
          </div>
          <div className="location">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M19 10c0 5-7 10-7 10s-7-5-7-10a7 7 0 1 1 14 0Z" stroke="currentColor" strokeWidth="1.7" />
              <circle cx="12" cy="10" r="2" stroke="currentColor" strokeWidth="1.7" />
            </svg>
            {venue.location}
          </div>
        </div>
      </header>
      <main className="shell">
        <section className="hero" aria-labelledby="page-title">
          <div>
            <p className="eyebrow"><span className="live-dot" /> Standby booking</p>
            <h1 id="page-title">Meeting space,<br />at short notice.</h1>
            <p className="hero-copy">Tell us what your team needs. When a room opens up at {venue.name}, we’ll look for a match and show you the price before you book.</p>
          </div>
          {heroPhotos[venue.id] ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img className="hero-photo" src={heroPhotos[venue.id].src} alt={heroPhotos[venue.id].alt} width={1200} height={900} />
          ) : (
            <RoomPlan />
          )}
        </section>
        <Standby venueName={venue.name} />
      </main>
    </>
  );
}
