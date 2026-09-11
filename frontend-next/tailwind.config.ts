import type { Config } from "tailwindcss";

/**
 * Two environments in one screen:
 *  - `shell`  the dark instrument chrome (rail, top bar, composer)
 *  - `sheet`  the bright reading surface where results live
 * The contrast is the whole point: navigation recedes, data comes forward.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: {
          DEFAULT: "#0F1D28",
          raised: "#162936",
          hover: "#1D3647",
          line: "#24404F",
          text: "#C3D3DC",
          dim: "#7C95A4",
        },
        sheet: {
          DEFAULT: "#F4F6F7",
          card: "#FFFFFF",
          line: "#DDE3E7",
          ink: "#0E1A22",
          muted: "#5E7280",
        },
        signal: {
          DEFAULT: "#0E8C88",
          deep: "#0A6C69",
          wash: "#E2F1F0",
          edge: "#9AD3D0",
        },
        flag: "#A8620A",
        plum: "#7A2E6B",
      },
      fontFamily: {
        sans: ["var(--font-archivo)", "system-ui", "sans-serif"],
        read: ["var(--font-newsreader)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        micro: ["11.5px", { lineHeight: "1.4" }],
        meta: ["12.5px", { lineHeight: "1.45" }],
      },
      borderRadius: { card: "6px", chip: "4px" },
      boxShadow: {
        card: "0 1px 2px rgba(14,26,34,.05), 0 6px 20px -12px rgba(14,26,34,.18)",
        lift: "0 2px 4px rgba(14,26,34,.06), 0 16px 40px -20px rgba(14,26,34,.30)",
      },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        sweep: { "0%": { left: "-40%" }, "100%": { left: "100%" } },
        grow: { from: { transform: "scaleX(0)" }, to: { transform: "scaleX(1)" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: ".35" } },
      },
      animation: {
        rise: "rise .34s cubic-bezier(.2,.7,.3,1) both",
        sweep: "sweep 1.1s ease-in-out infinite",
        grow: "grow .5s cubic-bezier(.2,.7,.3,1) both",
        pulse2: "pulse2 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
