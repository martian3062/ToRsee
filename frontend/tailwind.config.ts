import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18212f",
        field: "#f7f9fb",
        signal: "#0f9b8e",
        amberline: "#d98634",
      },
      boxShadow: {
        panel: "0 16px 40px rgba(23, 31, 45, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
