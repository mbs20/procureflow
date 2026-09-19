import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, Plus } from "lucide-react";
import { ExtractedLineItemCreate } from "../../api/quotation";
import { RFQLineItem } from "../../api/rfq";
import { parseReviewNumber } from "../../lib/reviewNumbers";
import { formatCurrency } from "../../lib/formatters";
import { translateBackendError } from "../../lib/errorMessageMap";

interface LineItemAddDialogProps {
  isOpen: boolean;
  currency: string;
  rfqLineItems: RFQLineItem[];
  onClose: () => void;
  onAdd: (data: ExtractedLineItemCreate) => Promise<void>;
}

export const LineItemAddDialog: React.FC<LineItemAddDialogProps> = ({
  isOpen,
  currency,
  rfqLineItems,
  onClose,
  onAdd,
}) => {
  const { t } = useTranslation();

  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("units");
  const [unitPrice, setUnitPrice] = useState("0");
  const [totalPrice, setTotalPrice] = useState<string>("");
  const [leadTime, setLeadTime] = useState<string>("");
  const [rfqItemId, setRfqItemId] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const parsedQuantity = parseReviewNumber(quantity, { positive: true });
  const parsedUnitPrice = parseReviewNumber(unitPrice);
  const parsedTotal = parseReviewNumber(totalPrice);
  const parsedLeadTime = leadTime.trim() === "" ? null : parseReviewNumber(leadTime, { integer: true });
  const product = parsedQuantity !== null && parsedUnitPrice !== null ? parsedQuantity * parsedUnitPrice : NaN;
  const calculatedTotal = Number.isFinite(product) ? Number(product.toFixed(4)) : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (parsedQuantity === null || parsedUnitPrice === null || calculatedTotal === null || (totalPrice.trim() !== "" && parsedTotal === null) || (leadTime.trim() !== "" && parsedLeadTime === null)) {
      setError(t('review.invalidNumericValues'));
      return;
    }
    try {
      setAdding(true);
      setError(null);
      await onAdd({
        description_raw: description,
        quantity: parsedQuantity,
        unit,
        unit_price: parsedUnitPrice,
        total_price: parsedTotal ?? calculatedTotal,
        currency,
        lead_time_days: parsedLeadTime,
        rfq_line_item_id: rfqItemId || null,
      });
      onClose();
    } catch (err: any) {
      setError(translateBackendError(err, t));
    } finally {
      setAdding(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-item-title"
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-xl overflow-hidden animate-fadeIn">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div>
            <h2 id="add-item-title" className="text-base font-bold text-white">
              {t('review.addMissedTitle')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('review.addMissedSubtitle')}
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

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t('review.descriptionLabel')}
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Stainless Steel Fasteners M8"
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t('review.matchRfqRequirement')}
            </label>
            <select
              value={rfqItemId}
              onChange={(e) => setRfqItemId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            >
              <option value="">{t('review.noneUnmatched')}</option>
              {rfqLineItems.map((rfqItem) => (
                <option key={rfqItem.id} value={rfqItem.id}>
                  Item #{rfqItem.position}: {rfqItem.description} ({rfqItem.quantity} {rfqItem.unit})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">{t('review.quantityLabel')} *</label>
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
              <label className="block text-xs font-semibold text-slate-300 mb-1">{t('review.unitLabel')} *</label>
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
                {t('review.unitPriceLabel', { currency })} *
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                {t('review.supplierQuotedTotalOptional')}
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={totalPrice ?? ""}
                onChange={(e) => setTotalPrice(e.target.value)}
                placeholder={t('review.defaultCalculated', { amount: formatCurrency(calculatedTotal, currency) })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                {t('review.leadTimeDays')}
              </label>
              <input
                type="number"
                min="0"
                value={leadTime ?? ""}
                onChange={(e) => setLeadTime(e.target.value)}
                placeholder="e.g. 7"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>
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
              disabled={adding}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              <span>{adding ? t('review.addingItem') : t('review.addItem')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
