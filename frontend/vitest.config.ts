import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(viteConfig, defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    exclude: [
      "tests/e2e/**",
      "node_modules/**",
      "dist/**",
      "release/**",
      "test-results/**",
    ],
    restoreMocks: true,
  },
}));