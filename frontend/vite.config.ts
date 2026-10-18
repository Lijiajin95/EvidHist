import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies the API paths to the local backend so the browser only
// ever talks to one origin; production deployments map the same paths at their
// edge. VITE_API_BASE_URL overrides the base for deployment-specific setups.
export default defineConfig({
  plugins: [react()],
  server: {
    // Playwright probes the dev server at 127.0.0.1; Node resolves "localhost"
    // to ::1 first on IPv6-preferring hosts, which would leave that probe (and
    // therefore the E2E job) waiting on a closed port.
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      // E2E overrides this to its dedicated backend port so a running demo
      // service on 8000 can never receive browser-test traffic.
      "/v1": process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000",
      "/health": process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000",
    },
  },
});
