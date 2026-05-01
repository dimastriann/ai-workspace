// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",

  // ── Modules ───────────────────────────────────────────────────────────
  modules: ["@nuxtjs/tailwindcss", "@pinia/nuxt"],

  devtools: { enabled: false },

  // ── Runtime Config ────────────────────────────────────────────────────
  runtimeConfig: {
    // Server-only (not exposed to client)
    apiBaseUrl: process.env.NUXT_API_BASE_URL || "http://localhost:8000",

    // Public (exposed to client)
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000",
    },
  },

  // ── TailwindCSS ───────────────────────────────────────────────────────
  tailwindcss: {
    cssPath: "~/assets/css/main.css",
  },

  // ── Experimental Stability Flags ─────────────────────────────────────
  experimental: {
    appManifest: false,
    payloadExtraction: false,
  },

  nitro: {
    esbuild: {
      options: {
        target: 'esnext'
      }
    }
  },

  vite: {
    server: {
      hmr: {
        protocol: "ws",
        host: "localhost",
      },
      watch: {
        usePolling: true,
      },
    },
  },

  // ── App Metadata ──────────────────────────────────────────────────────
  app: {
    head: {
      title: "AI Workspace",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        {
          name: "description",
          content: "Fullstack AI system with RAG & Agents",
        },
      ],
      link: [
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
        },
      ],
    },
  },
});
