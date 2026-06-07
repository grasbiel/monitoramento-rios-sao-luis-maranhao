/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#13242f",
        ink2: "#52646f",
        ink3: "#8c9aa3",
        hair: "#e3e9ee",
        hair2: "#eef2f5",
        paper: "#ffffff",
        paper2: "#f6f9fb",
        navy: "#16344a",
        blue: "#1f6f9e",
        blueMid: "#3f93c4",
        blueLt: "#e9f2f8",
        blueLt2: "#d6e7f1",
        green: "#2f9e6f",
        greenLt: "#e4f4ec",
        red: "#cd4a3a",
        redLt: "#f8e6e2",
        amber: "#d9963f",
        amberLt: "#f8eedb",
        gray: "#aab4bc",
        grayLt: "#eef1f3",
      },
      fontFamily: {
        sans: ['"Helvetica Neue"', "Helvetica", "Arial", "sans-serif"],
        mono: ['"SFMono-Regular"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(19,36,47,0.04)",
      },
    },
  },
  plugins: [],
};
