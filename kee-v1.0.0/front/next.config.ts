import type { NextConfig } from "next";

const BACKEND = process.env.KEE_BACKEND_URL || "http://127.0.0.1:8306";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
