import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Pin the project root to web/. Otherwise Next may infer a parent folder and watch the
  // engine's files too (Python caches, the database), reloading the page whenever they change.
  turbopack: { root: here },
  outputFileTracingRoot: here,
  // The Docker image runs the self-contained server (node web/server.js).
  ...(process.env.PLACEIQ_STANDALONE ? { output: "standalone" } : {}),
};

export default nextConfig;
