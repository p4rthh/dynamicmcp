/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        nvidia: {
          green: "#76B900",
          hover: "#87D300",
          dark: "#0F1905",
          subtle: "#1B2F08",
        },
        nebius: {
          purple: "#7928CA",
          blue: "#0070F3",
          dark: "#0E0E18",
        },
        cyber: {
          950: "#07090E",
          900: "#0D1117",
          850: "#131822",
          800: "#1A202C",
          700: "#2D3748",
          600: "#4A5568",
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
