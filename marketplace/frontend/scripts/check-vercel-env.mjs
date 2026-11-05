const originKey = process.env.MARKETPLACE_API_MODE === "private-proxy"
  ? "MARKETPLACE_PRIVATE_API_URL"
  : "MARKETPLACE_API_URL";
const error = `Set ${originKey} to the hosted API's HTTPS origin before deploying.`;
const frontendHosts = [process.env.VERCEL_URL, process.env.VERCEL_PROJECT_PRODUCTION_URL];
const value = process.env[originKey] ?? "";

try {
  const api = new URL(value);
  const hostname = api.hostname.replace(/\.$/, "");
  if (
    value !== value.trim() ||
    api.protocol !== "https:" ||
    api.username ||
    api.password ||
    api.pathname !== "/" ||
    api.search ||
    api.hash ||
    hostname === "localhost" ||
    hostname.endsWith(".localhost") ||
    hostname === "0.0.0.0" ||
    hostname.startsWith("127.") ||
    hostname === "[::1]" ||
    frontendHosts.includes(hostname)
  ) {
    throw new Error(error);
  }
} catch {
  console.error(error);
  process.exitCode = 1;
}
