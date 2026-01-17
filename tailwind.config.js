/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./core/templates/**/*.html",
    "./experiments/*/templates/**/*.html",
    "./core/static/js/**/*.js",
    "./experiments/*/static/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'serif': ['Charter', 'Bitstream Charter', 'Sitka Text', 'Cambria', 'serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
      colors: {
        'lab': {
          'bg': '#fafafa',
          'surface': '#ffffff',
          'card': '#ffffff',
          'border': '#e5e5e5',
          'border-light': '#d4d4d4',
          'text': '#171717',
          'text-muted': '#525252',
          'text-subtle': '#a3a3a3',
          'accent': '#171717',
        }
      }
    },
  },
  plugins: [],
}
