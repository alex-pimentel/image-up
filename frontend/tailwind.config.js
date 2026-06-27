/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  // Avoid PrimeVue/Tailwind button/input collisions via preflight reset.
  corePlugins: { preflight: true },
  theme: {
    extend: {
      // `brand` is aliased to Tailwind's default `blue` to match the
      // AgenteResolve reference site styling.
      colors: {
        brand: {
          50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd',
          400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8',
          800: '#1e40af', 900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
}