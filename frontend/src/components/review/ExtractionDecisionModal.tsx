import React, { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, X } from "lucide-react";
import { ExtractionValidationStatus } from "../../api/quotation";

interface ExtractionDecisionModalProps {
  isOpen: boolean;
  type: "approve" | "reject";
  supplierName: string;
  validationStatus: ExtractionValidationStatus | null;
  onClose: () => void;
  onConfirmApprove: (acknowledgedWarnings: string[]) => Promise<void>;
  onConfirmReject: (reason: string) => Promise<void>;
}

export const ExtractionDecisionModal: React.FC<ExtractionDecisionModalProps> = ({
  isOpen,
  type,
  supplierName,
  validationStatus,
  onClose,
  onConfirmApprove,
  onConfirmReject,
}) => {
  if (!isOpen) return null;

  const [rejectionReason, setRejectionReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isApprove = type === "approve";
  const hasCriticalIssues = validationStatus ? !validationStatus.can_approve : false;

  const handleApprove = async () => {
    try {
      setSubmitting(true);
      setError(null);
      // Pass any warnings as acknowledged
      const warningsToAck = validationStatus?.warnings || [];
      await onConfirmApprove(warningsToAck);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to approve extraction");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectionReason.trim()) {
      setError("Please provide a reason for rejecting this extraction.");
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await onConfirmReject(rejectionReason.trim());
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to reject extraction");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="decision-modal-title"
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-fadeIn">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            {isApprove ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400" />
            )}
            <h2 id="decision-modal-title" className="text-base font-bold text-white">
              {isApprove ? "Approve Extraction Quality" : "Reject Extraction"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-4 text-xs text-slate-300">
          {error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800 text-rose-300 rounded-lg">
              {error}
            </div>
          )}

          {isApprove ? (
            <div className="space-y-3">
              <p className="leading-relaxed">
                You are approving the structured extraction for supplier{" "}
                <strong className="text-white">{supplierName}</strong>.
              </p>
              <div className="p-3 bg-blue-950/30 border border-blue-800/40 rounded-lg text-[11px] text-blue-200/90 leading-relaxed">
                <strong>Review Scope:</strong> This action verifies extraction accuracy for downstream RFQ comparison. It does not commercially award or accept the supplier's quotation bid.
              </div>

              {hasCriticalIssues && (
                <div className="p-3.5 bg-rose-950/50 border border-rose-700 rounded-lg text-rose-300 space-y-2">
                  <div className="flex items-center gap-1.5 font-bold text-rose-200">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    <span>Cannot Approve: Critical Unresolved Issues</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-[11px]">
                    {validationStatus?.critical_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                  <p className="text-[10px] text-rose-400 italic">
                    Server-side validation rules require correcting or resolving these issues before approval.
                  </p>
                </div>
              )}

              {!hasCriticalIssues && validationStatus && validationStatus.warnings.length > 0 && (
                <div className="p-3 bg-amber-950/30 border border-amber-800/50 rounded-lg text-amber-200 text-[11px]">
                  <span>
                    Approving will automatically acknowledge {validationStatus.warnings.length} advisory warning(s).
                  </span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={submitting || hasCriticalIssues}
                  className="px-4 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-lg shadow-emerald-700/20 transition"
                >
                  {submitting ? "Approving..." : "Confirm & Approve Extraction"}
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleReject} className="space-y-4">
              <p className="leading-relaxed">
                Rejecting the extraction for <strong className="text-white">{supplierName}</strong> will transition status to <span className="font-mono text-rose-400 font-semibold">rejected</span>.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Rejection Reason *
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Explain why this quotation extraction is rejected (e.g. illegible PDF, invalid quotation structure, non-responsive quotation)..."
                  required
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-rose-500 transition"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !rejectionReason.trim()}
                  className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-lg shadow-rose-500/20 transition"
                >
                  {submitting ? "Rejecting..." : "Confirm & Reject Extraction"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
