import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

const devPort = Number(process.env.PORT ?? process.env.VITE_PORT ?? "5173");

// https://vite.dev/config/
export default defineConfig({
  base: process.env.VITE_ELECTRON === "true" ? "./" : "/",
  plugins: [react()],
  server: {
    port: devPort,
    strictPort: true,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        authPopup: resolve(__dirname, "auth-popup.html"),
      },
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/@azure/msal")) return "vendor-msal";
          if (id.includes("node_modules/recharts")) return "vendor-charts";
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom/") ||
            id.includes("node_modules/react-router-dom/")
          )
            return "vendor-react";
          if (
            id.includes("node_modules/lucide-react") ||
            id.includes("node_modules/clsx") ||
            id.includes("node_modules/tailwind-merge")
          )
            return "vendor-ui";
        },
      },
    },
  },
});
