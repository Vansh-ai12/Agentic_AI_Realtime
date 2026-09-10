"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  PageHeader,
  MetricCard,
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

export default function DashboardHome() {
  const [runs, setRuns] = useState<Run[]>([]);
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

  const totalRuns = runs.length;
  const resolvedCount = runs.filter((r) => r.status === "resolved").length;
  const unresolvedCount = runs.filter((r) => r.status === "unresolved").length;

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Hero Header */}
      <PageHeader
        badgeText="LangGraph StateMachine Observability"
        title="Agentic RAG Telemetry Control Center"
        description="Live DAG visualization, granular node-by-node execution logs, and token compression analytics for multi-agent self-correcting RAG."
        actions={
          <Button href="/runs" variant="primary" size="md">
            Browse All Runs &rarr;
          </Button>
        }
      />

      {/* Top Telemetry KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Runs Logged"
          value={loading ? "..." : totalRuns}
          sublabel="Supabase agent_runs"
          variant="neutral"
        />
        <MetricCard
          label="Resolved Runs"
          value={loading ? "..." : resolvedCount}
          sublabel="Verified & approved"
          variant="emerald"
        />
        <MetricCard
          label="Unresolved Runs"
          value={loading ? "..." : unresolvedCount}
          sublabel="Max retry guardrails active"
          variant="rose"
        />
        <MetricCard
          label="D21 Token Reduction"
          value="18.8%"
          sublabel="2,967 tokens saved / run"
          variant="indigo"
        />
      </div>

      {/* Recent Runs Section */}
      <Card>
        <SectionHeader
          title="Recent Pipeline Runs"
          subtitle="Click any run to view the interactive DAG and execution timeline"
          actions={
            <Link
              href="/runs"
              className="text-xs text-indigo-400 hover:text-indigo-300 font-mono transition-colors"
            >
              View All &rarr;
            </Link>
          }
        />

        {loading && <LoadingState message="Querying recent runs from Supabase..." />}

        {error && (
          <ErrorState
            title="Backend Connection Failed"
            error={`Could not reach ${API_BASE}: ${error}`}
          />
        )}

        {!loading && !error && runs.length === 0 && (
          <EmptyState
            title="No Pipeline Runs"
            message="No pipeline runs recorded in the agent_runs table yet."
          />
        )}

        {!loading && !error && runs.length > 0 && (
          <div className="divide-y divide-slate-800/60">
            {runs.slice(0, 8).map((run) => (
              <Link
                key={run.id}
                href={`/trace/${run.id}`}
                className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-800/40 transition-colors group"
              >
                <div className="min-w-0 flex-1 pr-4 space-y-0.5">
                  <div className="text-sm font-medium text-slate-200 group-hover:text-indigo-300 transition-colors truncate">
                    {run.query || "(Empty Query)"}
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
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

      {/* D21 Optimization Banner */}
      <div className="border border-indigo-500/30 bg-gradient-to-r from-indigo-950/30 via-slate-900/60 to-purple-950/30 rounded-xl p-5 text-slate-200 shadow-sm backdrop-blur-sm">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span>📊</span> D21 Token Optimization Benchmark
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Empirical Results
          </span>
        </div>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed">
          Measuring prompt context compression across retry cycles by omitting already-cited chunks:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
            <div className="text-[11px] text-slate-500 font-mono">
              Naive Pipeline (Full Chunks)
            </div>
            <div className="text-base font-bold font-mono text-slate-200 mt-1">
              15,805 tokens
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
              3,733 prompt tokens / retry
            </div>
          </div>
          <div className="bg-slate-900/80 border border-indigo-500/30 rounded-lg p-3">
            <div className="text-[11px] text-indigo-400 font-mono">
              Optimized (D17 Compression)
            </div>
            <div className="text-base font-bold font-mono text-indigo-300 mt-1">
              12,838 tokens
            </div>
            <div className="text-[10px] text-indigo-400/80 mt-0.5 font-mono">
              532 prompt tokens on retry 2
            </div>
          </div>
          <div className="bg-slate-900/80 border border-emerald-500/30 rounded-lg p-3">
            <div className="text-[11px] text-emerald-400 font-mono">
              Measured Savings
            </div>
            <div className="text-base font-bold font-mono text-emerald-300 mt-1">
              18.8% Reduction
            </div>
            <div className="text-[10px] text-emerald-400/80 mt-0.5 font-mono">
              2,967 tokens conserved
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
