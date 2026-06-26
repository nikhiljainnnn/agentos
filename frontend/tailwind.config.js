/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"],
      },
      colors: {
        // ── Redesign surface / text scale (referenced in CSS vars + Tailwind classes) ──
        base:        "#070B14",
        "surf-a":    "#0D1526",
        "surf-b":    "#111D35",
        "surf-c":    "#162240",
        accent:      "#6C63FF",
        "accent-hi": "#8B7FFF",
        violet:      "#8B5CF6",
        emerald:     "#10B981",
        amber:       "#F59E0B",
        rose:        "#F43F5E",
        t1:          "#F0F4FF",
        t2:          "#94A3C4",
        t3:          "#4E6080",
        t4:          "#2A3A55",
        // ── Provider colours ──
        azure:       "#60A5FA",
        anthropic:   "#FB923C",
        google:      "#34D399",
        // ── Legacy brand palette (kept for backward compat) ──
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
        // ── Per-agent colours ──
        agent: {
          supervisor:  "#fbbf24",
          rag:         "#60a5fa",
          search:      "#34d399",
          code:        "#a78bfa",
          synthesizer: "#fb923c",
          critic:      "#f87171",
        },
      },
      borderColor: {
        DEFAULT: "rgba(255,255,255,0.07)",
      },
      boxShadow: {
        "glow-accent": "0 0 24px rgba(108,99,255,0.25)",
        "glow-sm":     "0 0 12px rgba(108,99,255,0.15)",
        card:          "0 4px 24px rgba(0,0,0,0.4)",
        "card-lg":     "0 8px 40px rgba(0,0,0,0.5)",
      },
      animation: {
        "fade-up":      "fadeUp 0.25s ease both",
        "fade-in":      "fadeIn 0.2s ease both",
        "cursor-blink": "cursor-blink 0.9s ease infinite",
        shimmer:        "shimmer 1.6s infinite",
        "pulse-slow":   "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-up":     "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "cursor-blink": {
          "0%,100%": { opacity: "1" },
          "50%":     { opacity: "0" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
