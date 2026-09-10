"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Navbar() {
  const pathname = usePathname();

  const isHome = pathname === "/";
  const isRuns = pathname.startsWith("/runs");
  const isTrace = pathname.startsWith("/trace");

  return (
    <header className="border-b border-slate-800/80 bg-[#090d16]/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 border border-indigo-400/30 group-hover:scale-105 transition-transform">
              <svg
                className="w-4 h-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-white">
                Agentic RAG
              </span>
              <span className="text-[10px] font-mono font-normal px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                OBSERVER
              </span>
            </div>
          </Link>

          {/* Nav links */}
          <nav className="flex items-center gap-1 text-xs font-medium">
            <Link
              href="/"
              className={`px-3 py-1.5 rounded-md transition-all font-mono text-[11px] ${
                isHome
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/runs"
              className={`px-3 py-1.5 rounded-md transition-all font-mono text-[11px] ${
                isRuns
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              Runs Directory
            </Link>
            {isTrace && (
              <span className="px-3 py-1.5 rounded-md text-[11px] font-mono bg-slate-800/50 text-slate-300 border border-slate-700/60 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                Live Trace
              </span>
            )}
          </nav>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-slate-400 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50" />
            <span className="hidden sm:inline text-slate-500">FastAPI:</span>
            <span className="text-slate-300 font-medium">localhost:8000</span>
          </div>
        </div>
      </div>
    </header>
  );
}
