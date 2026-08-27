import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-server proxy so the frontend can call relative /api/... paths
// without CORS setup; point CONSOLE_API_TARGET at wherever
// console/backend is actually running.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": process.env.CONSOLE_API_TARGET || "http://localhost:8001",
    },
  },
});
