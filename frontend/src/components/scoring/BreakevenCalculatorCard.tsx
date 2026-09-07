import React, { useState } from "react";
import { BreakevenResult, SupplierScore } from "../../api/scoring";
import { Calculator, ArrowDownRight, CheckCircle2, ShieldAlert, Cpu } from "lucide-react";

interface BreakevenCalculatorCardProps {
  scores: SupplierScore[];
  onCalculateBreakeven: (supplierId: string) => Promise<void>;
  breakevenResult: BreakevenResult | null;
  isLoading?: boolean;
}

export const BreakevenCalculatorCard: React.FC<BreakevenCalculatorCardProps> = ({
  scores,
  onCalculateBreakeven,
  breakevenResult,
  isLoading = false,
}) => {
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>(
    scores.length > 1 ? scores[1].quotation_id : scores[0]?.quotation_id || ""
  );

  const handleCompute = async () => {
    if (!selectedSupplierId) return;
    await onCalculateBreakeven(selectedSupplierId);
  };

  return (
    <div className="glass-card rounded-xl p-5 space-y-5 border border-border/80">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Calculator className="h-4 w-4 text-primary" />
            Authoritative Breakeven & Price Delta Analysis
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Bounded bisection search calculating exact price reduction required to achieve target rank #1.
          </p>
        </div>
      </div>

      {/* Target Selector */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="flex-1">
          <label htmlFor="breakeven-candidate-select" className="text-xs font-semibold text-muted-foreground mb-1 block">
            Select Candidate Supplier to Test for Rank #1
          </label>
          <select
            id="breakeven-candidate-select"
            value={selectedSupplierId}
            onChange={(e) => setSelectedSupplierId(e.target.value)}
            className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
          >
            {scores.map((s) => (
              <option key={s.quotation_id} value={s.quotation_id}>
                {s.supplier_name} {s.rank ? `(Rank #${s.rank}, Score: ${s.composite_score.toFixed(1)})` : "(Ineligible)"}
              </option>
            ))}
          </select>
        </div>

        <div className="self-end">
          <button
            onClick={handleCompute}
            disabled={isLoading || !selectedSupplierId}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md shadow-primary/20 disabled:opacity-50"
          >
            <Cpu className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            {isLoading ? "Running Bisection..." : "Compute Breakeven"}
          </button>
        </div>
      </div>

      {/* Results Display */}
      {breakevenResult && (
        <div className="space-y-4 pt-2">
          {/* Status Badge */}
          <div
            className={`p-4 rounded-xl border flex items-start gap-3 ${
              breakevenResult.is_feasible
                ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-200"
                : "bg-amber-950/20 border-amber-800/40 text-amber-200"
            }`}
          >
            {breakevenResult.is_feasible ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            )}
            <div className="space-y-1">
              <div className="font-semibold text-sm">
                {breakevenResult.is_feasible
                  ? `Feasible Breakeven Target Identified`
                  : `Breakeven Infeasible Under Current Constraints`}
              </div>
              <p className="text-xs text-muted-foreground">{breakevenResult.explanation}</p>
              {breakevenResult.bisection_iterations != null && (
                <div className="text-[11px] font-mono text-muted-foreground">
                  Converged in {breakevenResult.bisection_iterations} bisection numerical iterations.
                </div>
              )}
            </div>
          </div>

          {/* Metric Cards Grid */}
          {breakevenResult.is_feasible && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div className="glass-card rounded-xl p-3.5 space-y-1 border border-border/70">
                <div className="text-[10px] uppercase font-bold text-muted-foreground">Current Price</div>
                <div className="text-base font-bold text-foreground">
                  ${breakevenResult.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div className="glass-card rounded-xl p-3.5 space-y-1 border border-border/70">
                <div className="text-[10px] uppercase font-bold text-muted-foreground">Target Breakeven Price</div>
                <div className="text-base font-bold text-emerald-400">
                  ${breakevenResult.required_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div className="glass-card rounded-xl p-3.5 space-y-1 border border-border/70">
                <div className="text-[10px] uppercase font-bold text-muted-foreground">Price Delta</div>
                <div className="text-base font-bold text-blue-400">
                  -${breakevenResult.price_delta?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div className="glass-card rounded-xl p-3.5 space-y-1 border border-border/70">
                <div className="text-[10px] uppercase font-bold text-muted-foreground">Required Price Reduction</div>
                <div className="text-base font-bold text-amber-400 flex items-center gap-1">
                  <ArrowDownRight className="h-4 w-4" />
                  {breakevenResult.percentage_reduction_needed?.toFixed(2)}%
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
