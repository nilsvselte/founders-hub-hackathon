import Browse from "./browse";
import FindRoom from "./find-room";

export default function Home() {
  return (
    <main className="market-browse">
      <FindRoom>
        <a className="button primary" href="/live/digs-demo-1">Live room now <span aria-hidden="true">→</span></a>
        <a className="button primary" href="/ntnu?demo">Find a room now (NTNU agent) <span aria-hidden="true">→</span></a>
      </FindRoom>
      <p className="browse-standby find-room-browse"><a href="#browse">Or browse all rooms <span aria-hidden="true">↓</span></a></p>
      <div id="browse">
        <Browse />
      </div>
    </main>
  );
}
