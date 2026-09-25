import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Django routes retain their trailing slash, including multipart POST requests.
  skipTrailingSlashRedirect: true,
  experimental: { proxyTimeout: 900_000, proxyClientMaxBodySize: "48mb" },
  async rewrites() {
    const backend = (process.env.BID_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*/` }];
  },
};

export default nextConfig;
