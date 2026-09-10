import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "standard" | "highlight" | "emerald" | "rose";
}

export function Card({ children, className = "", variant = "standard" }: CardProps) {
  const variantStyles = {
    standard: "border-slate-800/80 bg-slate-900/60",
    highlight: "border-indigo-500/30 bg-indigo-950/15",
    emerald: "border-emerald-500/30 bg-emerald-950/15",
    rose: "border-rose-500/30 bg-rose-950/15",
  }[variant];

  return (
    <div
      className={`border rounded-xl overflow-hidden shadow-sm backdrop-blur-sm transition-all duration-150 ${variantStyles} ${className}`}
    >
      {children}
    </div>
  );
}

interface SectionHeaderProps {
  title: string | React.ReactNode;
  subtitle?: string | React.ReactNode;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  bordered?: boolean;
}

export function SectionHeader({
  title,
  subtitle,
  icon,
  actions,
  className = "",
  bordered = true,
}: SectionHeaderProps) {
  return (
    <div
      className={`px-5 py-3.5 flex items-center justify-between gap-3 ${
        bordered ? "border-b border-slate-800" : ""
      } ${className}`}
    >
      <div className="space-y-0.5">
        <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
          {icon && <span className="text-indigo-400 text-xs">{icon}</span>}
          {title}
        </h2>
        {subtitle && <p className="text-[11px] text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}
