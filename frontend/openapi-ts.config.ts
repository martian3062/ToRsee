import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../docs/openapi.yaml",
  output: {
    clean: true,
    path: "src/lib/openapi",
  },
  plugins: [
    "@hey-api/typescript",
    {
      name: "@tanstack/react-query",
      queryOptions: true,
      mutationOptions: true,
    },
  ],
});
