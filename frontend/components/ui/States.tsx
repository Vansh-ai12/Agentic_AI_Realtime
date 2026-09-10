import React from "react";

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({
  message = "Loading telemetry data...",
  className = "",
}: LoadingStateProps) {
  return (
    <div
      className={`p-16 text-center text-slate-400 font-mono text-xs flex flex-col items-center justify-center gap-3 ${className}`}
    >
      <div className="relative w-8 h-8 flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-2 border-indigo-500/20" />
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
      <span className="text-slate-400">{message}</span>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  error: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Telemetry Query Failed",
  error,
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      className={`m-4 p-5 border border-rose-500/40 bg-rose-950/20 text-rose-300 rounded-xl text-xs font-mono space-y-2 ${className}`}
    >
      <div className="flex items-center gap-2 font-bold text-rose-200">
        <span className="text-rose-400 text-sm">⚠️</span>
        <span>{title}</span>
      </div>
      <p className="text-rose-300/80 leading-relaxed">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-3 py-1 bg-rose-900/40 hover:bg-rose-900/60 border border-rose-700/50 rounded text-rose-200 transition-colors"
        >
          Retry Request
        </button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title = "No Records Found",
  message = "No data recorded in the telemetry store matching your criteria.",
  icon = "📂",
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`p-16 text-center text-slate-400 space-y-3 flex flex-col items-center justify-center ${className}`}
    >
      <div className="text-3xl opacity-60 mb-1">{icon}</div>
      <div className="text-sm font-semibold text-slate-200">{title}</div>
      <div className="text-xs text-slate-500 max-w-sm font-mono leading-relaxed">
        {message}
      </div>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
