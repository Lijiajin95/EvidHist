import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["tests/setup.ts"],
    include: [
      "src/**/*.test.{ts,tsx}",
      "tests/unit/**/*.test.{ts,tsx}",
      "tests/component/**/*.test.{ts,tsx}",
      "tests/property/**/*.test.{ts,tsx}",
    ],
    testTimeout: 5000,
    hookTimeout: 10000,
    retry: 0,
    passWithNoTests: false,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      // main.tsx is the bootstrap entry; pendingQuote.ts is a type-only module:
      // neither contains behavior to cover.
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/generated/**",
        "src/main.tsx",
        "src/domain/pendingQuote.ts",
      ],
      reporter: ["text", "json", "lcov"],
      thresholds: { lines: 90, branches: 90, functions: 90, statements: 90 },
    },
  },
});
