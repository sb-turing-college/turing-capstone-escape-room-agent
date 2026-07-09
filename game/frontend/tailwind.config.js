/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        pixel: ['"Press Start 2P"', "monospace"],
        retro: ['"VT323"', "monospace"],
      },
      colors: {
        mm: {
          bg: "#1a1025",
          panel: "#2d1f3d",
          border: "#6b4c9a",
          accent: "#f4c542",
          text: "#e8dcc8",
          highlight: "#7ec8e3",
        },
      },
    },
  },
  plugins: [],
};
