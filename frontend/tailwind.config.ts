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
        paper: "#f4f1ea",
        "paper-2": "#efebe0",
        ink: "#1c1a17",
        "ink-soft": "#5b554b",
        "ink-faint": "#8c857a",
        rule: "#ddd5c5",
        accent: "#b23a2e",
        "accent-ink": "#8f2c22",
        // category accents (muted editorial tones)
        coding: "#355e5b",   // pine
        design: "#8a5a2b",   // ochre
        general: "#54514a",  // graphite
      },
      fontFamily: {
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
    },
  },
  plugins: [],
};

export default config;
