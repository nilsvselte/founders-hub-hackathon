import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AccountProvider, MarketHeader } from "./account";
import { ServiceWorkerRegister } from "./sw-register";
import "./globals.css";

export const metadata: Metadata = {
  title: "standbyroom · Meeting rooms",
  description: "Browse and request meeting rooms across venues.",
  applicationName: "standbyroom",
  appleWebApp: { capable: true, title: "standbyroom", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#0A0E18",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500&family=Inter:wght@400;500;600&display=swap" />
      </head>
      <body>
        <AccountProvider>
          <MarketHeader />
          {children}
        </AccountProvider>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
