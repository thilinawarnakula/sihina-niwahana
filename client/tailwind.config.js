/** Tailwind theme carrying the realestate.com.au design tokens
 *  (see docs/roadmap.md migration section). */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#E4002B", dark: "#B80022", tint: "#FCE9ED" },
        ink: "#2E3A44",
        body: "#3B454E",
        mut: "#6A737B",
        line: "#E1E4E6",
        page: "#F7F7F8",
        link: "#0073E0",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "Helvetica Neue", "Arial", "sans-serif"],
      },
      borderRadius: { card: "12px" },
      boxShadow: {
        card: "0 1px 3px rgba(46,58,68,.08),0 4px 16px -8px rgba(46,58,68,.12)",
        lift: "0 2px 6px rgba(46,58,68,.1),0 16px 40px -12px rgba(46,58,68,.18)",
      },
    },
  },
  plugins: [],
};
