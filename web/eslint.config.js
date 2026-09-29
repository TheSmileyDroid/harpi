import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

export default [
  {
    ignores: [
      "node_modules/",
      ".svelte-kit/",
      "test-results/",
      "playwright-report/",
      "coverage/",
      "build/",
    ],
  },
  {
    files: ["**/*.js"],
    ...js.configs.recommended,
  },
  ...svelte.configs.recommended,
  {
    files: ["src/**/*.{js,svelte}"],
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },
  {
    files: ["e2e/**/*.js", "*.config.js"],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
];
