/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./static/**/*.js",
    "./*.html",
    "./**/*.html",
  ],
  corePlugins: {
    preflight: true,
  },
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        sm: '50px',
        md: '50px',
        lg: '50px',
        xl: '50px',
        '2xl': '50px',
      },
    },
    screens: {
      'xs': '375px',
      'sm': '576px',
      'md': '758px',
      'xl': '1100px',
      '2xl': '1440px',
    },
    extend: {},
  },
  plugins: [],
}

