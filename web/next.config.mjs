/**
 * API проксируется через Next, чтобы фронт и бэк были одним источником:
 * куки становятся first-party, CORS не нужен, и через туннель (cloudflared)
 * всё работает по одному адресу.
 *
 * BACKEND_ORIGIN — адрес бэкенда изнутри сети docker, в браузер не попадает.
 */
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://backend:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // dev-сервер открывается через туннель (cloudflared) — иначе Next ругается на чужой origin
  allowedDevOrigins: ["*.trycloudflare.com", "*.ngrok-free.app"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
      { source: "/health", destination: `${BACKEND_ORIGIN}/health` },
    ];
  },
};

export default nextConfig;
