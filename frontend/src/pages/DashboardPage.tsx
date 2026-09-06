import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu,
  Layers,
  FileSpreadsheet,
  TrendingUp,
  Sparkles,
  RefreshCw,
  Scale,
} from "lucide-react";
import { fetchHealth, HealthResponse } from "../api/client";

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || "Failed to reach backend API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-blue-500/20 bg-gradient-to-r from-blue-950/40 via-indigo-950/20 to-slate-900/40 p-8">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
              <Sparkles className="h-3.5 w-3.5" />
              Transparent & Explainable Procurement Intelligence
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
              ProcureFlow <span className="gradient-text">Decision Engine</span>
            </h1>
            <p className="max-w-2xl text-sm text-slate-300">
              Transform messy, unstructured vendor quotations (PDF, Excel, CSV) into standardized,
              transparent, and audit-compliant procurement awards.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={loadHealth}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl border border-border bg-card/80 px-4 py-2 text-xs font-medium text-foreground hover:bg-secondary transition-all"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh Health
            </button>
          </div>
        </div>
      </div>

      {/* Core Infrastructure Health Bar */}
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-400" />
            <h2 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">
              Core Engine Health & Subsystems
            </h2>
          </div>
          <span className="text-xs text-muted-foreground">
            Version: {health?.version || "0.1.0"} ({health?.environment || "development"})
          </span>
        </div>

        {error ? (
          <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Backend service connectivity notice: {error} (verify FastAPI server is listening on port 8000)</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Database Service */}
            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
                  <Database className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-foreground">Relational Storage</div>
                  <div className="text-[11px] text-muted-foreground">PostgreSQL / Async SQLite</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{health?.database.status === "healthy" ? "Online" : "Ready"}</span>
              </div>
            </div>

            {/* Task Worker */}
            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
                  <Cpu className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-foreground">Ingestion Pipeline</div>
                  <div className="text-[11px] text-muted-foreground">Celery + Redis Broker</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Active</span>
              </div>
            </div>

            {/* AI Abstraction */}
            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-foreground">Structured AI Engine</div>
                  <div className="text-[11px] text-muted-foreground">OpenAI & Local Ollama Support</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Configured</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 4 Pillars of ProcureFlow */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs uppercase font-semibold">1. Multi-Format Intake</span>
            <FileSpreadsheet className="h-4 w-4 text-blue-400" />
          </div>
          <div className="text-lg font-bold text-white">PDF, Excel, CSV</div>
          <p className="text-xs text-muted-foreground">
            Automatic structure detection and layout-aware table extraction.
          </p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs uppercase font-semibold">2. Source Citations</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-white">Zero Black-Box</div>
          <p className="text-xs text-muted-foreground">
            Every extracted line item links directly to its source page and coordinate.
          </p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs uppercase font-semibold">3. Weighted Scoring</span>
            <Scale className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-lg font-bold text-white">Deterministic Math</div>
          <p className="text-xs text-muted-foreground">
            Configurable criteria weights, knockout conditions, and full score breakdowns.
          </p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs uppercase font-semibold">4. Audit Philosophy</span>
            <TrendingUp className="h-4 w-4 text-purple-400" />
          </div>
          <div className="text-lg font-bold text-white">Append-Only Logs</div>
          <p className="text-xs text-muted-foreground">
            Soft-delete archiving and full provenance on every decision override.
          </p>
        </div>
      </div>

      {/* Pipeline Workflow Visualizer */}
      <div className="glass-card rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-blue-400" />
            Standard Procurement Decision Journey
          </h2>
          <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-md border border-blue-500/20">
            Phase 0 Foundation Validated
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-6 gap-3 pt-2">
          {[
            { step: "01", title: "Create RFQ", desc: "Define items & weighted criteria" },
            { step: "02", title: "Upload Quotes", desc: "PDF, XLSX, CSV from vendors" },
            { step: "03", title: "Human Review", desc: "Side-by-side verification & audit" },
            { step: "04", title: "Normalization", desc: "Currency & unit alignment" },
            { step: "05", title: "Scoring Engine", desc: "Transparent ranking calculation" },
            { step: "06", title: "Award & Export", desc: "Decision record & PDF archive" },
          ].map((item) => (
            <div
              key={item.step}
              className="rounded-lg border border-border/70 bg-secondary/20 p-3.5 space-y-1.5 transition-all hover:border-blue-500/40"
            >
              <div className="text-[10px] font-mono font-bold text-blue-400">{item.step}</div>
              <div className="text-xs font-semibold text-foreground">{item.title}</div>
              <div className="text-[11px] text-muted-foreground leading-snug">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
