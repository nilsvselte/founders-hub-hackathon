import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "standbyroom",
    short_name: "standbyroom",
    description: "Browse and request meeting rooms across venues.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    theme_color: "#0A0E18",
    background_color: "#0A0E18",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
