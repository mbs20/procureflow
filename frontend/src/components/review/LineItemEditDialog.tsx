import React, { useState, useEffect } from "react";
import { X, Save, AlertTriangle, Calculator } from "lucide-react";
import { ExtractedLineItem } from "../../api/quotation";
import { RFQLineItem } from "../../api/rfq";

interface LineItemEditDialogProps {
  item: ExtractedLineItem | null;
  rfqLineItems: RFQLineItem[];
  isOpen: boolean;
  onClose: () => void;
  onSave: (itemId: string, patch: Partial<ExtractedLineItem>, reason?: string) => Promise<void>;
}

export const LineItemEditDialog: React.FC<LineItemEditDialogProps> = ({
  item,
  rfqLineItems,
  isOpen,
  onClose,
  onSave,
}) => {
  if (!isOpen || !item) return null;

  const [description, setDescription] = useState<string>(item.description_raw);
  const [quantity, setQuantity] = useState<number>(item.quantity);
  const [unit, setUnit] = useState<string>(item.unit || "units");
  const [unitPrice, setUnitPrice] = useState<number>(item.unit_price);
  const [quotedTotal, setQuotedTotal] = useState<number>(item.total_price);
  const [leadTime, setLeadTime] = useState<number | undefined>(item.lead_time_days ?? undefined);
  const [rfqItemId, setRfqItemId] = useState<string>(item.rfq_line_item_id || "");
  const [reason, setReason] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDescription(item.description_raw);
    setQuantity(item.quantity);
    setUnit(item.unit || "units");
    setUnitPrice(item.unit_price);
    setQuotedTotal(item.total_price);
    setLeadTime(item.lead_time_days ?? undefined);
    setRfqItemId(item.rfq_line_item_id || "");
    setReason("");
    setError(null);
  }, [item]);

  const calculatedTotal = Number((quantity * unitPrice).toFixed(4));
  const mathDiscrepancy = Math.abs(quotedTotal - calculatedTotal) > 0.01;

  const handleApplyCalculatedToQuoted = () => {
    setQuotedTotal(calculatedTotal);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);

      const patch: Partial<ExtractedLineItem> = {
        description_raw: description,
        quantity,
        unit,
        unit_price: unitPrice,
        total_price: quotedTotal,
        lead_time_days: leadTime ? Number(leadTime) : null,
        rfq_line_item_id: rfqItemId || null,
      };

      await onSave(item.id, patch, reason);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save line item correction");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-item-title"
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div>
            <h2 id="edit-item-title" className="text-base font-bold text-white flex items-center gap-2">
              <span>Edit Line Item (Preserves Quoted vs Calculated)</span>
              {item.human_corrected && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
                  Previously Corrected
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Auditable human-in-the-loop correction. Original extraction values remain preserved in audit history.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          <div className="p-3 bg-blue-950/40 border border-blue-800/60 rounded-lg text-xs text-blue-300">
            <strong>Phase 3 Audit Safeguard:</strong> Changes are recorded with reviewer timestamp and reason. Original supplier-quoted extraction is retained.
          </div>

          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs">
              {error}
            </div>
          )}

          {/* Reason for Change */}
          <div>
            <label htmlFor="edit-reason" className="block text-xs font-semibold text-slate-300 mb-1">
              Reason for Change *
            </label>
            <input
              id="edit-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              placeholder="e.g. Corrected OCR typo in unit price based on invoice page 1"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="edit-description" className="block text-xs font-semibold text-slate-300 mb-1">
              Item Raw Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* RFQ Line Item Matching */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Match with RFQ Line Item
            </label>
            <select
              value={rfqItemId}
              onChange={(e) => setRfqItemId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            >
              <option value="">-- Select matching RFQ requirement --</option>
              {rfqLineItems.map((rfqItem) => (
                <option key={rfqItem.id} value={rfqItem.id}>
                  Item #{rfqItem.position}: {rfqItem.description} ({rfqItem.quantity} {rfqItem.unit})
                </option>
              ))}
            </select>
          </div>

          {/* Qty, Unit, Unit Price */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Quantity</label>
              <input
                type="number"
                step="any"
                min="0.0001"
                value={quantity}
                onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Unit</label>
              <input
                type="text"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Unit Price ({item.currency})
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={unitPrice}
                onChange={(e) => setUnitPrice(parseFloat(e.target.value) || 0)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          {/* Supplier Quoted Total vs ProcureFlow Calculated Total */}
          <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-blue-400" />
                <span>Price Preservation & Verification</span>
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                Calculated ({quantity} × {unitPrice}):{" "}
                <strong className="text-white">${calculatedTotal.toFixed(2)}</strong>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 items-end">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  Supplier-Quoted Total ({item.currency})
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={quotedTotal}
                  onChange={(e) => setQuotedTotal(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
                />
              </div>

              {mathDiscrepancy && (
                <button
                  type="button"
                  onClick={handleApplyCalculatedToQuoted}
                  className="px-3 py-2 text-xs rounded-lg bg-blue-900/40 hover:bg-blue-800/60 border border-blue-700/60 text-blue-200 transition font-medium text-left"
                >
                  Set Quoted to Calculated (${calculatedTotal.toFixed(2)})
                </button>
              )}
            </div>

            {mathDiscrepancy && (
              <div className="flex items-center gap-2 text-[11px] text-amber-300 bg-amber-950/30 border border-amber-800/40 p-2 rounded">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                <span>
                  Mathematical discrepancy detected: Quoted total (${quotedTotal.toFixed(2)}) differs from calculated total (${calculatedTotal.toFixed(2)}).
                </span>
              </div>
            )}
          </div>

          {/* Lead Time */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Lead Time (Calendar Days)
            </label>
            <input
              type="number"
              min="0"
              value={leadTime ?? ""}
              onChange={(e) => setLeadTime(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="e.g. 14"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Footer Actions */}
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
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg shadow-lg shadow-blue-500/20 transition"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "Saving Changes..." : "Save Correction"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
