import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
        paper: "#faf8f3",
        chalk: "#ffffff",
        graphite: "#2f2f2f",
        tomato: "#f05a3f",
        aqua: "#17bebb",
        lemon: "#ffd84d",
        moss: "#536b48"
      },
      boxShadow: {
        crisp: "8px 8px 0 #171717"
      }
    }
  },
  plugins: []
};

export default config;
