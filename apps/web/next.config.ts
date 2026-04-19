import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const DEV_ORIGINS = process.env.DEV_ORIGINS ? process.env.DEV_ORIGINS.split(",") : [];

const nextConfig: NextConfig = {
  allowedDevOrigins: [...DEV_ORIGINS],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;