import type { NextConfig } from "next";

const apiUrl = (process.env.MARKETPLACE_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
const searchKeys = ["location", "date", "guests", "category"] as const;

const nextConfig: NextConfig = {
  agentRules: false,
  devIndicators: false,
  async redirects() {
    return [
      { source: "/index.html", destination: "/", permanent: true },
      ...searchKeys.map((key) => ({
        source: "/",
        has: [{ type: "query" as const, key }],
        destination: "/marketplace",
        permanent: true,
      })),
    ];
  },
  async rewrites() {
    const beforeFiles = [
      { source: "/", destination: "/_landing/index.html" },
      { source: "/utleie.html", destination: "/_landing/utleie.html" },
      { source: "/ledig-moterom.html", destination: "/_landing/ledig-moterom.html" },
    ];
    if (process.env.MARKETPLACE_API_MODE !== "private-proxy") {
      beforeFiles.push({ source: "/api/:path*", destination: `${apiUrl}/:path*` });
    }
    return { beforeFiles, afterFiles: [], fallback: [] };
  },
};

export default nextConfig;
