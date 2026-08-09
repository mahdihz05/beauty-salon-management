import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const apiProxy = process.env.VITE_DEV_API_PROXY ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": apiProxy,
      "/media": apiProxy,
    },
  },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
});
