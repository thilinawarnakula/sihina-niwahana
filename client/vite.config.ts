import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { version } from "./package.json";

// __APP_VERSION__ is baked in at build time and shown on the login screen
// and homepage, so you can always tell which build is deployed.
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(
      `${version} · ${new Date().toISOString().slice(0, 10)}`),
  },
  server: { proxy: { "/api": "http://localhost:3001" } },
});
