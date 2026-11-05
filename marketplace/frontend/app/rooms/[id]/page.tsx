import RoomDetail from "./room-detail";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function RoomPage({ params, searchParams }: Props) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const searchDate = typeof query.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(query.date) ? query.date : undefined;
  const guests = typeof query.guests === "string" && /^\d{1,3}$/.test(query.guests) ? Number(query.guests) : 0;
  return <RoomDetail roomId={id} searchDate={searchDate} guests={guests || undefined} key={id} />;
}
