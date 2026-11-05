import Link from "next/link";
import Standby from "../../standby";

export default async function BookingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="booking-detail">
      <Link className="room-back" href="/bookings"><span aria-hidden="true">←</span> My bookings</Link>
      <div className="booking-detail-heading">
        <p className="room-kicker">My bookings</p>
        <h1>Room request</h1>
      </div>
      <Standby requestId={id} key={id} />
    </main>
  );
}
