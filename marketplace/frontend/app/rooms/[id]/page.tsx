import RoomDetail from "./room-detail";

export default async function RoomPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RoomDetail roomId={id} key={id} />;
}
