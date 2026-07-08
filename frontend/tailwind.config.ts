import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7",
        ink: "#1F2933",
        blueprint: {
          50: "#EAF1F8",
          100: "#CFE0EE",
          400: "#4A7BAB",
          600: "#1D4E89",
          700: "#163C69",
          900: "#0E2540",
        },
        hazard: "#E8A33D",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Inter", "sans-serif"],
      },
      backgroundImage: {
        "iso-grid":
          "linear-gradient(30deg, rgba(29,78,137,0.08) 12%, transparent 12.5%, transparent 87%, rgba(29,78,137,0.08) 87.5%, rgba(29,78,137,0.08)), linear-gradient(150deg, rgba(29,78,137,0.08) 12%, transparent 12.5%, transparent 87%, rgba(29,78,137,0.08) 87.5%, rgba(29,78,137,0.08)), linear-gradient(30deg, rgba(29,78,137,0.08) 12%, transparent 12.5%, transparent 87%, rgba(29,78,137,0.08) 87.5%, rgba(29,78,137,0.08)), linear-gradient(150deg, rgba(29,78,137,0.08) 12%, transparent 12.5%, transparent 87%, rgba(29,78,137,0.08) 87.5%, rgba(29,78,137,0.08))",
      },
      backgroundSize: {
        "iso-grid": "40px 70px",
      },
    },
  },
  plugins: [],
};

export default config;
