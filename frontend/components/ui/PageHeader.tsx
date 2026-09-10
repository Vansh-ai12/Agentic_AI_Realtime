import React from "react";

interface PageHeaderProps {
  badgeText: string;
  title: string | React.ReactNode;
  description: string | React.ReactNode;
  actions?: React.ReactNode;
  statusBadge?: React.ReactNode;
  variant?: "indigo" | "emerald" | "rose";
  className?: string;
}

export function PageHeader({
  badgeText,
  title,
  description,
  actions,
  statusBadge,
  variant = "indigo",
  className = "",
}: PageHeaderProps) {
  const gradientStyles = {
    indigo: "border-indigo-500/20 bg-gradient-to-r from-slate-900/90 via-indigo-950/40 to-slate-950/90",
    emerald: "border-emerald-500/30 bg-gradient-to-r from-slate-900/95 via-emerald-950/30 to-slate-950/95",
    rose: "border-rose-500/30 bg-gradient-to-r from-slate-900/95 via-rose-950/30 to-slate-950/95",
  }[variant];

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border p-6 sm:p-8 backdrop-blur-xl shadow-2xl transition-all ${gradientStyles} ${className}`}
    >
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              {badgeText}
            </div>
            {statusBadge}
          </div>

          <div className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            {title}
          </div>

          <div className="text-sm text-slate-400 leading-relaxed">
            {description}
          </div>
        </div>

        {actions && <div className="shrink-0 self-start md:self-center">{actions}</div>}
      </div>
    </div>
  );
}
