import { AccountForm } from "../account";

export default async function SignInPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  const { next } = await searchParams;
  return <AccountForm mode="login" next={typeof next === "string" ? next : undefined} />;
}
