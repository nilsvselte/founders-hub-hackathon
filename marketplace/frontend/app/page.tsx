import Browse from "./browse";
import { DemoRoomLink } from "./demo-room";
import FindRoom from "./find-room";

export default function Home() {
  return (
    <main className="market-browse">
      <FindRoom>
        <DemoRoomLink />
      </FindRoom>
      <p className="browse-standby find-room-browse"><a href="#browse">Or browse all rooms <span aria-hidden="true">↓</span></a></p>
      <div id="browse">
        <Browse />
      </div>
    </main>
  );
}
