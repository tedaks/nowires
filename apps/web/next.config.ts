import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

function normalizeOrigins(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((origin) => {
      if (/^https?:\/\//.test(origin)) {
        try {
          return new URL(origin).hostname;
        } catch {
          return origin;
        }
      }
      return origin;
    });
}

const nextConfig: NextConfig = {
  allowedDevOrigins: normalizeOrigins(process.env.DEV_ORIGINS),
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