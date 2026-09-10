"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  PageHeader,
  Card,
  SectionHeader,
  StatusBadge,
  Button,
  LoadingState,
  ErrorState,
  EmptyState,
} from "@/components/ui";

const API_BASE = "http://localhost:8000/api";

interface Run {
  id: string;
  query: string;
  status: string;
  total_attempts: number;
  created_at: string;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "resolved" | "unresolved">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/runs`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setRuns(data.runs ?? []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = runs.filter((r) => {
    const matchQuery =
      (r.query || "").toLowerCase().includes(search.toLowerCase()) ||
      r.id.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filter === "all" || r.status === filter;
    return matchQuery && matchStatus;
  });

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Hero Header */}
      <PageHeader
        badgeText="Supabase Execution Logs"
        title="Pipeline Runs Directory"
        description="Complete historical archive of LangGraph pipeline executions. Click any run to inspect DAG flow, node-by-node telemetry, and token consumption."
        actions={
          <Button href="/" variant="secondary" size="md">
            &larr; Back to Dashboard
          </Button>
        }
      />

      {/* Filter & Search Bar Card */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {(["all", "resolved", "unresolved"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                filter === status
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                  : "bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              {status.toUpperCase()} (
              {status === "all"
                ? runs.length
                : runs.filter((r) => r.status === status).length}
              )
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-80">
          <input
            type="text"
            placeholder="Search query text or Run ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-900/80 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 font-mono focus:border-indigo-500/50 transition-colors"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-2 text-slate-500 hover:text-slate-300 text-xs font-mono"
            >
              CLEAR
            </button>
          )}
        </div>
      </div>

      {/* Directory Table Card */}
      <Card>
        <SectionHeader
          title="Recorded Telemetry Runs"
          subtitle={`Showing ${filtered.length} of ${runs.length} recorded runs in Supabase`}
          actions={
            <div className="text-xs font-mono text-slate-400">
              Total Recorded:{" "}
              <strong className="text-white font-mono">{runs.length}</strong>
            </div>
          }
        />

        {loading && (
          <LoadingState message="Querying agent_runs from Supabase..." />
        )}

        {error && (
          <ErrorState
            title="Failed to Load Runs"
            error={`Could not query ${API_BASE}/runs: ${error}`}
          />
        )}

        {!loading && !error && filtered.length === 0 && (
          <EmptyState
            title="No Matching Runs"
            message={
              search
                ? `No pipeline runs found matching "${search}".`
                : "No runs matching this status filter."
            }
            action={
              search ? (
                <button
                  onClick={() => setSearch("")}
                  className="text-xs font-mono text-indigo-400 hover:underline"
                >
                  Clear search filter
                </button>
              ) : undefined
            }
          />
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="divide-y divide-slate-800/60">
            {filtered.map((run) => (
              <Link
                key={run.id}
                href={`/trace/${run.id}`}
                className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-800/40 transition-colors group"
              >
                <div className="min-w-0 flex-1 pr-4 space-y-0.5">
                  <div className="text-sm font-medium text-slate-200 group-hover:text-indigo-300 transition-colors truncate">
                    {run.query || "(Empty Query)"}
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 selection:bg-indigo-900">
                    {run.id}
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <div className="text-right font-mono text-xs text-slate-400">
                    {run.total_attempts ?? 1} att.
                    <span className="text-slate-600 ml-2">
                      {relativeTime(run.created_at)}
                    </span>
                  </div>
                  <StatusBadge status={run.status} />
                  <span className="text-slate-600 group-hover:text-indigo-400 text-sm font-bold pl-1 transition-colors">
                    &rarr;
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
