/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        crextio: {
          bg: "#E8E7E0", // The soft grayish cream base
          gradientStart: "#F3EDE1", // The warm cream top right
          gradientEnd: "#E3E5DF", // The cool slate bottom left
          card: "#FFFFFF",
          cardDark: "#2B2B2B", // The dark soft black
          cardDarkHover: "#3A3A3A",
          mustard: "#F4D160", // The accent yellow
          textMain: "#1A1A1A",
          textMuted: "#737373",
          border: "#EFEFEF"
        },
      },
      fontFamily: {
        urdu:  ["Noto Nastaliq Urdu", "serif"],
        latin: ["Inter", "sans-serif"],
      },
      borderRadius: {
        '4xl': '32px',
        '5xl': '40px',
      },
      boxShadow: {
        crextio: "0 10px 40px -10px rgba(0,0,0,0.06)",
        crextioDark: "0 20px 40px -10px rgba(0,0,0,0.2)",
      }
    },
  },
  plugins: [],
}
