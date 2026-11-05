import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AccountProvider, MarketHeader } from "./account";
import "./globals.css";

export const metadata: Metadata = {
  title: "Roomline · Find a room",
  description: "Browse and request meeting rooms across venues.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AccountProvider>
          <MarketHeader />
          {children}
        </AccountProvider>
      </body>
    </html>
  );
}
