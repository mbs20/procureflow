import React, { useState } from "react";
import { useTranslation, Trans } from "react-i18next";
import { CheckCircle2, XCircle, AlertTriangle, X } from "lucide-react";
import { ExtractionValidationStatus } from "../../api/quotation";
import { translateBackendError } from "../../lib/errorMessageMap";

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
  const { t } = useTranslation();

  const [rejectionReason, setRejectionReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

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
      setError(translateBackendError(err, t));
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectionReason.trim()) {
      setError(t('review.decisionProvideReasonError'));
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await onConfirmReject(rejectionReason.trim());
      onClose();
    } catch (err: any) {
      setError(translateBackendError(err, t));
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
              {isApprove ? t('review.decisionApproveQuality') : t('review.decisionReject')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label={t('common.close')}
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
                <Trans
                  i18nKey="review.decisionApproveText"
                  values={{ supplier: supplierName }}
                  components={{ 1: <strong className="text-white" /> }}
                />
              </p>
              <div className="p-3 bg-blue-950/30 border border-blue-800/40 rounded-lg text-[11px] text-blue-200/90 leading-relaxed">
                <strong>{t('review.decisionScopeTitle')} </strong>
                {t('review.decisionScopeBody')}
              </div>

              {hasCriticalIssues && (
                <div className="p-3.5 bg-rose-950/50 border border-rose-700 rounded-lg text-rose-300 space-y-2">
                  <div className="flex items-center gap-1.5 font-bold text-rose-200">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    <span>{t('review.decisionCannotApprove')}</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-[11px]">
                    {validationStatus?.critical_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                  <p className="text-[10px] text-rose-400 italic">
                    {t('review.decisionValidationRulesNote')}
                  </p>
                </div>
              )}

              {!hasCriticalIssues && validationStatus && validationStatus.warnings.length > 0 && (
                <div className="p-3 bg-amber-950/30 border border-amber-800/50 rounded-lg text-amber-200 text-[11px]">
                  <span>
                    {t('review.decisionAckWarnings', { count: validationStatus.warnings.length })}
                  </span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={submitting || hasCriticalIssues}
                  className="px-4 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-lg shadow-emerald-700/20 transition"
                >
                  {submitting ? t('review.decisionApproving') : t('review.decisionConfirmApprove')}
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleReject} className="space-y-4">
              <p className="leading-relaxed">
                <Trans
                  i18nKey="review.decisionRejectText"
                  values={{ supplier: supplierName }}
                  components={{
                    1: <strong className="text-white" />,
                    3: <span className="font-mono text-rose-400 font-semibold" />
                  }}
                />
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {t('review.decisionReasonLabel')}
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder={t('review.decisionReasonPlaceholder')}
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
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={submitting || !rejectionReason.trim()}
                  className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-lg shadow-rose-500/20 transition"
                >
                  {submitting ? t('review.decisionRejecting') : t('review.decisionConfirmReject')}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
