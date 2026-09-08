/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b3ccff",
          300: "#84acff",
          400: "#5586ff",
          500: "#2d63f6",
          600: "#1c47d1",
          700: "#1836a3",
          800: "#152c7f",
          900: "#132763",
        },
      },
    },
  },
  plugins: [],
};
