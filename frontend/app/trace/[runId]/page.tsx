"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
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

/* ─── Groq model pricing (ESTIMATED, unverified) ──────────────────────── */
const PRICING: Record<string, { input: number; output: number }> = {
  "openai/gpt-oss-20b":  { input: 0.10 / 1_000_000, output: 0.30 / 1_000_000 },
  "openai/gpt-oss-120b": { input: 0.60 / 1_000_000, output: 1.80 / 1_000_000 },
};
const DEFAULT_PRICING = { input: 0.30 / 1_000_000, output: 0.90 / 1_000_000 };

/* ─── Types ──────────────────────────────────────────────────────────── */
interface TraceEvent {
  id: string;
  run_id: string;
  attempt_id: string | null;
  node_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  tokens_used: number;
  latency_ms: number;
  created_at: string;
}

interface TokenLog {
  id: string;
  run_id: string;
  attempt_id: string | null;
  agent_role: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  created_at: string;
}

interface RunInfo {
  id: string;
  query: string;
  status: string;
  total_attempts: number;
  created_at: string;
  completed_at: string | null;
}

interface TraceData {
  run: RunInfo | null;
  attempts: unknown[];
  events: TraceEvent[];
  token_logs: TokenLog[];
}

/* ─── Pipeline topology ──────────────────────────────────────────────── */
const PIPELINE_NODES = [
  "memory_reader",
  "planner",
  "retriever",
  "synthesizer",
  "citation_verifier",
  "critic",
] as const;

const NODE_META: Record<
  string,
  { label: string; icon: string; category: "utility" | "llm" | "gate" | "terminal" }
