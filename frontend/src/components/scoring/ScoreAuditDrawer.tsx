import React from "react";
import { X, CheckCircle, AlertTriangle, ShieldAlert, FileText } from "lucide-react";
import { SupplierScore } from "../../api/scoring";

interface ScoreAuditDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  supplierScore: SupplierScore | null;
  snapshotVersion?: number;
  configVersion?: number;
}

export const ScoreAuditDrawer: React.FC<ScoreAuditDrawerProps> = ({
  isOpen,
  onClose,
  supplierScore,
  snapshotVersion,
  configVersion,
}) => {
  if (!isOpen || !supplierScore) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-drawer-title"
    >
      <div className="w-full max-w-xl bg-card border-l border-border h-full flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-border/80 flex items-center justify-between bg-card/50">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-blue-400">
                Deterministic Score Audit
              </span>
              {supplierScore.rank && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                  Rank #{supplierScore.rank}
                </span>
              )}
            </div>
            <h2 id="audit-drawer-title" className="text-xl font-bold text-white mt-1">
              {supplierScore.supplier_name}
            </h2>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
              <span>Snapshot v{snapshotVersion ?? 1}</span>
              <span>•</span>
              <span>Scoring Config v{configVersion ?? 1}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted-foreground hover:text-white hover:bg-secondary/80 transition-colors"
            aria-label="Close audit drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status Banner */}
          <div
            className={`p-4 rounded-xl border flex items-start gap-3 ${
              supplierScore.is_eligible
                ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-200"
                : "bg-red-950/20 border-red-800/40 text-red-200"
            }`}
          >
            {supplierScore.is_eligible ? (
              <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-semibold text-sm">
                Status: {supplierScore.status.toUpperCase()}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {supplierScore.is_eligible
                  ? "Passed all deterministic knockout gates and evaluated in relative scoring cohort."
                  : `Disqualified from competitive ranking. Reason: ${supplierScore.knockout_reasons.join(", ")}`}
              </p>
            </div>
          </div>

          {/* Composite Score Card */}
          <div className="glass-card rounded-xl p-5 border border-border/80 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase font-bold text-muted-foreground">Composite Evaluation Score</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Sum of weighted criterion contributions (0.00 – 100.00)
              </div>
            </div>
            <div className="text-3xl font-mono font-black text-blue-400">
              {supplierScore.composite_score.toFixed(2)}
              <span className="text-sm font-normal text-muted-foreground"> / 100</span>
            </div>
          </div>

          {/* Criteria Breakdown */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              Formula & Criterion Breakdown
            </h3>

            {Object.entries(supplierScore.breakdown).map(([criterionName, b]) => (
              <div
                key={criterionName}
                className="rounded-xl border border-border/70 bg-secondary/20 p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm text-white">{criterionName}</div>
                  <div className="text-xs font-mono font-bold text-emerald-400">
                    +{b.weighted_contribution.toFixed(2)} pts
                    <span className="text-muted-foreground font-normal text-[11px] ml-1">
                      (w = {(b.weight * 100).toFixed(1)}%)
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-card/60 p-3 rounded-lg border border-border/40 font-mono">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Raw Value</span>
                    <span className="text-foreground font-semibold">
                      {b.raw_value !== null ? String(b.raw_value) : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Cohort Bounds</span>
                    <span className="text-muted-foreground">
                      {b.cohort_min != null && b.cohort_max != null
                        ? `[${b.cohort_min}, ${b.cohort_max}]`
                        : "Single/Fixed"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Norm Score</span>
                    <span className="text-blue-400 font-bold">{b.normalized_score.toFixed(2)} / 100</span>
                  </div>
                </div>

                {/* Mathematical Equation display */}
                <div className="text-[11px] text-muted-foreground bg-secondary/30 p-2.5 rounded-lg border border-border/30 font-mono">
                  <span className="text-foreground font-semibold">Formula: </span>
                  {b.cohort_min !== null && b.cohort_max !== null && b.cohort_min !== b.cohort_max ? (
                    <span>
                      Normalized = ({b.raw_value} - {b.cohort_min}) / ({b.cohort_max} - {b.cohort_min}) × 100 ={" "}
                      {b.normalized_score.toFixed(2)}
                    </span>
                  ) : (
                    <span>Normalized = 100.00 (Cohort variance zero or single candidate)</span>
                  )}
                  <br />
                  <span className="text-foreground font-semibold">Contribution: </span>
                  <span>
                    {b.normalized_score.toFixed(2)} × {b.weight.toFixed(4)} = {b.weighted_contribution.toFixed(2)}
                  </span>
                </div>

                {b.source_path && (
                  <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground">Source Binding:</span>
                    <span className="text-primary truncate" title={b.source_path}>
                      {b.source_path}
                    </span>
                  </div>
                )}
                {b.notes && (
                  <div className="text-xs text-amber-300/90 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>{b.notes}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border/80 bg-card/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-secondary text-sm font-semibold text-foreground hover:bg-secondary/80 transition-colors"
          >
            Close Audit
          </button>
        </div>
      </div>
    </div>
  );
};
