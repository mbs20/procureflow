import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Archive,
  RefreshCw,
  Copy,
  FileSpreadsheet,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  Scale,
} from "lucide-react";
import { RFQ, fetchRFQById, archiveRFQ, unarchiveRFQ, cloneRFQ } from "../api/rfq";

export const RFQDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [rfq, setRfq] = useState<RFQ | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRFQById(id);
      setRfq(data);
    } catch (err: any) {
      setError(err.message || "Failed to load RFQ");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleArchive = async () => {
    if (!rfq) return;
    try {
      await archiveRFQ(rfq.id);
      setActionMessage("RFQ archived (soft deleted)");
      loadData();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUnarchive = async () => {
    if (!rfq) return;
    try {
      await unarchiveRFQ(rfq.id);
      setActionMessage("RFQ restored to active");
      loadData();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleClone = async () => {
    if (!rfq) return;
    try {
      const cloned = await cloneRFQ(rfq.id, `${rfq.title} (Clone)`);
      navigate(`/rfqs/${cloned.id}`);
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-24 text-muted-foreground">
        <RefreshCw className="h-6 w-6 animate-spin text-blue-400" />
      </div>
    );
  }

  if (error || !rfq) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">RFQ Not Found</h2>
        <p className="text-xs text-muted-foreground">{error || "Could not retrieve procurement request."}</p>
        <Link to="/rfqs" className="inline-flex items-center gap-2 rounded-xl bg-secondary px-4 py-2 text-xs font-semibold text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to RFQ List
        </Link>
      </div>
    );
  }

  const totalWeight = (rfq.criteria || []).reduce((acc, c) => acc + (Number(c.weight) || 0), 0);
  const totalWeightPercent = Math.round(totalWeight * 100);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/rfqs"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{rfq.title}</h1>
              {rfq.is_archived ? (
                <span className="rounded bg-zinc-500/10 px-2 py-0.5 text-[11px] font-semibold text-zinc-400 border border-zinc-500/20">
                  Archived
                </span>
              ) : (
                <span className="rounded bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-400 border border-blue-500/20 uppercase">
                  {rfq.status}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
              <span>Category: <strong className="text-foreground">{rfq.category}</strong></span>
              <span>•</span>
              <span>Currency: <strong className="text-foreground">{rfq.reference_currency}</strong></span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Created {new Date(rfq.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleClone}
            className="flex items-center gap-1.5 rounded-xl bg-secondary/60 px-3.5 py-2 text-xs font-medium text-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
          >
            <Copy className="h-3.5 w-3.5" />
            Clone Template
          </button>

          {rfq.is_archived ? (
            <button
              onClick={handleUnarchive}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Restore RFQ
            </button>
          ) : (
            <button
              onClick={handleArchive}
              className="flex items-center gap-1.5 rounded-xl bg-secondary/60 px-3.5 py-2 text-xs font-medium text-muted-foreground hover:bg-red-500/20 hover:text-red-400 border border-border transition-colors"
            >
              <Archive className="h-3.5 w-3.5" />
              Archive
            </button>
          )}

          <Link
            to="/quotations"
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-white shadow-md shadow-blue-500/25 hover:bg-blue-600 transition-colors"
          >
            <Upload className="h-3.5 w-3.5" />
            Upload Quotations
          </Link>
        </div>
      </div>

      {actionMessage && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Scope / Notes */}
      {rfq.description && (
        <div className="glass-card rounded-xl p-5 space-y-1.5">
          <div className="text-xs uppercase font-semibold text-muted-foreground">Scope & Specification Notes</div>
          <p className="text-xs text-foreground leading-relaxed">{rfq.description}</p>
        </div>
      )}

      {/* Grid: Line Items + Criteria */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Line Items Table (2 cols) */}
        <div className="lg:col-span-2 glass-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-blue-400" />
              Required Line Items ({rfq.line_items?.length || 0})
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border/80 text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3 text-right">Quantity</th>
                  <th className="py-2.5 px-3">Unit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {(rfq.line_items || []).map((item, idx) => (
                  <tr key={item.id || idx} className="hover:bg-secondary/20 transition-colors">
                    <td className="py-3 px-3 font-mono text-muted-foreground">{item.position || idx + 1}</td>
                    <td className="py-3 px-3 font-medium text-foreground">{item.description}</td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-blue-400">{item.quantity}</td>
                    <td className="py-3 px-3 text-muted-foreground">{item.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Evaluation Criteria Rubric (1 col) */}
        <div className="glass-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Scale className="h-4 w-4 text-purple-400" />
              Weighted Criteria
            </h2>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
              Total {totalWeightPercent}%
            </span>
          </div>

          <div className="space-y-3">
            {(rfq.criteria || []).map((crit, idx) => {
              const weightPct = Math.round(Number(crit.weight) * 100);
              return (
                <div key={crit.id || idx} className="rounded-lg border border-border/70 bg-secondary/20 p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">{crit.name}</span>
                    <span className="rounded bg-purple-500/10 px-2 py-0.5 text-xs font-mono font-bold text-purple-400 border border-purple-500/20">
                      {weightPct}%
                    </span>
                  </div>
                  {crit.description && (
                    <p className="text-[11px] text-muted-foreground">{crit.description}</p>
                  )}
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1">
                    <span>Direction: <strong className="text-foreground">{crit.direction === "lower_is_better" ? "Lower is better" : "Higher is better"}</strong></span>
                    {crit.is_knockout && (
                      <span className="text-red-400 font-semibold">Knockout Rule</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="rounded-lg border border-border/50 bg-secondary/30 p-3 text-[11px] text-muted-foreground space-y-1">
            <div className="flex items-center gap-1.5 text-foreground font-semibold">
              <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
              Scoring Philosophy
            </div>
            <p>
              When supplier quotations are uploaded, this RFQ will evaluate all normalized bids against these criteria with mathematical explainability.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