> = {
  memory_reader:     { label: "Memory Reader",     icon: "🧠", category: "utility" },
  planner:           { label: "Planner",           icon: "🧭", category: "llm" },
  retriever:         { label: "Retriever",         icon: "🔍", category: "utility" },
  synthesizer:       { label: "Synthesizer",       icon: "⚡", category: "llm" },
  citation_verifier: { label: "Citation Verifier", icon: "📑", category: "gate" },
  critic:            { label: "Critic",            icon: "⚖️", category: "gate" },
  write_memory:      { label: "Write Memory",      icon: "💾", category: "terminal" },
  unresolved:        { label: "Unresolved",        icon: "🚫", category: "terminal" },
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function estimateCost(model: string, tokensIn: number, tokensOut: number): number {
  const p = PRICING[model] ?? DEFAULT_PRICING;
  return tokensIn * p.input + tokensOut * p.output;
}

/* ═══════════════════════════════════════════════════════════════════════
   DAG VISUALIZATION — Integrated SVG Flow
   ═══════════════════════════════════════════════════════════════════════ */
function DagView({ events, status }: { events: TraceEvent[]; status: string }) {
  const nodeCounts: Record<string, number> = {};
  for (const e of events) {
    nodeCounts[e.node_name] = (nodeCounts[e.node_name] ?? 0) + 1;
  }

  const nodeW = 145;
  const nodeH = 50;
  const gapX = 36;
  const startX = 24;
  const topY = 48;
  const botY = 160;

  const positions: Record<string, { x: number; y: number }> = {};
  PIPELINE_NODES.forEach((n, i) => {
    positions[n] = { x: startX + i * (nodeW + gapX), y: topY };
  });

  const criticPos = positions["critic"];
  positions["write_memory"] = { x: criticPos.x - 90, y: botY };
  positions["unresolved"] = { x: criticPos.x + 90, y: botY };

  const svgW = startX * 2 + PIPELINE_NODES.length * (nodeW + gapX);
  const svgH = botY + nodeH + 36;

  const synthCount = nodeCounts["synthesizer"] ?? 0;
  const retryCycles = Math.max(0, synthCount - 1);

  function getNodeStyle(name: string) {
    const count = nodeCounts[name] ?? 0;
    const isReached = count > 0;

    if (!isReached) {
      return {
        fill: "#0f172a",
        stroke: "#334155",
        text: "#64748b",
        subtext: "#475569",
        badge: null,
      };
    }

    if (name === "unresolved") {
      return {
        fill: "#260b13",
        stroke: "#f43f5e",
        text: "#fecdd3",
        subtext: "#fb7185",
        badge: { bg: "#881337", text: "#ffe4e6", label: "Failed" },
      };
    }

    if (name === "write_memory") {
      return {
        fill: "#062817",
        stroke: "#10b981",
        text: "#d1fae5",
        subtext: "#34d399",
        badge: { bg: "#064e3b", text: "#a7f3d0", label: "Success" },
      };
    }

    if (name === "critic") {
      const lastCritic = [...events].reverse().find((e) => e.node_name === "critic");
      const verdict = lastCritic?.output?.verdict;
      if (verdict === "approve") {
        return {
          fill: "#062817",
          stroke: "#10b981",
          text: "#d1fae5",
          subtext: "#34d399",
          badge: { bg: "#064e3b", text: "#a7f3d0", label: "Approved" },
        };
      }
      return {
        fill: "#241105",
        stroke: "#f59e0b",
        text: "#fef3c7",
        subtext: "#fbbf24",
        badge: { bg: "#78350f", text: "#fde68a", label: `Rejected (${count}x)` },
      };
    }

    if (name === "synthesizer" && count > 1) {
      return {
        fill: "#231806",
        stroke: "#d97706",
        text: "#fef3c7",
        subtext: "#fbbf24",
        badge: { bg: "#78350f", text: "#fde68a", label: `${count} attempts` },
      };
    }

    return {
      fill: "#111827",
      stroke: "#6366f1",
      text: "#e0e7ff",
      subtext: "#a5b4fc",
      badge: count > 1 ? { bg: "#312e81", text: "#c7d2fe", label: `${count}x` } : null,
    };
  }

  return (
    <div className="overflow-x-auto pb-2">
      <svg width={svgW} height={svgH} className="mx-auto select-none">
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
          </marker>
          <marker id="arrow-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#818cf8" />
          </marker>
          <marker id="arrow-amber" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" />
          </marker>
          <marker id="arrow-rose" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#f43f5e" />
          </marker>
          <marker id="arrow-emerald" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#10b981" />
          </marker>
        </defs>

        {/* Linear edges */}
        {PIPELINE_NODES.slice(0, -1).map((fromNode, i) => {
          const toNode = PIPELINE_NODES[i + 1];
          const p1 = positions[fromNode];
          const p2 = positions[toNode];
          const active = (nodeCounts[toNode] ?? 0) > 0;
          return (
            <line
              key={`${fromNode}->${toNode}`}
              x1={p1.x + nodeW}
              y1={p1.y + nodeH / 2}
              x2={p2.x - 2}
              y2={p2.y + nodeH / 2}
              stroke={active ? "#6366f1" : "#334155"}
              strokeWidth={active ? 2 : 1.5}
              strokeDasharray={active ? undefined : "4 3"}
              markerEnd={active ? "url(#arrow-active)" : "url(#arrow)"}
            />
          );
        })}

        {/* Terminal branches from critic */}
        {criticPos && (
          <>
            <path
              d={`M ${criticPos.x + nodeW / 2 - 20} ${criticPos.y + nodeH} C ${criticPos.x + nodeW / 2 - 20} ${botY - 20}, ${positions["write_memory"].x + nodeW / 2} ${botY - 25}, ${positions["write_memory"].x + nodeW / 2} ${botY - 2}`}
              fill="none"
              stroke={status === "resolved" ? "#10b981" : "#334155"}
              strokeWidth={status === "resolved" ? 2.5 : 1}
              strokeDasharray={status === "resolved" ? undefined : "4 3"}
              markerEnd={status === "resolved" ? "url(#arrow-emerald)" : "url(#arrow)"}
            />
            <path
              d={`M ${criticPos.x + nodeW / 2 + 20} ${criticPos.y + nodeH} C ${criticPos.x + nodeW / 2 + 20} ${botY - 20}, ${positions["unresolved"].x + nodeW / 2} ${botY - 25}, ${positions["unresolved"].x + nodeW / 2} ${botY - 2}`}
              fill="none"
              stroke={status === "unresolved" ? "#f43f5e" : "#334155"}
              strokeWidth={status === "unresolved" ? 2.5 : 1}
              strokeDasharray={status === "unresolved" ? undefined : "4 3"}
              markerEnd={status === "unresolved" ? "url(#arrow-rose)" : "url(#arrow)"}
            />
          </>
        )}

        {/* Retry Loop Arc: critic → synthesizer */}
        {retryCycles > 0 && positions["synthesizer"] && positions["critic"] && (() => {
          const s = positions["synthesizer"];
          const c = positions["critic"];
          const sx = s.x + nodeW / 2;
          const cx = c.x + nodeW / 2;
          const arcTopY = topY - 34;

          return (
            <g>
              <path
                d={`M ${cx} ${topY} C ${cx} ${arcTopY}, ${sx} ${arcTopY}, ${sx} ${topY - 3}`}
                fill="none"
                stroke="#f59e0b"
                strokeWidth={3}
                strokeOpacity={0.3}
              />
              <path
                d={`M ${cx} ${topY} C ${cx} ${arcTopY}, ${sx} ${arcTopY}, ${sx} ${topY - 3}`}
                fill="none"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="6 4"
                markerEnd="url(#arrow-amber)"
              />
              <g transform={`translate(${(sx + cx) / 2 - 68}, ${arcTopY - 12})`}>
                <rect width="136" height="22" rx="11" fill="#78350f" stroke="#f59e0b" strokeWidth="1" />
                <text
                  x="68"
                  y="14"
                  textAnchor="middle"
                  fill="#fef3c7"
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="monospace"
                >
                  ↺ RETRY LOOP ({retryCycles}x)
                </text>
              </g>
            </g>
          );
        })()}

        {/* Render Node Cards */}
        {[...PIPELINE_NODES, "write_memory", "unresolved"].map((name) => {
          const pos = positions[name];
          if (!pos) return null;
          const style = getNodeStyle(name);
          const meta = NODE_META[name];

          return (
            <g key={name} transform={`translate(${pos.x}, ${pos.y})`}>
              <rect
                width={nodeW}
                height={nodeH}
                rx="10"
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth={nodeCounts[name] ? "1.5" : "1"}
                className="transition-all duration-200"
              />
              <text x="12" y="24" fontSize="13">
                {meta?.icon ?? "⚙️"}
              </text>
              <text
                x="32"
                y="24"
                fill={style.text}
                fontSize="11.5"
                fontWeight="600"
                letterSpacing="-0.01em"
              >
                {meta?.label ?? name}
              </text>
              {style.badge ? (
                <g transform={`translate(32, 30)`}>
                  <rect width={style.badge.label.length * 6 + 10} height="14" rx="4" fill={style.badge.bg} />
                  <text x="5" y="10.5" fill={style.badge.text} fontSize="9" fontWeight="700" fontFamily="monospace">
                    {style.badge.label}
                  </text>
                </g>
              ) : (
                <text x="32" y="40" fill={style.subtext} fontSize="9.5" fontFamily="monospace">
                  {meta?.category.toUpperCase()}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   NODE EXECUTION TIMELINE — Connected Visual Flow
   ═══════════════════════════════════════════════════════════════════════ */
function ExecutionFlowTimeline({ events }: { events: TraceEvent[] }) {
  let retryCount = 0;
  let currentAttempt = 1;
  const retryNodes = new Set(["synthesizer", "citation_verifier", "critic"]);

  return (
    <div className="relative pl-6 sm:pl-8 space-y-6">
      <div className="absolute left-3 sm:left-4 top-4 bottom-4 w-0.5 bg-gradient-to-b from-indigo-500 via-purple-500/50 to-slate-800" />

      {events.map((event, idx) => {
        if (event.node_name === "synthesizer" && idx > 0) {
          const prevHadLoop = events.slice(0, idx).some((e) => retryNodes.has(e.node_name));
          if (prevHadLoop) {
            retryCount++;
            currentAttempt++;
          }
        }

        const isRetry = retryCount > 0 && retryNodes.has(event.node_name);
        const meta = NODE_META[event.node_name];

        const isApproved = event.output?.verdict === "approve";
        const isRejected = event.output?.verdict === "reject";
        const isUnresolved = event.node_name === "unresolved";
        const isMemorySaved = event.node_name === "write_memory";

        let statusBorder = "border-slate-800 bg-slate-900/60";
        let dotColor = "bg-indigo-500 ring-indigo-500/20";

        if (isApproved || isMemorySaved) {
          statusBorder = "border-emerald-500/40 bg-emerald-950/20";
          dotColor = "bg-emerald-400 ring-emerald-400/30";
        } else if (isRejected || isUnresolved) {
          statusBorder = "border-rose-500/40 bg-rose-950/20";
          dotColor = "bg-rose-400 ring-rose-400/30";
        } else if (isRetry) {
          statusBorder = "border-amber-500/40 bg-amber-950/20";
          dotColor = "bg-amber-400 ring-amber-400/30";
        }

        return (
          <div key={event.id ?? idx} className="relative group">
            <div
              className={`absolute -left-6 sm:-left-8 top-4 w-4 h-4 rounded-full border-2 border-[#090d16] ${dotColor} ring-4 flex items-center justify-center`}
            />

            <div className={`border rounded-xl p-4 transition-all duration-150 backdrop-blur-sm shadow-sm ${statusBorder}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                <div className="flex items-center gap-2.5">
                  <span className="text-base">{meta?.icon ?? "⚙️"}</span>
                  <span className="font-semibold text-sm text-slate-100">
                    {meta?.label ?? event.node_name}
                  </span>

                  {isRetry && (
                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[10px] font-mono">
                      <span>Attempt {currentAttempt} of 3</span>
                      <div className="flex gap-0.5 ml-1">
                        {[1, 2, 3].map((step) => (
                          <span
                            key={step}
                            className={`w-1.5 h-1.5 rounded-full ${
                              step <= currentAttempt ? "bg-amber-400" : "bg-slate-700"
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {isApproved && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      APPROVED
                    </span>
                  )}
                  {isRejected && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                      REJECTED
                    </span>
                  )}
                  {isUnresolved && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-600/30 text-rose-200 border border-rose-500/60 animate-pulse">
                      MAX RETRIES EXCEEDED
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                  {event.latency_ms > 0 && (
                    <span className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 text-[11px]">
                      ⏱ {formatMs(event.latency_ms)}
                    </span>
                  )}
                  {event.tokens_used > 0 && (
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[11px]">
                      🪙 {event.tokens_used.toLocaleString()} tok
                    </span>
                  )}
                  <span className="text-slate-500 text-[11px]">
                    {new Date(event.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              <div className="pt-2 text-xs text-slate-300 space-y-1">
                {Boolean(event.output?.verdict) && (
                  <div className="text-xs">
                    <span className="text-slate-500">Reason: </span>
                    <span className="text-slate-200 italic">{String(event.output?.reason ?? "")}</span>
                  </div>
                )}
                {Boolean(event.output?.final_reason) && (
                  <div className="text-xs text-rose-300 font-medium">
                    ⚠️ {String(event.output?.final_reason)}
                  </div>
                )}
                {event.output?.chunks_retrieved !== undefined && (
                  <div className="text-xs text-slate-400">
                    Retrieved <strong className="text-slate-200">{String(event.output.chunks_retrieved)}</strong> contextual chunks
                  </div>
                )}
                {Array.isArray(event.output?.sub_questions) && (
                  <div className="text-xs text-slate-400">
                    Planned into {event.output.sub_questions.length} sub-queries
                  </div>
                )}
              </div>

              <details className="mt-3 group/details">
                <summary className="text-[11px] font-mono text-indigo-400 hover:text-indigo-300 cursor-pointer select-none flex items-center gap-1.5 transition-colors">
                  <span className="group-open/details:rotate-90 transition-transform">▸</span>
                  Inspect Input / Output Payload
                </summary>
                <div className="mt-2.5 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold mb-1">
                      Input
                    </div>
                    <pre className="bg-[#060910] border border-slate-800/80 rounded-lg p-3 overflow-x-auto max-h-52 text-[11px] font-mono text-slate-300 whitespace-pre-wrap break-all selection:bg-indigo-900">
                      {JSON.stringify(event.input, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold mb-1">
                      Output
                    </div>
                    <pre className="bg-[#060910] border border-slate-800/80 rounded-lg p-3 overflow-x-auto max-h-52 text-[11px] font-mono text-slate-300 whitespace-pre-wrap break-all selection:bg-indigo-900">
                      {JSON.stringify(event.output, null, 2)}
                    </pre>
                  </div>
                </div>
              </details>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TOKEN & COST PANEL — Executive Breakdown
   ═══════════════════════════════════════════════════════════════════════ */
function TokenCostPanel({ tokenLogs }: { tokenLogs: TokenLog[] }) {
  const byRole: Record<
    string,
    { model: string; tokens_in: number; tokens_out: number; total: number; cost: number }
  > = {};

  for (const t of tokenLogs) {
    if (!byRole[t.agent_role]) {
      byRole[t.agent_role] = { model: t.model, tokens_in: 0, tokens_out: 0, total: 0, cost: 0 };
    }
    const r = byRole[t.agent_role];
    r.tokens_in += t.tokens_in;
    r.tokens_out += t.tokens_out;
    r.total += t.tokens_in + t.tokens_out;
    r.cost += estimateCost(t.model, t.tokens_in, t.tokens_out);
    r.model = t.model;
  }

  const grandIn = tokenLogs.reduce((s, t) => s + t.tokens_in, 0);
  const grandOut = tokenLogs.reduce((s, t) => s + t.tokens_out, 0);
  const grandTotal = grandIn + grandOut;
  const grandCost = Object.values(byRole).reduce((s, r) => s + r.cost, 0);

  const roleColors: Record<string, string> = {
    synthesizer: "bg-indigo-500",
    planner: "bg-sky-500",
    critic: "bg-amber-500",
    citation_verifier: "bg-teal-500",
  };

  if (tokenLogs.length === 0) {
    return (
      <EmptyState
        title="No Token Logs Recorded"
        message="No granular token usage was logged for this run in the token_logs table."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Tokens"
          value={grandTotal.toLocaleString()}
          sublabel="Sum of all LLM node calls"
          variant="neutral"
          icon="⚡"
        />
        <MetricCard
          label="Tokens In (Prompt)"
          value={grandIn.toLocaleString()}
          sublabel="Context chunks + instructions"
          variant="indigo"
          icon="↓"
        />
        <MetricCard
          label="Tokens Out (Comp.)"
          value={grandOut.toLocaleString()}
          sublabel="Generated outputs & critiques"
          variant="neutral"
          icon="↑"
        />
        <MetricCard
          label="Est. Cost"
          value={`$${grandCost.toFixed(5)}`}
          sublabel="Approximate Groq API estimate"
          variant="amber"
          icon="$"
          tooltip="Pricing is estimated based on Groq gpt-oss tier assumptions ($0.10-$0.60/M in, $0.30-$1.80/M out). Unverified approximation. Tokens are exact measured values."
        />
      </div>

      {/* Proportional Token Distribution Bar */}
      <div className="border border-slate-800/80 bg-slate-900/60 rounded-xl p-4 shadow-sm backdrop-blur-sm">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-300">
            Relative Consumption by Agent Role
          </span>
          <span className="text-[11px] font-mono text-slate-500">
            {Object.keys(byRole).length} active roles
          </span>
        </div>

        <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden flex">
          {Object.entries(byRole).map(([role, data]) => {
            const pct = grandTotal > 0 ? (data.total / grandTotal) * 100 : 0;
            return (
              <div
                key={role}
                style={{ width: `${pct}%` }}
                className={`h-full ${roleColors[role] ?? "bg-slate-500"} transition-all duration-300`}
                title={`${role}: ${data.total.toLocaleString()} tokens (${pct.toFixed(1)}%)`}
              />
            );
          })}
        </div>

        <div className="flex flex-wrap gap-4 mt-3 text-xs">
          {Object.entries(byRole).map(([role, data]) => {
            const pct = grandTotal > 0 ? (data.total / grandTotal) * 100 : 0;
            return (
              <div key={role} className="flex items-center gap-1.5">
                <span className={`w-2.5 h-2.5 rounded-full ${roleColors[role] ?? "bg-slate-500"}`} />
                <span className="text-slate-300 font-medium capitalize">{role}</span>
                <span className="text-slate-500 font-mono text-[11px]">
                  ({pct.toFixed(1)}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Breakdown Table */}
      <div className="border border-slate-800/80 bg-slate-900/60 rounded-xl overflow-hidden shadow-sm backdrop-blur-sm">
        <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-300">
          Agent Role Breakdown &amp; Model Routing
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-mono text-[11px]">
                <th className="py-2.5 px-4 text-left font-medium">Agent Role</th>
                <th className="py-2.5 px-4 text-left font-medium">Model</th>
                <th className="py-2.5 px-4 text-right font-medium">Tokens In</th>
                <th className="py-2.5 px-4 text-right font-medium">Tokens Out</th>
                <th className="py-2.5 px-4 text-right font-medium">Total</th>
                <th className="py-2.5 px-4 text-right font-medium text-amber-400">
                  Cost <span className="italic font-normal">(est.)</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {Object.entries(byRole)
                .sort((a, b) => b[1].total - a[1].total)
                .map(([role, data]) => (
                  <tr key={role} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-4 font-medium text-slate-200 flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${roleColors[role] ?? "bg-slate-500"}`} />
                      {role}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-slate-400 text-[11px]">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/60">
                        {data.model}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                      {data.tokens_in.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                      {data.tokens_out.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono font-bold text-white">
                      {data.total.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-amber-300">
                      ${data.cost.toFixed(5)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="px-1 text-[11px] text-slate-500 italic flex items-center gap-1.5">
        <span className="text-amber-400">⚠️</span>
        Dollar figures use unverified estimates for Groq gpt-oss pricing models. Token counts are exact measured values from Supabase telemetry.
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN TRACE PAGE
   ═══════════════════════════════════════════════════════════════════════ */
export default function TracePage() {
  const { runId } = useParams<{ runId: string }>();
  const [data, setData] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    fetch(`${API_BASE}/runs/${runId}/trace`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <LoadingState message="Streaming trace events from Supabase telemetry..." />
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <ErrorState
          title="Failed to Load Run Trace"
          error={error}
          onRetry={() => window.location.reload()}
        />
      </main>
    );
  }

  if (!data?.run) {
    return (
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <EmptyState
          title="Run Not Found"
          message={`No run record exists in Supabase matching ID "${runId}".`}
          action={
            <Button href="/runs" variant="secondary" size="sm">
              &larr; Return to Runs Directory
            </Button>
          }
        />
      </main>
    );
  }

  const { run, events, token_logs } = data;
  const isUnresolved = run.status === "unresolved";
  const isResolved = run.status === "resolved";

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Back Link */}
      <div>
        <Link
          href="/runs"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-indigo-300 transition-colors"
        >
          <span>&larr;</span> Back to Runs Directory
        </Link>
      </div>

      {/* Hero Header matching Dashboard styling */}
      <PageHeader
        badgeText="LangGraph Execution Trace"
        variant={isUnresolved ? "rose" : isResolved ? "emerald" : "indigo"}
        statusBadge={
          <div className="flex items-center gap-2">
            <StatusBadge status={run.status} size="sm" />
            <span className="text-xs font-mono text-slate-400 bg-slate-900/70 border border-slate-800 px-2 py-0.5 rounded">
              {run.total_attempts ?? 1} Attempt{(run.total_attempts || 1) !== 1 ? "s" : ""}
            </span>
            <span className="text-xs font-mono text-slate-500">
              {new Date(run.created_at).toLocaleTimeString()}
            </span>
          </div>
        }
        title={run.query || "(Empty Query)"}
        description={
          <div className="font-mono text-xs text-slate-400 selection:bg-indigo-900">
            Run ID: <span className="text-slate-300">{run.id}</span>
          </div>
        }
        actions={
          isUnresolved ? (
            <div className="border border-rose-500/30 bg-rose-950/30 rounded-xl px-4 py-3 text-rose-200">
              <div className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                <span>⚠️</span> Unresolved Execution
              </div>
              <div className="text-[11px] text-rose-300/80 mt-1 max-w-xs font-mono">
                Failed verification after retry ceiling
              </div>
            </div>
          ) : isResolved ? (
            <div className="border border-emerald-500/30 bg-emerald-950/30 rounded-xl px-4 py-3 text-emerald-200">
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <span>✓</span> Verified &amp; Approved
              </div>
              <div className="text-[11px] text-emerald-300/80 mt-1 font-mono">
                Passed critic verification &amp; saved to memory
              </div>
            </div>
          ) : undefined
        }
      />

      {/* Section 1: DAG Flow */}
      <Card>
        <SectionHeader
          icon="❖"
          title="Pipeline DAG Execution Graph"
          subtitle="LangGraph StateMachine Topology with retry loop cycles"
        />
        <div className="p-5">
          <DagView events={events} status={run.status} />
        </div>
      </Card>

      {/* Section 2: Execution Flow Timeline */}
      <Card>
        <SectionHeader
          icon="⚡"
          title={`Granular Execution Flow (${events.length} events)`}
          subtitle="Chronological trace_events telemetry with payload inspection"
        />
        <div className="p-6">
          <ExecutionFlowTimeline events={events} />
        </div>
      </Card>

      {/* Section 3: Token Usage & Cost Panel */}
      <Card>
        <SectionHeader
          icon="🪙"
          title="Token Consumption &amp; Cost Telemetry"
          subtitle="Recorded via Supabase token_logs with Groq pricing estimations"
        />
        <div className="p-6">
          <TokenCostPanel tokenLogs={token_logs} />
        </div>
      </Card>
    </main>
  );
}
