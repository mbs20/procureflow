import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { X, Save, AlertTriangle, Calculator } from "lucide-react";
import { ExtractedLineItem } from "../../api/quotation";
import { RFQLineItem } from "../../api/rfq";
import { parseReviewNumber } from "../../lib/reviewNumbers";
import { formatCurrency } from "../../lib/formatters";
import { translateBackendError } from "../../lib/errorMessageMap";

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
  const { t } = useTranslation();

  const [description, setDescription] = useState<string>(item?.description_raw || "");
  const [quantity, setQuantity] = useState<string>(String(item?.quantity ?? ""));
  const [unit, setUnit] = useState<string>(item?.unit || "units");
  const [unitPrice, setUnitPrice] = useState<string>(String(item?.unit_price ?? ""));
  const [quotedTotal, setQuotedTotal] = useState<string>(String(item?.total_price ?? ""));
  const [leadTime, setLeadTime] = useState<string>(String(item?.lead_time_days ?? ""));
  const [rfqItemId, setRfqItemId] = useState<string>(item?.rfq_line_item_id || "");
  const [reason, setReason] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (item) {
      setDescription(item.description_raw);
      setQuantity(String(item.quantity ?? ""));
      setUnit(item.unit || "units");
      setUnitPrice(String(item.unit_price ?? ""));
      setQuotedTotal(String(item.total_price ?? ""));
      setLeadTime(String(item.lead_time_days ?? ""));
      setRfqItemId(item.rfq_line_item_id || "");
      setReason("");
      setError(null);
    }
  }, [item]);

  if (!isOpen || !item) return null;

  const parsedQuantity = parseReviewNumber(quantity, { positive: true });
  const parsedUnitPrice = parseReviewNumber(unitPrice);
  const parsedTotal = parseReviewNumber(quotedTotal);
  const parsedLeadTime = leadTime.trim() === "" ? null : parseReviewNumber(leadTime, { integer: true });
  const product = parsedQuantity !== null && parsedUnitPrice !== null ? parsedQuantity * parsedUnitPrice : NaN;
  const calculatedTotal = Number.isFinite(product) ? Number(product.toFixed(4)) : null;
  const mathDiscrepancy = parsedTotal !== null && calculatedTotal !== null && Math.abs(parsedTotal - calculatedTotal) > 0.01;

  const handleApplyCalculatedToQuoted = () => {
    if (calculatedTotal !== null) setQuotedTotal(String(calculatedTotal));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (parsedQuantity === null || parsedUnitPrice === null || calculatedTotal === null || parsedTotal === null || (leadTime.trim() !== "" && parsedLeadTime === null)) {
      setError(t('review.invalidNumericValues'));
      return;
    }
    if (!reason.trim()) {
      setError(t('review.reasonRequired'));
      return;
    }
    try {
      setSaving(true);
      setError(null);

      const patch: Partial<ExtractedLineItem> = {
        description_raw: description,
        quantity: parsedQuantity,
        unit,
        unit_price: parsedUnitPrice,
        total_price: parsedTotal,
        lead_time_days: parsedLeadTime,
        rfq_line_item_id: rfqItemId || null,
      };

      await onSave(item.id, patch, reason.trim());
      onClose();
    } catch (err: any) {
      setError(translateBackendError(err, t));
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
              <span>{t('review.editDialogTitle')}</span>
              {item.human_corrected && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
                  {t('review.previouslyCorrected')}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('review.editDialogSubtitle')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label={t('common.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          <div className="p-3 bg-blue-950/40 border border-blue-800/60 rounded-lg text-xs text-blue-300">
            <strong>{t('review.phase3Safeguard')}</strong>
          </div>

          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs">
              {error}
            </div>
          )}

          {/* Reason for Change */}
          <div>
            <label htmlFor="edit-reason" className="block text-xs font-semibold text-slate-300 mb-1">
              {t('review.reasonForChange')}
            </label>
            <input
              id="edit-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              placeholder={t('review.reasonPlaceholder')}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="edit-description" className="block text-xs font-semibold text-slate-300 mb-1">
              {t('review.rawDescriptionLabel')}
            </label>
            <input
              id="edit-description"
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
              {t('review.matchRfqLabel')}
            </label>
            <select
              value={rfqItemId}
              onChange={(e) => setRfqItemId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            >
              <option value="">{t('review.selectRfqPrompt')}</option>
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
              <label className="block text-xs font-semibold text-slate-300 mb-1">{t('review.quantityLabel')}</label>
              <input
                type="number"
                step="any"
                min="0.0001"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">{t('review.unitLabel')}</label>
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
                {t('review.unitPriceLabel', { currency: item.currency })}
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
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
                <span>{t('review.pricePreservationTitle')}</span>
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {t('review.calculatedFormula', { qty: quantity, price: formatCurrency(unitPrice, item.currency) })}{" "}
                <strong className="text-white">{formatCurrency(calculatedTotal, item.currency)}</strong>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 items-end">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  {t('review.supplierQuotedTotal', { currency: item.currency })}
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={quotedTotal}
                  onChange={(e) => setQuotedTotal(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
                />
              </div>

              {mathDiscrepancy && (
                <button
                  type="button"
                  onClick={handleApplyCalculatedToQuoted}
                  className="px-3 py-2 text-xs rounded-lg bg-blue-900/40 hover:bg-blue-800/60 border border-blue-700/60 text-blue-200 transition font-medium text-left"
                >
                  {t('review.setQuotedToCalculated', { amount: formatCurrency(calculatedTotal, item.currency) })}
                </button>
              )}
            </div>

            {mathDiscrepancy && (
              <div className="flex items-center gap-2 text-[11px] text-amber-300 bg-amber-950/30 border border-amber-800/40 p-2 rounded">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                <span>
                  {t('review.mathDiscrepancy', {
                    quoted: formatCurrency(quotedTotal, item.currency),
                    calculated: formatCurrency(calculatedTotal, item.currency)
                  })}
                </span>
              </div>
            )}
          </div>

          {/* Lead Time */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t('review.leadTimeDaysLabel')}
            </label>
            <input
              type="number"
              min="0"
              value={leadTime ?? ""}
              onChange={(e) => setLeadTime(e.target.value)}
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
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg shadow-lg shadow-blue-500/20 transition"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? t('review.savingChanges') : t('review.saveCorrection')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
