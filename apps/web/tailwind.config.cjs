/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "sans-serif",
        ],
      },
      colors: {
        app: {
          // Main background for the app
          bg: "#020617", // near-black, blue-tinted

          // Cards / surfaces
          surface: "#020617",
          surfaceAlt: "#020617",

          // Borders
          border: "#1f2937",

          // Text
          text: "#e5e7eb",
          muted: "#9ca3af",

          // Accent (links, highlights, primary buttons)
          accent: "#38bdf8",
          accentSoft: "#0ea5e9",
        },
      },
      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },
      boxShadow: {
        soft: "0 10px 25px rgba(15, 23, 42, 0.45)",
      },
      maxWidth: {
        "content": "960px",
      },
    },
  },
  plugins: [],
};
