import React from "react";
import { AlertTriangle, XCircle, CheckCircle2 } from "lucide-react";
import { ExtractionValidationStatus } from "../../api/quotation";

interface ValidationAlertCenterProps {
  validationStatus: ExtractionValidationStatus | null;
  onAcknowledgeWarning?: (warningKey: string) => void;
  discrepanciesCount: number;
}

export const ValidationAlertCenter: React.FC<ValidationAlertCenterProps> = ({
  validationStatus,
  onAcknowledgeWarning,
  discrepanciesCount,
}) => {
  if (!validationStatus) return null;

  const hasCritical = validationStatus.critical_issues.length > 0;
  const hasWarnings = validationStatus.warnings.length > 0;

  if (!hasCritical && !hasWarnings && discrepanciesCount === 0) {
    return (
      <div className="flex items-center gap-2 px-3.5 py-2.5 bg-emerald-950/30 border border-emerald-800/40 rounded-lg text-xs text-emerald-300">
        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        <span>Extraction passed all structural and arithmetic validation checks. Eligible for approval.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Critical Blockers Banner */}
      {hasCritical && (
        <div
          role="alert"
          aria-live="assertive"
          className="flex flex-col gap-2 p-3.5 bg-rose-950/40 border border-rose-700/60 rounded-lg text-xs text-rose-200"
        >
          <div className="flex items-center gap-2 font-semibold text-rose-300">
            <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>Critical Issues (Preventing Extraction Approval)</span>
          </div>
          <ul className="list-disc list-inside space-y-1 pl-1 text-rose-300/90 text-[11px]">
            {validationStatus.critical_issues.map((issue, idx) => (
              <li key={idx} className="leading-relaxed">
                {issue}
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-rose-400/80 italic mt-0.5">
            Resolve all negative/zero amounts or acknowledge mathematical discrepancies to enable approval.
          </p>
        </div>
      )}

      {/* Ordinary & Arithmetic Warnings */}
      {hasWarnings && (
        <div
          role="status"
          className="flex flex-col gap-2 p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg text-xs text-amber-200"
        >
          <div className="flex items-center justify-between font-medium text-amber-300 text-[11px]">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>Review Alerts & Advisory Warnings ({validationStatus.warnings.length})</span>
            </div>
          </div>
          <div className="space-y-1.5 text-[11px]">
            {validationStatus.warnings.map((warn, idx) => (
              <div
                key={idx}
                className="flex items-start justify-between gap-2 p-1.5 rounded bg-amber-900/20 border border-amber-800/30"
              >
                <span className="text-amber-300/90">{warn}</span>
                {onAcknowledgeWarning && (
                  <button
                    onClick={() => onAcknowledgeWarning(warn)}
                    className="text-[10px] px-2 py-0.5 rounded bg-amber-800/40 hover:bg-amber-700/50 text-amber-200 transition border border-amber-600/40 flex-shrink-0"
                  >
                    Acknowledge
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
