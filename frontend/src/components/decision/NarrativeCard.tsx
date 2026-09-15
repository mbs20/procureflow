import React, { useState } from "react";
import {
  NarrativeGenerationResponse,
  NarrativeClaim,
  createNarrativeRevision,
} from "../../api/decision";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Clock,
  Edit3,
  ShieldCheck,
  History,
  Send,
  X,
  FileText,
  AlertCircle,
} from "lucide-react";

interface NarrativeCardProps {
  narrative: NarrativeGenerationResponse;
  rfqId: string;
  onRevisionSaved?: () => void;
}

export const NarrativeCard: React.FC<NarrativeCardProps> = ({
  narrative,
  rfqId,
  onRevisionSaved,
}) => {
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [showClaimDetails, setShowClaimDetails] = useState<NarrativeClaim | null>(null);
  const [revisedText, setRevisedText] = useState("");
  const [revisionRationale, setRevisionRationale] = useState("");
  const [submittingRevision, setSubmittingRevision] = useState(false);
  const [revisionError, setRevisionError] = useState<string | null>(null);

  const sections = narrative.raw_structured_output;
  const grounding = narrative.grounding_validation_result;

  const handleCreateRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revisedText.trim()) return;
    setSubmittingRevision(true);
    setRevisionError(null);
    try {
      await createNarrativeRevision(
        rfqId,
        narrative.id,
        revisedText.trim(),
        revisionRationale.trim() || undefined
      );
      setShowRevisionModal(false);
      setRevisedText("");
      setRevisionRationale("");
      if (onRevisionSaved) onRevisionSaved();
    } catch (err: any) {
      setRevisionError(err.message || "Failed to submit revision");
    } finally {
      setSubmittingRevision(false);
    }
  };

  const getOriginBadge = () => {
    switch (narrative.current_origin) {
      case "ai_generated_human_revised":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <Edit3 className="w-3.5 h-3.5" /> AI + Human Revised
          </span>
        );
      case "human_authored":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Human Authored
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-300 border border-sky-500/30">
            <Sparkles className="w-3.5 h-3.5" /> AI Generated
          </span>
        );
    }
  };

  return (
    <div className="glass-card rounded-xl border border-border/80 overflow-hidden flex flex-col space-y-6 p-6">
      {/* Superseded Warning Banner */}
      {narrative.is_superseded && (
        <div className="bg-amber-950/40 border border-amber-500/40 rounded-lg p-3.5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-200">
            <span className="font-semibold block text-sm">Superseded Narrative</span>
            {narrative.superseded_reason ||
              "A newer scoring run or evaluation has superseded this narrative. It is preserved for compliance auditing."}
          </div>
        </div>
      )}

      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-white capitalize">
              {narrative.narrative_type.replace(/_/g, " ")} #{narrative.generation_number}
            </h3>
            {getOriginBadge()}
          </div>
          <p className="text-xs text-muted-foreground flex items-center gap-2">
            <span>Provider: <strong className="text-foreground">{narrative.provider}</strong> ({narrative.model_identifier})</span>
            <span>•</span>
            <Clock className="w-3 h-3 inline" />
            <span>{new Date(narrative.generated_at).toLocaleString()}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Grounding Status Overview */}
          <div className="flex items-center gap-1.5 bg-secondary/50 px-3 py-1.5 rounded-lg text-xs border border-border/40">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-300 font-medium">{grounding.verified} verified</span>
            {grounding.unsupported > 0 && (
              <span className="text-rose-400 font-medium ml-1.5">
                • {grounding.unsupported} unsupported
              </span>
            )}
          </div>

          <button
            onClick={() => {
              setRevisedText(
                narrative.revisions.length > 0
                  ? narrative.revisions[narrative.revisions.length - 1].revised_text
                  : sections.executive_summary
              );
              setShowRevisionModal(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-foreground border border-primary/40 text-xs font-semibold transition"
          >
            <Edit3 className="w-3.5 h-3.5" />
            Revise Narrative
          </button>
        </div>
      </div>

      {/* Active Revision Banner if revisions exist */}
      {narrative.revisions.length > 0 && (
        <div className="bg-slate-900/90 border border-primary/30 rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-primary font-semibold">
            <span className="flex items-center gap-1.5">
              <History className="w-4 h-4" /> Latest Human Revision (#{narrative.revisions[narrative.revisions.length - 1].revision_number})
            </span>
            <span className="text-muted-foreground">
              by {narrative.revisions[narrative.revisions.length - 1].revised_by}
            </span>
          </div>
          <p className="text-sm text-foreground whitespace-pre-wrap">
            {narrative.revisions[narrative.revisions.length - 1].revised_text}
          </p>
          {narrative.revisions[narrative.revisions.length - 1].revision_rationale && (
            <p className="text-xs text-muted-foreground italic">
              Rationale: "{narrative.revisions[narrative.revisions.length - 1].revision_rationale}"
            </p>
          )}
        </div>
      )}

      {/* Executive Summary */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Executive Summary</h4>
        <p className="text-sm text-foreground/90 leading-relaxed bg-secondary/30 p-3.5 rounded-lg border border-border/40">
          {sections.executive_summary}
        </p>
      </div>

      {/* Ranking Explanation */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Ranking Explanation</h4>
        <p className="text-sm text-foreground/80 leading-relaxed bg-secondary/20 p-3.5 rounded-lg border border-border/40">
          {sections.ranking_explanation}
        </p>
      </div>

      {/* Per Supplier Analysis */}
      {sections.per_supplier_analysis && sections.per_supplier_analysis.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Supplier Evaluation Breakdown</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sections.per_supplier_analysis.map((sa) => (
              <div
                key={sa.supplier_id}
                className="bg-secondary/40 border border-border/60 rounded-lg p-3.5 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center border border-primary/30">
                      #{sa.rank ?? "?"}
                    </span>
                    <strong className="text-sm text-white">{sa.supplier_name}</strong>
                  </div>
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                    Score: {sa.total_score}
                  </span>
                </div>

                {sa.strengths.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold text-emerald-300 block mb-1">Strengths</span>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      {sa.strengths.map((st, idx) => (
                        <li key={idx}>{st}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {sa.weaknesses.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold text-rose-300 block mb-1">Trade-offs / Weaknesses</span>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      {sa.weaknesses.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trade-offs & Considerations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.trade_offs && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Comparative Trade-offs</h4>
            <div className="text-xs text-foreground/80 bg-secondary/20 p-3 rounded-lg border border-border/40 leading-relaxed">
              {sections.trade_offs}
            </div>
          </div>
        )}
        {sections.decision_considerations && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Decision Considerations</h4>
            <div className="text-xs text-foreground/80 bg-secondary/20 p-3 rounded-lg border border-border/40 leading-relaxed">
              {sections.decision_considerations}
            </div>
          </div>
        )}
      </div>

      {/* Grounded Claims List with Fact References */}
      {narrative.claims && narrative.claims.length > 0 && (
        <div className="space-y-2 border-t border-border/60 pt-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Evidence-Grounded Claims ({narrative.claims.length})
            </h4>
            <span className="text-[11px] text-muted-foreground">
              Click claim to view deterministic context binding
            </span>
          </div>

          <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
            {narrative.claims.map((c) => (
              <div
                key={c.id}
                onClick={() => setShowClaimDetails(c)}
                className="cursor-pointer flex items-center justify-between gap-3 p-2 rounded bg-secondary/20 hover:bg-secondary/40 border border-border/30 text-xs transition"
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  {c.grounding_status === "verified" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : c.grounding_status === "unsupported" ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  ) : (
                    <HelpCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="truncate text-foreground/90">{c.text}</span>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground shrink-0 uppercase">
                  {c.claim_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claim Detail Modal */}
      {showClaimDetails && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-xl p-6 space-y-4 border border-border shadow-2xl">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                <h3 className="font-bold text-sm text-white">
                  Claim Fact Reference #{showClaimDetails.claim_index}
                </h3>
              </div>
              <button
                onClick={() => setShowClaimDetails(null)}
                className="text-muted-foreground hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-muted-foreground block mb-1">Claim Text:</span>
                <p className="p-2.5 rounded bg-secondary/40 text-foreground">
                  {showClaimDetails.text}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-muted-foreground block">Type:</span>
                  <span className="font-mono text-white">{showClaimDetails.claim_type}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Grounding Status:</span>
                  <span
                    className={`font-semibold ${
                      showClaimDetails.grounding_status === "verified"
                        ? "text-emerald-400"
                        : showClaimDetails.grounding_status === "unsupported"
                        ? "text-rose-400"
                        : "text-amber-400"
                    }`}
                  >
                    {showClaimDetails.grounding_status}
                  </span>
                </div>
              </div>

              {showClaimDetails.fact_references && (
                <div>
                  <span className="text-muted-foreground block mb-1">
                    Deterministic Fact References:
                  </span>
                  <pre className="p-2.5 rounded bg-slate-950 font-mono text-[11px] text-emerald-300 overflow-x-auto border border-border/40">
                    {JSON.stringify(showClaimDetails.fact_references, null, 2)}
                  </pre>
                </div>
              )}

              {showClaimDetails.grounding_notes && (
                <div className="p-2.5 rounded bg-rose-950/40 border border-rose-500/30 text-rose-300">
                  <span className="font-semibold block">Grounding Note:</span>
                  {showClaimDetails.grounding_notes}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowClaimDetails(null)}
                className="px-4 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Human Revision Modal */}
      {showRevisionModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-xl rounded-xl p-6 space-y-4 border border-border shadow-2xl">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-primary" />
                <h3 className="font-bold text-sm text-white">Create Human Revision</h3>
              </div>
              <button
                onClick={() => setShowRevisionModal(false)}
                className="text-muted-foreground hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {revisionError && (
              <div className="p-3 rounded bg-rose-950/50 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{revisionError}</span>
              </div>
            )}

            <form onSubmit={handleCreateRevision} className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-muted-foreground font-medium block">
                  Revised Narrative Text (Replaces active presentation):
                </label>
                <textarea
                  rows={5}
                  value={revisedText}
                  onChange={(e) => setRevisedText(e.target.value)}
                  className="w-full bg-slate-900 border border-border rounded-lg p-3 text-white text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  placeholder="Enter corrected narrative memo..."
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-muted-foreground font-medium block">
                  Revision Rationale (Mandatory audit explanation):
                </label>
                <input
                  type="text"
                  value={revisionRationale}
                  onChange={(e) => setRevisionRationale(e.target.value)}
                  className="w-full bg-slate-900 border border-border rounded-lg p-2.5 text-white text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  placeholder="e.g. Corrected commercial warranty terms clarification"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setShowRevisionModal(false)}
                  className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingRevision || !revisedText.trim()}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold transition disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submittingRevision ? "Saving..." : "Save Revision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
