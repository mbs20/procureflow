import React, { useState } from "react";
import {
  AwardDecisionCreate,
  createDraftAward,
  confirmAward,
  AwardDecisionResponse,
} from "../../api/decision";
import {
  ShieldAlert,
  Award,
  CheckSquare,
  Square,
  AlertTriangle,
  X,
  Lock,
} from "lucide-react";

interface SupplierOption {
  quotation_id: string;
  supplier_name: string;
  rank?: number | null;
  total_score: string | number;
  eligibility_status: string;
}

interface AwardConfirmationModalProps {
  rfqId: string;
  scoringRunId: string;
  scoringRunProvenanceHash?: string | null;
  suppliers: SupplierOption[];
  onClose: () => void;
  onAwardConfirmed: (award: AwardDecisionResponse) => void;
}

export const AwardConfirmationModal: React.FC<AwardConfirmationModalProps> = ({
  rfqId,
  scoringRunId,
  scoringRunProvenanceHash,
  suppliers,
  onClose,
  onAwardConfirmed,
}) => {
  const eligibleSuppliers = suppliers.filter((s) => s.eligibility_status === "eligible");
  const rank1Supplier = eligibleSuppliers.find((s) => s.rank === 1);

  // Selector initially has NO selected supplier (human must actively choose)
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("");
  const [awardJustification, setAwardJustification] = useState("");
  const [nonRank1Rationale, setNonRank1Rationale] = useState("");
  const [ackScores, setAckScores] = useState(false);
  const [ackTerms, setAckTerms] = useState(false);
  const [ackBinding, setAckBinding] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSupplier = suppliers.find((s) => s.quotation_id === selectedSupplierId);
  const isNonRank1 = Boolean(selectedSupplier && selectedSupplier.rank !== 1);

  const canSubmit =
    Boolean(selectedSupplierId) &&
    awardJustification.trim().length > 0 &&
    (!isNonRank1 || nonRank1Rationale.trim().length > 0) &&
    ackScores &&
    ackTerms &&
    ackBinding &&
    !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);

    try {
      // 1. Create draft award
      const payload: AwardDecisionCreate = {
        scoring_run_id: scoringRunId,
        awarded_supplier_id: selectedSupplierId,
        award_justification: awardJustification.trim(),
        non_rank1_rationale: isNonRank1 ? nonRank1Rationale.trim() : undefined,
      };

      const draft = await createDraftAward(rfqId, payload);

      // 2. Human confirms award (The authoritative final step)
      const confirmed = await confirmAward(rfqId, draft.id, {
        final_justification: awardJustification.trim(),
      });

      onAwardConfirmed(confirmed);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to execute award decision");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-md">
      <div className="glass-panel w-full max-w-2xl rounded-2xl p-6 space-y-5 border border-border shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Human Procurement Award Decision</h2>
              <p className="text-xs text-muted-foreground">
                Authoritative human confirmation required. This action cannot be undone automatically.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Rank #1 Contextual Scoring Information (Not pre-selected) */}
          {rank1Supplier && (
            <div className="p-3 rounded-xl bg-secondary/40 border border-border/60 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Deterministic Top-Scored Supplier (Context Only):</span>
              <span className="font-semibold text-primary">
                {rank1Supplier.supplier_name} (Rank #1 &bull; Score: {String(rank1Supplier.total_score)})
              </span>
            </div>
          )}

          {/* Supplier Selection */}
          <div className="space-y-1.5">
            <label className="font-semibold text-foreground block">
              Select Award Recipient Supplier:
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {eligibleSuppliers.map((s) => {
                const isSelected = s.quotation_id === selectedSupplierId;
                return (
                  <div
                    key={s.quotation_id}
                    onClick={() => setSelectedSupplierId(s.quotation_id)}
                    className={`cursor-pointer p-3 rounded-xl border transition ${
                      isSelected
                        ? "bg-primary/20 border-primary shadow-lg shadow-primary/10"
                        : "bg-secondary/30 border-border/60 hover:bg-secondary/60"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-white">{s.supplier_name}</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">
                        Rank #{s.rank}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground mt-1 text-[11px]">
                      <span>Total Score: {String(s.total_score)}</span>
                      <span className="text-emerald-400 font-semibold">Eligible</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Non-Rank 1 Warning & Mandatory Rationale */}
          {isNonRank1 && (
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-2">
              <div className="flex items-center gap-2 text-amber-300 font-semibold">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>Non-Rank #1 Selection Governance Rule</span>
              </div>
              <p className="text-amber-200/90 text-[11px] leading-relaxed">
                Selected supplier is ranked #{selectedSupplier?.rank}, not #1. Public sector and enterprise compliance requires an explicit, audited rationale explaining why the higher-ranked vendor was bypassed.
              </p>
              <textarea
                rows={2}
                value={nonRank1Rationale}
                onChange={(e) => setNonRank1Rationale(e.target.value)}
                placeholder="Mandatory rationale for selecting non-Rank #1 supplier (e.g. historical supplier risk, warranty extension)..."
                className="w-full bg-slate-950 border border-amber-500/40 rounded-lg p-2.5 text-white text-xs focus:ring-1 focus:ring-amber-400 focus:outline-none"
                required
              />
            </div>
          )}

          {/* Primary Award Justification */}
          <div className="space-y-1.5">
            <label className="font-semibold text-foreground block">
              Official Award Justification (Recorded permanently in audit trail):
            </label>
            <textarea
              rows={3}
              value={awardJustification}
              onChange={(e) => setAwardJustification(e.target.value)}
              placeholder="Provide commercial and technical justification for this procurement award..."
              className="w-full bg-slate-900 border border-border rounded-lg p-2.5 text-white text-xs focus:ring-1 focus:ring-primary focus:outline-none"
              required
            />
          </div>

          {/* Provenance Context */}
          {scoringRunProvenanceHash && (
            <div className="p-2.5 rounded-lg bg-secondary/30 border border-border/40 text-[11px] text-muted-foreground flex items-center justify-between">
              <span>Scoring Run Provenance SHA-256:</span>
              <span className="font-mono text-foreground font-semibold">
                {scoringRunProvenanceHash.slice(0, 16)}...
              </span>
            </div>
          )}

          {/* Human Checkboxes */}
          <div className="space-y-2 pt-2 border-t border-border/60">
            <div
              onClick={() => setAckScores(!ackScores)}
              className="cursor-pointer flex items-center gap-2.5 select-none text-foreground/90 hover:text-white"
            >
              {ackScores ? (
                <CheckSquare className="w-4 h-4 text-primary shrink-0" />
              ) : (
                <Square className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
              <span>I have reviewed the deterministic scoring calculations and verified criterion weights.</span>
            </div>

            <div
              onClick={() => setAckTerms(!ackTerms)}
              className="cursor-pointer flex items-center gap-2.5 select-none text-foreground/90 hover:text-white"
            >
              {ackTerms ? (
                <CheckSquare className="w-4 h-4 text-primary shrink-0" />
              ) : (
                <Square className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
              <span>I confirm that technical compliance and commercial quotation terms have been verified.</span>
            </div>

            <div
              onClick={() => setAckBinding(!ackBinding)}
              className="cursor-pointer flex items-center gap-2.5 select-none text-foreground/90 hover:text-white"
            >
              {ackBinding ? (
                <CheckSquare className="w-4 h-4 text-primary shrink-0" />
              ) : (
                <Square className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
              <span className="text-amber-300">
                I understand this human action transitions the RFQ to DECIDED and locks the award decision.
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-3 border-t border-border/60">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-xs font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-bold text-xs shadow-lg shadow-amber-500/20 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Lock className="w-3.5 h-3.5" />
              {submitting ? "Signing & Confirming..." : "Confirm & Award RFQ"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
