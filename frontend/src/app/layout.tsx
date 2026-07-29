import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "ToRsy",
  description: "The Buddy in the Dark",
};

// Swallows errors injected by browser wallet extensions (MetaMask et al.) so the
// Next.js dev overlay does not surface them. These originate in the extension's
// own inpage.js — never in ToRsy code — so suppressing them is purely cosmetic.
const suppressExtensionErrors = `
(function () {
  function fromExtension(text) {
    text = String(text || "");
    return text.indexOf("chrome-extension://") !== -1 ||
           text.indexOf("moz-extension://") !== -1 ||
           text.indexOf("MetaMask") !== -1;
  }
  window.addEventListener("error", function (e) {
    var stack = (e && e.error && e.error.stack) || "";
    if (fromExtension(e && e.filename) || fromExtension(stack) || fromExtension(e && e.message)) {
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  }, true);
  window.addEventListener("unhandledrejection", function (e) {
    var r = e && e.reason;
    var stack = (r && (r.stack || r.message)) || r || "";
    if (fromExtension(stack)) {
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  }, true);
})();
`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <script dangerouslySetInnerHTML={{ __html: suppressExtensionErrors }} />
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
