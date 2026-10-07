import { defineConfig } from "oxlint";

export default defineConfig({
  plugins: ["unicorn", "typescript", "oxc", "import"],
  categories: {
    correctness: "error",
    suspicious: "error",
    perf: "warn",
  },
  options: {
    typeAware: true,
    reportUnusedDisableDirectives: "error",
  },
  rules: {
    eqeqeq: "error",
    "no-var": "error",
    "prefer-const": "error",
    "prefer-template": "error",
    "require-await": "error",
    "import/no-cycle": "error",
    "import/no-duplicates": "error",
    "typescript/consistent-type-imports": "error",
    "typescript/no-explicit-any": "warn",
    "typescript/no-misused-promises": "error",
  },
});
