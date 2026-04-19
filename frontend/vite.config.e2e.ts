import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const devPort = Number(process.env.PORT ?? process.env.VITE_PORT ?? "4173");
const localApiTarget = process.env.SENTINEL_LOCAL_API_URL ?? "http://127.0.0.1:7071";

export default defineConfig({
  plugins: [react()],
  server: {
    port: devPort,
    strictPort: true,
    proxy: {
      "/api": {
        target: localApiTarget,
        changeOrigin: true,
      },
    },
  },
});