import Browse from "./browse";
import FindRoom from "./find-room";

export default function Home() {
  return (
    <main className="market-browse">
      <FindRoom>
        <a className="button primary" href="/ntnu?demo">Find a room now <span aria-hidden="true">→</span></a>
      </FindRoom>
      <p className="browse-standby find-room-browse"><a href="#browse">Or browse all rooms <span aria-hidden="true">↓</span></a></p>
      <div id="browse">
        <Browse />
      </div>
    </main>
  );
}
