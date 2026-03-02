/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        grace: {
          dark: '#0B0F1A',
          card: '#111827',
          accent: '#22D3A7',
          'accent-hover': '#1AB892',
          input: '#1E293B',
          border: '#334155',
          text: '#F1F5F9',
          muted: '#94A3B8',
          error: '#F87171',
        },
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
