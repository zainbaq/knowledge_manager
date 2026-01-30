import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["https://knowledge-manager.promethean-labs.co"],
  turbopack: {
    // Explicitly set root to this directory to avoid lockfile detection issues
    root: process.cwd(),
  },
};

export default nextConfig;
