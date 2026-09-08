import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SECE AI",
  description:
    "SECE AI — the agentic assistant for Sri Eshwar College of Engineering (SECE)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased text-slate-900">{children}</body>
    </html>
  );
}
