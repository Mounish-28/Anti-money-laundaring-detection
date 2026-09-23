/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          950: '#020617',
          900: '#0b1329',
          850: '#0f172a',
          800: '#1e293b',
          700: '#334155'
        }
      }
    },
  },
  plugins: [],
}
