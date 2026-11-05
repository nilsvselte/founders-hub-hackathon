export type Room = {
  id: string;
  name: string;
  city: string;
  venue: string;
  kind: string;
  description: string;
  image_key: string;
  capacity: number;
  equipment: string[];
  hourly_rate_ore: number;
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.method && !["GET", "HEAD"].includes(options.method.toUpperCase())) {
    headers.set("X-Marketplace-Request", "1");
    if (typeof options.body === "string" && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }
  const response = await fetch(`/api/${path}`, { cache: "no-store", ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : null;
    throw new ApiError(message ?? "Something went wrong. Please try again.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

const price = new Intl.NumberFormat("en-GB", {
  style: "currency", currency: "NOK", currencyDisplay: "code",
  minimumFractionDigits: 0, maximumFractionDigits: 2,
});

export function money(ore: number) {
  return price.format(ore / 100);
}

const roomPhotos = new Set(["digs-driv", "brighten-meeting-room", "kowork-meeting-room"]);
const venuePhotos = new Set(["digs-gnist-spark", "kowork-venue", "brighten-venue"]);

export function photo(imageKey: string | null | undefined) {
  const key = imageKey?.replace(/\.webp$/, "");
  if (!key || (!roomPhotos.has(key) && !venuePhotos.has(key))) return null;
  return { src: `/rooms/${key}.webp`, isVenuePhoto: venuePhotos.has(key) };
}
