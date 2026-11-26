// ABOUTME: Next.js configuration for the web admin.
// ABOUTME: Holds the one redirect from / to the sign-in page.

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/",
        destination: "/auth/login",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
