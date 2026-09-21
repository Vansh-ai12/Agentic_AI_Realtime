import React from "react";

interface GradientBannerProps {
  children: React.ReactNode;
  variant?: "indigo" | "emerald" | "rose" | "amber";
  className?: string;
}

export function GradientBanner({ children, variant = "indigo", className = "" }: GradientBannerProps) {
  const gradients = {
    indigo: "from-indigo-600/20 via-purple-600/10 to-slate-900/60 border-indigo-500/30",
    emerald: "from-emerald-600/20 via-teal-600/10 to-slate-900/60 border-emerald-500/30",
    rose: "from-rose-600/20 via-pink-600/10 to-slate-900/60 border-rose-500/30",
    amber: "from-amber-600/20 via-orange-600/10 to-slate-900/60 border-amber-500/30",
  }[variant];

  return (
    <div className={`relative overflow-hidden rounded-xl border bg-gradient-to-r ${gradients} ${className}`}>
      {/* Animated gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-pulse" />
      <div className="relative p-5">
        {children}
      </div>
    </div>
  );
}
