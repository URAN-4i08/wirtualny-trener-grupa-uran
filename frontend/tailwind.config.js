/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "surface-container": "#1d2027",
        "on-surface-variant": "#c2c6d6",
        "surface-variant": "#32353c",
        "primary": "#adc6ff",
        "primary-container": "#4d8eff",
        "secondary": "#d0bcff",
        "error": "#ffb4ab",
        "background": "#10131a",
        "on-background": "#e1e2ec",
        "surface": "#10131a",
      },
      fontFamily: {
        "h1": ["Space Grotesk", "sans-serif"],
        "body-lg": ["Inter", "sans-serif"],
        "label-sm": ["Inter", "sans-serif"],
      }
    }
  },
  plugins: [],
}
