import type { Config } from "tailwindcss";
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:              "var(--color-bg)",
        surface:         "var(--color-surface)",
        "surface-2":     "var(--color-surface-2)",
        "surface-off":   "var(--color-surface-offset)",
        border:          "var(--color-border)",
        divider:         "var(--color-divider)",
        text:            "var(--color-text)",
        muted:           "var(--color-text-muted)",
        faint:           "var(--color-text-faint)",
        primary:         "var(--color-primary)",
        "primary-hover": "var(--color-primary-hover)",
        success:         "var(--color-success)",
        error:           "var(--color-error)",
        warning:         "var(--color-warning)",
        gold:            "var(--color-gold)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        body:    ["var(--font-body)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm:   "var(--radius-sm)",
        md:   "var(--radius-md)",
        lg:   "var(--radius-lg)",
        xl:   "var(--radius-xl)",
        full: "var(--radius-full)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
    },
  },
  plugins: [],
};
export default config;
