import React from "react";
import { History, X, Clock, User, ArrowRight } from "lucide-react";
import { AuditLogEntry } from "../../api/quotation";

interface AuditHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  logs: AuditLogEntry[];
}

export const AuditHistoryDrawer: React.FC<AuditHistoryDrawerProps> = ({
  isOpen,
  onClose,
  logs,
}) => {
  if (!isOpen) return null;

  const formatEventName = (eventType: string) => {
    switch (eventType) {
      case "LINE_ITEM_CORRECTED":
        return "Line Item Corrected";
      case "LINE_ITEM_ADDED":
        return "Line Item Added";
      case "LINE_ITEM_EXCLUDED":
        return "Line Item Excluded";
      case "LINE_ITEM_RESTORED":
        return "Line Item Restored";
      case "QUOTATION_FIELD_CORRECTED":
        return "Header Field Corrected";
      case "QUOTATION_EXTRACTION_APPROVED":
        return "Extraction Approved";
      case "QUOTATION_EXTRACTION_REJECTED":
        return "Extraction Rejected";
      default:
        return eventType;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-drawer-title"
    >
      <div className="w-full max-w-md h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-slideLeft">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <History className="w-4 h-4 text-blue-400" />
            <h2 id="audit-drawer-title">Immutable Audit Trail ({logs.length})</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close audit drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Audit List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {logs.length === 0 ? (
            <div className="text-center text-xs text-slate-500 py-12">
              No audit events recorded for this quotation yet.
            </div>
          ) : (
            logs.map((log) => {
              const payload = log.payload || {};
              const hasDiff = payload.previous_values && payload.new_values;

              return (
                <div
                  key={log.id}
                  className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-blue-300">
                      {formatEventName(log.event_type)}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                      <Clock className="w-3 h-3" />
                      {new Date(log.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] text-slate-400">
                    <User className="w-3 h-3 text-slate-500" />
                    <span>Actor: {log.actor_id} ({log.actor_type})</span>
                  </div>

                  {/* Value diff display */}
                  {hasDiff && (
                    <div className="p-2 bg-slate-900 rounded border border-slate-800/80 space-y-1 text-[11px] font-mono">
                      {Object.keys(payload.new_values).map((key) => (
                        <div key={key} className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-slate-400">{key}:</span>
                          <span className="text-rose-400 line-through">
                            {String(payload.previous_values[key] ?? "none")}
                          </span>
                          <ArrowRight className="w-2.5 h-2.5 text-slate-500" />
                          <span className="text-emerald-400 font-bold">
                            {String(payload.new_values[key])}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {payload.reason && (
                    <div className="text-[11px] text-amber-300/90 italic">
                      Reason: "{payload.reason}"
                    </div>
                  )}

                  {payload.rejection_reason && (
                    <div className="text-[11px] text-rose-300/90 italic">
                      Rejection Reason: "{payload.rejection_reason}"
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
