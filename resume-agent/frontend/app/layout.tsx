import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "ResumeAI — Tailor. Match. Land.",
  description: "AI-powered resume tailoring for every job application.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <Navbar />
          <main className="max-w-[1200px] mx-auto px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
