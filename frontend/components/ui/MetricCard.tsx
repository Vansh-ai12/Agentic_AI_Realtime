import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  variant?: "neutral" | "emerald" | "rose" | "indigo" | "amber";
  icon?: React.ReactNode;
  tooltip?: string;
  className?: string;
}

export function MetricCard({
  label,
  value,
  sublabel,
  variant = "neutral",
  icon,
  tooltip,
  className = "",
}: MetricCardProps) {
  const variantStyles = {
    neutral: {
      card: "border-slate-800/80 bg-slate-900/60",
      label: "text-slate-400",
      value: "text-white",
      iconBg: "bg-slate-800/50 text-slate-400 border-slate-700/50",
    },
    emerald: {
      card: "border-emerald-500/30 bg-emerald-950/15",
      label: "text-emerald-400",
      value: "text-emerald-300",
      iconBg: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    },
    rose: {
      card: "border-rose-500/30 bg-rose-950/15",
      label: "text-rose-400",
      value: "text-rose-300",
      iconBg: "bg-rose-500/15 text-rose-400 border-rose-500/30",
    },
    indigo: {
      card: "border-indigo-500/30 bg-indigo-950/15",
      label: "text-indigo-400",
      value: "text-indigo-300",
      iconBg: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
    },
    amber: {
      card: "border-amber-500/30 bg-amber-950/15",
      label: "text-amber-400",
      value: "text-amber-300",
      iconBg: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    },
  }[variant];

  return (
    <div
      className={`relative overflow-hidden border rounded-xl p-4 shadow-sm backdrop-blur-sm transition-all duration-150 ${variantStyles.card} ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className={`text-[11px] font-mono uppercase tracking-wider ${variantStyles.label}`}>
            {label}
          </span>
          {tooltip && (
            <span
              className="text-[10px] italic text-slate-400 underline decoration-dotted cursor-help"
              title={tooltip}
            >
              (est.)
            </span>
          )}
        </div>
        {icon && (
          <div
            className={`w-7 h-7 rounded-lg border flex items-center justify-center text-xs font-mono shrink-0 ${variantStyles.iconBg}`}
          >
            {icon}
          </div>
        )}
      </div>

      <div className={`text-2xl sm:text-3xl font-bold font-mono mt-1.5 tracking-tight ${variantStyles.value}`}>
        {value}
      </div>

      {sublabel && (
        <div className="text-[11px] text-slate-500 mt-1 font-mono">
          {sublabel}
        </div>
      )}
    </div>
  );
}
