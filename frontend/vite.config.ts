import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const devPort = Number(process.env.PORT ?? process.env.VITE_PORT ?? "5173");

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: devPort,
    strictPort: true,
  },
  build: {
    rollupOptions: {
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
