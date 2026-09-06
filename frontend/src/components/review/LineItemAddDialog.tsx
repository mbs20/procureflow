import React, { useState } from "react";
import { X, Plus } from "lucide-react";
import { ExtractedLineItemCreate } from "../../api/quotation";
import { RFQLineItem } from "../../api/rfq";

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
  if (!isOpen) return null;

  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState("units");
  const [unitPrice, setUnitPrice] = useState(0);
  const [totalPrice, setTotalPrice] = useState<number | undefined>(undefined);
  const [leadTime, setLeadTime] = useState<number | undefined>(undefined);
  const [rfqItemId, setRfqItemId] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculatedTotal = Number((quantity * unitPrice).toFixed(4));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setAdding(true);
      setError(null);
      await onAdd({
        description_raw: description,
        quantity,
        unit,
        unit_price: unitPrice,
        total_price: totalPrice !== undefined ? totalPrice : calculatedTotal,
        currency,
        lead_time_days: leadTime ? Number(leadTime) : null,
        rfq_line_item_id: rfqItemId || null,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to add line item");
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
              Add Missed Line Item
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Append an item not automatically recognized during extraction. Marked as human-corrected.
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

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Description *
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
              Match RFQ Requirement
            </label>
            <select
              value={rfqItemId}
              onChange={(e) => setRfqItemId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 transition"
            >
              <option value="">-- None (unmatched) --</option>
              {rfqLineItems.map((rfqItem) => (
                <option key={rfqItem.id} value={rfqItem.id}>
                  Item #{rfqItem.position}: {rfqItem.description} ({rfqItem.quantity} {rfqItem.unit})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Quantity *</label>
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
              <label className="block text-xs font-semibold text-slate-300 mb-1">Unit *</label>
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
                Unit Price ({currency}) *
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Supplier-Quoted Total (Optional)
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={totalPrice ?? ""}
                onChange={(e) => setTotalPrice(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder={`Default: $${calculatedTotal.toFixed(2)}`}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Lead Time (Days)
              </label>
              <input
                type="number"
                min="0"
                value={leadTime ?? ""}
                onChange={(e) => setLeadTime(e.target.value ? parseInt(e.target.value) : undefined)}
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
              Cancel
            </button>
            <button
              type="submit"
              disabled={adding}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              <span>{adding ? "Adding Item..." : "Add Line Item"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
