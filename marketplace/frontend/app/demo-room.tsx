import Link from "next/link";

/** The room shown live on stage. Change this one line when the physical demo room is ready. */
export const DEMO_ROOM_ID = "digs-demo-1";
export const DEMO_ROOM_PATH = `/rooms/${DEMO_ROOM_ID}`;

export function DemoRoomLink({ className = "demo-room-link" }: { className?: string }) {
  return (
    <Link className={className} href={DEMO_ROOM_PATH}>
      <span className="demo-room-dot" aria-hidden="true" />
      Live demo room <span aria-hidden="true">→</span>
    </Link>
  );
}
