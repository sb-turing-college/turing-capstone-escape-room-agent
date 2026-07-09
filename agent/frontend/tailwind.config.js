/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#1a1228",
        accent: "#7c5cff",
        thought: "#fbbf24",
        action: "#60a5fa",
        observation: "#34d399",
        memory: "#c084fc",
      },
    },
  },
  plugins: [],
};
