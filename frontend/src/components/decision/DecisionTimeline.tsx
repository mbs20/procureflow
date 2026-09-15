import React, { useState } from "react";
import {
  AwardDecisionResponse,
  revokeAward,
} from "../../api/decision";
import {
  History,
  CheckCircle2,
  FilePlus,
  RotateCcw,
  User,
  Clock,
  Key,
  AlertCircle,
  X,
} from "lucide-react";

interface DecisionTimelineProps {
  award: AwardDecisionResponse;
  rfqId: string;
  onAwardRevoked?: (updatedAward: AwardDecisionResponse) => void;
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({
  award,
  rfqId,
  onAwardRevoked,
}) => {
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [revocationReason, setRevocationReason] = useState("");
  const [submittingRevoke, setSubmittingRevoke] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  const handleRevoke = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revocationReason.trim()) return;
    setSubmittingRevoke(true);
    setRevokeError(null);

    try {
      const updated = await revokeAward(rfqId, award.id, {
        revocation_reason: revocationReason.trim(),
      });
      setShowRevokeModal(false);
      setRevocationReason("");
      if (onAwardRevoked) onAwardRevoked(updated);
    } catch (err: any) {
      setRevokeError(err.message || "Failed to revoke award");
    } finally {
      setSubmittingRevoke(false);
    }
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case "draft_created":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            <FilePlus className="w-3 h-3" /> Draft Created
          </span>
        );
      case "confirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> Human Confirmed
          </span>
        );
      case "revoked":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <RotateCcw className="w-3 h-3" /> Revoked
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-300">
            {type}
          </span>
        );
    }
  };

  return (
    <div className="glass-card rounded-xl border border-border/80 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <History className="w-5 h-5 text-primary" />
            <h3 className="text-base font-bold text-white">
              Award Lifecycle Event Stream ({award.events.length} events)
            </h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Append-only event log capturing all state transitions and human confirmations.
          </p>
        </div>

        {award.current_status === "confirmed" && (
          <button
            onClick={() => setShowRevokeModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-semibold transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Revoke Confirmed Award
          </button>
        )}
      </div>

      {/* Events Timeline */}
      <div className="space-y-4 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-border/60 before:z-0">
        {award.events.map((evt) => (
          <div key={evt.id} className="relative z-10 flex items-start gap-4">
            <div className="w-7 h-7 rounded-full bg-slate-900 border-2 border-primary flex items-center justify-center shrink-0 text-primary font-mono text-xs font-bold shadow-md">
              {evt.event_number}
            </div>

            <div className="flex-1 bg-secondary/30 border border-border/60 rounded-xl p-4 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getEventBadge(evt.event_type)}
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <User className="w-3 h-3" />
                    <strong>{evt.actor_principal}</strong>
                  </span>
                </div>
                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(evt.created_at).toLocaleString()}
                </span>
              </div>

              {/* Event specific summaries */}
              {evt.event_type === "draft_created" && (
                <div className="text-xs text-foreground/90 space-y-1">
                  <div>
                    <span className="text-muted-foreground">Awarded Supplier: </span>
                    <strong className="text-white">{award.awarded_supplier_name}</strong>{" "}
                    (Rank #{award.awarded_supplier_rank ?? "—"})
                  </div>
                  {evt.event_payload?.justification && (
                    <p className="bg-secondary/40 p-2 rounded text-muted-foreground italic">
                      "{evt.event_payload.justification}"
                    </p>
                  )}
                  {evt.event_payload?.non_rank1_rationale && (
                    <div className="p-2 rounded bg-amber-950/30 border border-amber-500/30 text-amber-200">
                      <strong>Non-Rank #1 Rationale:</strong> {evt.event_payload.non_rank1_rationale}
                    </div>
                  )}
                </div>
              )}

              {evt.event_type === "confirmed" && (
                <div className="text-xs text-foreground/90 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                    <CheckCircle2 className="w-4 h-4" />
                    Confirmed by authorized buyer. RFQ transitioned to DECIDED status.
                  </div>
                  {award.provenance_hash && (
                    <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground bg-slate-950 p-2 rounded border border-border/40">
                      <Key className="w-3.5 h-3.5 text-primary" />
                      <span>Provenance Hash: {award.provenance_hash}</span>
                    </div>
                  )}
                </div>
              )}

              {evt.event_type === "revoked" && (
                <div className="text-xs text-foreground/90 space-y-1.5">
                  <div className="text-rose-400 font-semibold flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5" />
                    Award revoked. RFQ reverted to EVALUATING status.
                  </div>
                  {evt.event_payload?.revocation_reason && (
                    <p className="bg-rose-950/30 border border-rose-500/30 p-2 rounded text-rose-200">
                      <strong>Revocation Reason:</strong> "{evt.event_payload.revocation_reason}"
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Revocation Modal */}
      {showRevokeModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-md">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 space-y-4 border border-rose-500/40 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2 text-rose-400 font-bold">
                <RotateCcw className="w-5 h-5" />
                <h3>Revoke Confirmed Procurement Award</h3>
              </div>
              <button onClick={() => setShowRevokeModal(false)} className="text-muted-foreground hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {revokeError && (
              <div className="p-3 rounded bg-rose-950/50 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{revokeError}</span>
              </div>
            )}

            <form onSubmit={handleRevoke} className="space-y-4 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                Revoking an award invalidates the supplier decision and returns the RFQ to the <strong className="text-white">EVALUATING</strong> state. This action is permanently appended to the audit log.
              </p>

              <div className="space-y-1.5">
                <label className="font-semibold text-foreground block">
                  Mandatory Revocation Reason:
                </label>
                <textarea
                  rows={3}
                  value={revocationReason}
                  onChange={(e) => setRevocationReason(e.target.value)}
                  placeholder="e.g. Supplier failed final credit check or commercial terms renegotiation required..."
                  className="w-full bg-slate-900 border border-border rounded-lg p-2.5 text-white text-xs focus:ring-1 focus:ring-rose-400 focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setShowRevokeModal(false)}
                  className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingRevoke || !revocationReason.trim()}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition disabled:opacity-50"
                >
                  {submittingRevoke ? "Revoking..." : "Confirm Revocation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
