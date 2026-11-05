import Browse from "./browse";

export default function Home() {
  return (
    <main className="market-browse">
      <section className="browse-hero" aria-labelledby="browse-title">
        <div className="browse-hero-copy">
          <p className="browse-kicker">The room edit</p>
          <h1 id="browse-title">Make room.</h1>
        </div>
        <p className="browse-index">
          <span>01 / EXPLORE</span>
          <span>Meeting spaces in Norway</span>
        </p>
      </section>
      <Browse />
    </main>
  );
}
