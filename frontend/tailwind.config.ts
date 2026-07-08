import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // "Drafting table" palette: aged vellum paper + graphite ink +
        // a single blueprint-blue accent for actions and focus states.
        vellum: {
          50: "#FAF8F3",
          100: "#F2EEE3",
          200: "#E6DFCC",
        },
        graphite: {
          700: "#3A3D3E",
          800: "#26282A",
          900: "#17181A",
        },
        blueprint: {
          400: "#5B8FB9",
          500: "#3D6E96",
          600: "#2C5878",
        },
        signal: {
          amber: "#C77A32",
        },
        // Dark mode is a literal blueprint: the deep cyanotype blue paper
        // process blueprints are named after, with white/cyan linework -
        // an inversion of light mode's vellum-and-ink, not just a
        // brightness flip.
        print: {
          900: "#0B2942",
          800: "#123A5C",
          700: "#1C4D74",
        },
        linework: {
          DEFAULT: "#EAF3FA",
          dim: "#9FC1DC",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
        body: ["var(--font-body)", "sans-serif"],
      },
      backgroundImage: {
        "grid-lines":
          "linear-gradient(rgba(58,61,62,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(58,61,62,0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "24px 24px",
      },
    },
  },
  plugins: [],
};

export default config;
