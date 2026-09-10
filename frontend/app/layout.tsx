import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agentic RAG — Telemetry & Trace Observability",
  description: "Production LangGraph Trace Visualizer, DAG Inspector & Token Cost Telemetry",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-[#090d16] text-slate-100 selection:bg-indigo-500/30 selection:text-indigo-200">
        {/* Ambient background glow */}
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[350px] bg-gradient-to-b from-indigo-500/10 via-purple-500/5 to-transparent blur-3xl opacity-70" />
        </div>

        {/* Global Shared Header */}
        <Navbar />

        {/* Content Container */}
        <div className="flex-1 relative z-10">{children}</div>

        {/* Global Shared Footer */}
        <footer className="border-t border-slate-800/60 bg-[#070a12] py-5 text-center text-xs text-slate-500 relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2 font-mono text-[11px]">
            <span className="text-slate-500">
              LangGraph Multi-Agent RAG Pipeline · D20 DAG Trace &amp; D21 Token Compression
            </span>
            <span className="text-slate-600">
              Supabase Telemetry Engine
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
