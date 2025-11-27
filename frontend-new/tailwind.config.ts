import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        "bg-base": "#050712",
        "bg-panel": "rgba(9, 12, 28, 0.75)",
        "accent": "#10f0a0",
        "accent-soft": "#22f0c0",
        "accent-alt": "#8b5cf6",
        "text-dim": "#cbd5f5"
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "SFMono-Regular"],
        sans: ["Inter", "system-ui", "sans-serif"]
      },
      boxShadow: {
        neon: "0 0 20px rgba(16, 240, 160, 0.25)",
        "neon-strong": "0 0 30px rgba(34, 240, 192, 0.35)"
      }
    }
  },
  plugins: []
};

export default config;
