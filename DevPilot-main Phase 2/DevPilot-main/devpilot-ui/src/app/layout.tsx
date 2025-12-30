import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DevPilot - AI-Powered SDLC Platform",
  description: "Intelligent Software Development Lifecycle Management with Multi-Agent System",
  keywords: ["AI", "SDLC", "DevOps", "Automation", "Software Development", "Multi-Agent"],
  authors: [{ name: "DevPilot Team" }],
  openGraph: {
    title: "DevPilot - AI-Powered SDLC Platform",
    description: "Intelligent Software Development Lifecycle Management with Multi-Agent System",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
