import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // @ts-expect-error vitest config
  test: {
    include: ["src/**/*.{test,spec}.{js,ts,jsx,tsx}"],
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
  },
});
