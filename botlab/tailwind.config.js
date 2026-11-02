/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./landing.jsx"],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ['"Barlow Condensed"', '"Arial Narrow"', "Impact", "sans-serif"],
      },
      colors: {
        sys: {
          dark: "var(--a1-bg)",
          grid: "var(--a1-surface)",
          raised: "var(--a1-surface-raised)",
          line: "var(--a1-border)",
          accent: "var(--a1-accent)",
          accentfill: "var(--a1-accent-fill)",
          muted: "var(--a1-text-muted)",
          text: "var(--a1-text)",
          onaccent: "var(--a1-on-accent)",
        },
      },
    },
  },
};
