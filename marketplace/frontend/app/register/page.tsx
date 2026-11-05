import { AccountForm } from "../account";

export default async function RegisterPage({ searchParams }: { searchParams: Promise<{ next?: string | string[]; role?: string | string[] }> }) {
  const params = await searchParams;
  return <AccountForm mode="register" next={typeof params.next === "string" ? params.next : undefined} initialRole={params.role === "host" ? "host" : "renter"} />;
}
