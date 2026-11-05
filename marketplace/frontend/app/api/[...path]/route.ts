export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const sessionCookie = "marketplace_session=";
const allowedCookies = [sessionCookie, "ntnu_demo_session="];
const noCache = { "Cache-Control": "no-store" };

function error(status: number, detail: string) {
  return Response.json({ detail }, { status, headers: noCache });
}

function privateOrigin() {
  try {
    const origin = new URL(process.env.MARKETPLACE_PRIVATE_API_URL ?? "");
    if (
      origin.protocol === "https:" && !origin.username && !origin.password &&
      origin.pathname === "/" && !origin.search && !origin.hash
    ) return origin;
  } catch {
    // Keep configuration values out of error responses.
  }
  return null;
}

async function proxy(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  if (process.env.MARKETPLACE_API_MODE !== "private-proxy") return error(404, "Not found");

  const target = privateOrigin();
  if (!target) return error(503, "Marketplace API unavailable");

  const { path } = await params;
  target.pathname = `/${path.map(encodeURIComponent).join("/")}`;
  target.search = new URL(request.url).search;

  const headers = new Headers({ Accept: "application/json" });
  for (const name of ["Content-Type", "X-Marketplace-Request"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const cookies = request.headers.get("Cookie")?.split(";")
    .map((part) => part.trim()).filter((part) => allowedCookies.some((prefix) => part.startsWith(prefix)));
  if (cookies?.length) headers.set("Cookie", cookies.join("; "));

  if (target.pathname === "/internal/device/events") {
    const authorization = request.headers.get("Authorization");
    if (authorization) headers.set("Authorization", authorization);
  }
  if (target.hostname.endsWith(".proxy.daytona.work") || target.hostname.endsWith(".daytonaproxy01.eu")) {
    headers.set("X-Daytona-Skip-Preview-Warning", "true");
  }

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.body ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(20_000)]),
    });

    const contentType = upstream.headers.get("Content-Type")?.split(";", 1)[0].trim().toLowerCase();
    const emptyBody = request.method === "HEAD" || upstream.status === 204 || upstream.status === 205;
    const isJson = contentType === "application/json" || contentType?.endsWith("+json");
    if ((upstream.status >= 300 && upstream.status < 400) || (!emptyBody && !isJson)) {
      await upstream.body?.cancel();
      return error(502, "Marketplace API unavailable");
    }

    const responseHeaders = new Headers(noCache);
    if (isJson) responseHeaders.set("Content-Type", "application/json");
    for (const cookie of upstream.headers.getSetCookie()) {
      if (allowedCookies.some((prefix) => cookie.startsWith(prefix)) && !/;\s*domain\s*=/i.test(cookie)) {
        responseHeaders.append("Set-Cookie", cookie);
      }
    }
    return new Response(emptyBody ? null : upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return error(502, "Marketplace API unavailable");
  }
}

export { proxy as GET, proxy as HEAD, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE, proxy as OPTIONS };
