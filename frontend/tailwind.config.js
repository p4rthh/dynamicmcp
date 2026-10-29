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
        base: {
          950: "#050507",
          900: "#09090b",
          850: "#101014",
          800: "#18181b",
          700: "#27272a",
          600: "#3f3f46",
          500: "#52525b",
          400: "#71717a",
          300: "#a1a1aa",
          200: "#e4e4e7",
          100: "#f4f4f5",
        },
        brand: {
          DEFAULT: "#ffffff",
          invert: "#000000",
          accent: "#f59e0b", // Warm amber accent for run latency/highlights
          muted: "#3f3f46",
        }
      },
      fontFamily: {
        sans: ['"Geist"', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}
