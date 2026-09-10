interface StatusBadgeProps {
  status: string;
  className?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, className = "", size = "sm" }: StatusBadgeProps) {
  const normalized = (status || "unknown").toLowerCase();

  const sizeClasses = size === "sm" 
    ? "px-2.5 py-0.5 text-[10px]" 
    : "px-3 py-1 text-xs";

  if (normalized === "resolved" || normalized === "approved" || normalized === "success") {
    return (
      <span
        className={`inline-flex items-center rounded-full font-mono font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 ${sizeClasses} ${className}`}
      >
        resolved
      </span>
    );
  }

  if (normalized === "unresolved" || normalized === "rejected" || normalized === "failed" || normalized === "error") {
    return (
      <span
        className={`inline-flex items-center rounded-full font-mono font-bold uppercase tracking-wider bg-rose-500/15 text-rose-300 border border-rose-500/30 ${sizeClasses} ${className}`}
      >
        unresolved
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center rounded-full font-mono font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 ${sizeClasses} ${className}`}
    >
      {status}
    </span>
  );
}
