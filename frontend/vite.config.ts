import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies the API paths to the local backend so the browser only
// ever talks to one origin; production deployments map the same paths at their
// edge. VITE_API_BASE_URL overrides the base for deployment-specific setups.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
