import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RecoverAI — AI Revenue Recovery Platform",
  description: "Phase 0 Foundation for RecoverAI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased bg-slate-50 text-slate-900">
        {children}
      </body>
    </html>
  );
}
