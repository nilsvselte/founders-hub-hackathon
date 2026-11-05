import type { NextConfig } from "next";

const apiUrl = (process.env.MARKETPLACE_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  agentRules: false,
  devIndicators: false,
  async redirects() {
    return [{ source: "/welcome", destination: "/welcome/index.html", permanent: false }];
  },
  async rewrites() {
    if (process.env.MARKETPLACE_API_MODE === "private-proxy") return [];
    return { beforeFiles: [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }] };
  },
};

export default nextConfig;
