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

interface EvalRow {
  eval_case_id: string;
  category: string;
  query: string;
  eval_result_id: string | null;
  run_id: string | null;
  passed: boolean | null;
  notes: string | null;
  scored_at: string | null;
  tokens_used: number;
  run_status: string | null;
}

interface EvalPayload {
  summary: {
    eval_cases: number;
    scored: number;
    passed: number;
    pass_rate: number;
    by_category: Record<string, { total: number; scored: number; passed: number }>;
  };
  results: EvalRow[];
}

const CATEGORY_ORDER = ["normal", "adversarial", "missing_data", "edge_case"] as const;

export default function EvalPage() {
  const [data, setData] = useState<EvalPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pass" | "fail" | "unscored">("all");

  function load() {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/eval/results`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload: EvalPayload) => setData(payload))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  const rows = data?.results ?? [];
  const filtered = rows.filter((r) => {
    if (filter === "pass") return r.passed === true;
    if (filter === "fail") return r.passed === false;
    if (filter === "unscored") return r.passed === null;
    return true;
  });

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <PageHeader
        badgeText="D25 Evaluation Harness"
        title="Eval Results Dashboard"
        description="Real pipeline.invoke() runs against the 19 eval_cases stored in Supabase. Pass/fail is scored with rule-based checks plus an openai/gpt-oss-20b LLM judge."
        actions={
          <Button href="/runs" variant="secondary" size="md">
            View pipeline runs &rarr;
          </Button>
        }
      />

      {loading && (
        <Card>
          <LoadingState message="Querying eval_results joined with eval_cases..." />
        </Card>
      )}

      {error && (
        <ErrorState
          title="Failed to Load Eval Results"
          error={`Could not query ${API_BASE}/eval/results: ${error}`}
          onRetry={load}
        />
      )}

      {!loading && !error && data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Overall Pass Rate"
              value={`${data.summary.pass_rate.toFixed(1)}%`}
              sublabel={`${data.summary.passed}/${data.summary.scored} scored cases passed`}
              variant="emerald"
            />
            <MetricCard
              label="Cases Scored"
              value={data.summary.scored}
              sublabel={`${data.summary.eval_cases} eval_cases in Supabase`}
              variant="indigo"
            />
            <MetricCard
              label="Failed"
              value={data.summary.scored - data.summary.passed}
              sublabel="Did not meet rule or LLM criteria"
              variant="rose"
            />
            <MetricCard
              label="Unscored"
              value={data.summary.eval_cases - data.summary.scored}
              sublabel="No eval_results row yet"
              variant="amber"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {CATEGORY_ORDER.map((cat) => {
              const bucket = data.summary.by_category[cat] ?? { total: 0, scored: 0, passed: 0 };
              const rate = bucket.scored ? (bucket.passed / bucket.scored) * 100 : 0;
              return (
                <MetricCard
                  key={cat}
                  label={cat}
                  value={`${rate.toFixed(0)}%`}
                  sublabel={`${bucket.passed}/${bucket.scored} passed · ${bucket.total} cases`}
                  variant="neutral"
                />
              );
            })}
          </div>

          <Card>
            <SectionHeader
              title="All Eval Cases"
              subtitle="Latest eval_results row per case, joined with token_logs for that run_id"
              actions={
                <div className="flex items-center gap-2">
                  {(["all", "pass", "fail", "unscored"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                        filter === f
                          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                          : "bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-white"
                      }`}
                    >
                      {f.toUpperCase()}
                    </button>
                  ))}
                </div>
              }
            />

            {filtered.length === 0 && (
              <EmptyState
                title="No Matching Cases"
                message="No eval rows match this filter. Run backend/eval/run_eval.py to populate eval_results."
              />
            )}

            {filtered.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-mono text-[11px]">
                      <th className="py-2.5 px-4 text-left font-medium">Category</th>
                      <th className="py-2.5 px-4 text-left font-medium">Query</th>
                      <th className="py-2.5 px-4 text-left font-medium">Verdict</th>
                      <th className="py-2.5 px-4 text-left font-medium">Pass/Fail</th>
                      <th className="py-2.5 px-4 text-right font-medium">Tokens</th>
                      <th className="py-2.5 px-4 text-left font-medium">Run</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filtered.map((row) => (
                      <tr key={row.eval_case_id} className="hover:bg-slate-800/40 transition-colors align-top">
                        <td className="py-3 px-4 font-mono text-slate-300 whitespace-nowrap">
                          {row.category}
                        </td>
                        <td className="py-3 px-4 text-slate-200 max-w-md">
                          <div className="leading-relaxed">{row.query}</div>
                          {row.notes && (
                            <div className="mt-1 text-[11px] text-slate-500 font-mono line-clamp-2">
                              {row.notes}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {row.run_status ? (
                            <StatusBadge status={row.run_status} />
                          ) : (
                            <span className="text-slate-600 font-mono">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {row.passed === null ? (
                            <StatusBadge status="unscored" />
                          ) : (
                            <StatusBadge status={row.passed ? "pass" : "fail"} />
                          )}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.tokens_used ? row.tokens_used.toLocaleString() : "—"}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px]">
                          {row.run_id ? (
                            <Link
                              href={`/trace/${row.run_id}`}
                              className="text-indigo-400 hover:text-indigo-300"
                            >
                              {row.run_id.slice(0, 8)}…
                            </Link>
                          ) : (
                            <span className="text-slate-600">no run</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </main>
  );
}
