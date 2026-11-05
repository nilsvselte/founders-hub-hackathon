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
