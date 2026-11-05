import Link from "next/link";
import Standby from "../standby";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function StandbyPage({ searchParams }: Props) {
  const query = await searchParams;
  const date = typeof query.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(query.date) ? query.date : undefined;
  const guests = typeof query.guests === "string" && /^\d{1,3}$/.test(query.guests) ? Number(query.guests) : 0;

  return (
    <main className="booking-detail">
      <Link className="room-back" href="/marketplace"><span aria-hidden="true">←</span> Browse rooms</Link>
      <div className="booking-detail-heading">
        <p className="room-kicker">Standby matching</p>
        <h1>Find a room for me</h1>
        <p>Set your meeting needs and budget. We’ll look across venues and book a matching room automatically when one opens up.</p>
      </div>
      <Standby searchDate={date} guests={guests >= 1 && guests <= 100 ? guests : undefined} />
    </main>
  );
}
