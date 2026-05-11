import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { CaveatBanner } from "@/components/CaveatBanner";

export const metadata: Metadata = {
  title: "TRIDENT",
  description: "Disease to target to molecule to response research platform"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <div className="brand">TRIDENT</div>
            <nav className="nav">
              <Link href="/">Dashboard</Link>
              <Link href="/run/demo">Agent Graph</Link>
              <Link href="/run/demo/targets">Targets</Link>
              <Link href="/run/demo/report">Report</Link>
            </nav>
          </aside>
          <main className="main">
            {children}
            <div className="band">
              <CaveatBanner compact />
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
