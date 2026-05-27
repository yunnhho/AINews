import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        coding: "#3B82F6",   // blue-500
        design: "#8B5CF6",   // violet-500
        general: "#22C55E",  // green-500
      },
    },
  },
  plugins: [],
};

export default config;
