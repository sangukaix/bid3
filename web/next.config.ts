import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.BID3_DIST_DIR ?? ".next",
  // Public-demo builds remain gated even if a later start omits the runtime flag.
  env: { BID3_PUBLIC_DEMO_BUILD: process.env.BID3_PUBLIC_DEMO === "1" ? "1" : "0" },
  // Django routes retain their trailing slash, including multipart POST requests.
  skipTrailingSlashRedirect: true,
  experimental: { proxyTimeout: 900_000, proxyClientMaxBodySize: "48mb" },
  async rewrites() {
    const backend = (process.env.BID_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*/` }];
  },
};

export default nextConfig;
