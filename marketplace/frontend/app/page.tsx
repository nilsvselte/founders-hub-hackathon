import Browse from "./browse";

export default function Home() {
  return (
    <main className="market-browse">
      <section className="panel request-panel find-room" aria-labelledby="find-title">
        <div className="panel-heading">
          <h2 id="find-title">Find a free meeting room in seconds</h2>
          <a className="button primary" href="/ntnu?demo">Find a room now <span aria-hidden="true">→</span></a>
        </div>
      </section>
      <Browse />
    </main>
  );
}
