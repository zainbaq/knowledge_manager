import type { NextConfig } from "next";

// Security headers - kept identical to the other Promethean apps so every
// service behind Traefik presents the same posture.
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on',
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block',
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin',
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()',
  },
];

const nextConfig: NextConfig = {
  // Hide dev indicator
  devIndicators: false,

  // Standalone output for Docker deployment
  output: 'standalone',

  // Enable compression
  compress: true,

  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [],
  },

  experimental: {
    optimizePackageImports: ['lucide-react'],
  },

  // Empty turbopack config to acknowledge we're using Turbopack in dev
  turbopack: {},

  // This API's paths end in a slash (/api/v1/query/, /api/v1/list-indexes/).
  // Both flags are needed: trailingSlash keeps the slash on the proxied request
  // so the backend route matches, and skipTrailingSlashRedirect stops Next from
  // answering with its own redirect first. Without them the backend receives the
  // slash-less path and replies 307 to http://backend:8000/... - an internal
  // hostname the browser cannot reach, leaked in the Location header.
  trailingSlash: true,
  skipTrailingSlashRedirect: true,

  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },

  // Proxy API requests to the backend so the browser only ever talks to this
  // origin. Calling the backend cross-origin instead would force the backend to
  // keep a permissive CORS allowlist just to serve our own frontend.
  //
  // NOTE: rewrites() is evaluated during `next build` and baked into the routes
  // manifest - BACKEND_URL is therefore a BUILD-time value, not a runtime one.
  // Supplying it only as container env silently leaves the fallback in place and
  // every proxied request fails with ECONNREFUSED. It is passed as a build arg
  // in next/Dockerfile; the internal service DNS name is stable, so baking it in
  // is safe.
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
