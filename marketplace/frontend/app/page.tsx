import Browse from "./browse";
import FindRoom from "./find-room";

export default function Home() {
  return (
    <main className="market-browse">
      <FindRoom />
      <Browse />
    </main>
  );
}
