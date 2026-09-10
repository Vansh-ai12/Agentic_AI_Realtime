import React from "react";
import Link from "next/link";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  icon?: React.ReactNode;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  href,
  onClick,
  disabled = false,
  className = "",
  icon,
}: ButtonProps) {
  const baseClasses =
    "inline-flex items-center justify-center gap-1.5 font-semibold tracking-wide transition-all select-none rounded-lg font-sans";

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-xs",
  }[size];

  const variantClasses = {
    primary:
      "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 active:scale-[0.98]",
    secondary:
      "bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-slate-700/80 shadow-sm active:scale-[0.98]",
    ghost:
      "text-slate-400 hover:text-white hover:bg-slate-800/60 active:scale-[0.98]",
  }[variant];

  const disabledClasses = disabled
    ? "opacity-50 pointer-events-none cursor-not-allowed"
    : "";

  const combined = `${baseClasses} ${sizeClasses} ${variantClasses} ${disabledClasses} ${className}`;

  if (href) {
    return (
      <Link href={href} className={combined}>
        {icon}
        {children}
      </Link>
    );
  }

  return (
    <button onClick={onClick} disabled={disabled} className={combined}>
      {icon}
      {children}
    </button>
  );
}
