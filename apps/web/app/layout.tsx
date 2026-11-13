import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Workspace",
  description: "Fullstack AI system with RAG & Agents",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script
          // biome-ignore lint/security/noDangerouslySetInnerHtml: static theme bootstrap
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                try {
                  var pref = localStorage.getItem("theme") || "system";
                  var light = window.matchMedia("(prefers-color-scheme: light)").matches;
                  var theme = pref === "system" ? (light ? "light" : "dark") : pref;
                  document.documentElement.dataset.theme = theme;
                  document.documentElement.style.colorScheme = theme;
                } catch (error) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
