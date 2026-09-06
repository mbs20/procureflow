import React, { useState } from "react";
import {
  X,
  Plus,
  Trash2,
  Scale,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Layers,
} from "lucide-react";
import { Criterion, LineItem, createRFQ } from "../../api/rfq";

interface CreateRFQModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateRFQModal: React.FC<CreateRFQModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Industrial Valves & Equipment");
  const [currency, setCurrency] = useState("USD");

  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: "3-inch Stainless Steel Lug Butterfly Valve Class 150", quantity: 25, unit: "pcs" },
    { description: "2-inch Flanged 2-Piece Stainless Steel Ball Valve", quantity: 40, unit: "pcs" },
  ]);

  const [criteria, setCriteria] = useState<Criterion[]>([
    { name: "Total Cost of Procurement", weight: 0.40, direction: "lower_is_better", data_type: "price", is_knockout: false },
    { name: "Delivery Lead Time", weight: 0.30, direction: "lower_is_better", data_type: "days", is_knockout: false },
    { name: "Warranty Period", weight: 0.20, direction: "higher_is_better", data_type: "days", is_knockout: false },
    { name: "Payment Terms", weight: 0.10, direction: "higher_is_better", data_type: "enum", is_knockout: false },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const totalWeight = criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0);
  const totalWeightPercent = Math.round(totalWeight * 100);
  const isWeightValid = Math.abs(totalWeight - 1.0) <= 0.001;

  const handleAddLineItem = () => {
    setLineItems([...lineItems, { description: "", quantity: 1, unit: "pcs" }]);
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleLineItemChange = (index: number, field: keyof LineItem, value: any) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: value };
    setLineItems(updated);
  };

  const handleAddCriterion = () => {
    setCriteria([...criteria, { name: "New Criterion", weight: 0.10, direction: "lower_is_better", data_type: "price" }]);
  };

  const handleRemoveCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const handleCriterionChange = (index: number, field: keyof Criterion, value: any) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], [field]: value };
    setCriteria(updated);
  };

  const applyBalancedPreset = () => {
    setCriteria([
      { name: "Commercial Price (TCO)", weight: 0.40, direction: "lower_is_better", data_type: "price" },
      { name: "Lead Time (Ex-works)", weight: 0.30, direction: "lower_is_better", data_type: "days" },
      { name: "Technical Compliance", weight: 0.20, direction: "higher_is_better", data_type: "percentage" },
      { name: "Payment Flexibility", weight: 0.10, direction: "higher_is_better", data_type: "enum" },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please specify an RFQ title");
      return;
    }
    if (!isWeightValid) {
      setError(`Criteria weights must sum to exactly 100% (currently ${totalWeightPercent}%)`);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await createRFQ({
        title,
        description,
        category,
        reference_currency: currency,
        line_items: lineItems,
        criteria,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create RFQ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-2xl border border-border/80 bg-card p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Create Procurement Request (RFQ)</h2>
              <p className="text-xs text-muted-foreground">Define required line items and evaluation criteria</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* General Information */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">1. RFQ Overview</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-foreground">RFQ Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q4 2026 Stainless Steel Piping & Valves"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Category</label>
                <input
                  type="text"
                  placeholder="e.g. Industrial Valves"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Reference Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="USD">USD ($ - US Dollar)</option>
                  <option value="EUR">EUR (€ - Euro)</option>
                  <option value="GBP">GBP (£ - British Pound)</option>
                  <option value="CAD">CAD ($ - Canadian Dollar)</option>
                  <option value="JPY">JPY (¥ - Japanese Yen)</option>
                </select>
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-foreground">Scope / Description</label>
                <textarea
                  rows={2}
                  placeholder="Additional context or technical specifications..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
          </div>

          {/* Line Items Builder */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">2. Required Line Items</h3>
              <button
                type="button"
                onClick={handleAddLineItem}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/50 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-secondary"
              >
                <Plus className="h-3 w-3" />
                Add Item
              </button>
            </div>

            <div className="space-y-2">
              {lineItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/20 p-2.5">
                  <span className="text-xs font-mono text-muted-foreground w-6 text-center">{idx + 1}</span>
                  <input
                    type="text"
                    required
                    placeholder="Product or service description"
                    value={item.description}
                    onChange={(e) => handleLineItemChange(idx, "description", e.target.value)}
                    className="flex-1 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <input
                    type="number"
                    min="1"
                    required
                    placeholder="Qty"
                    value={item.quantity}
                    onChange={(e) => handleLineItemChange(idx, "quantity", parseFloat(e.target.value) || 0)}
                    className="w-20 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <input
                    type="text"
                    placeholder="Unit"
                    value={item.unit}
                    onChange={(e) => handleLineItemChange(idx, "unit", e.target.value)}
                    className="w-20 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  {lineItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveLineItem(idx)}
                      className="text-muted-foreground hover:text-red-400 p-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Evaluation Criteria Weighting Builder */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Scale className="h-3.5 w-3.5 text-blue-400" />
                  3. Weighted Evaluation Criteria
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={applyBalancedPreset}
                  className="flex items-center gap-1 rounded-lg border border-purple-500/30 bg-purple-500/10 px-2.5 py-1 text-xs font-medium text-purple-300 hover:bg-purple-500/20"
                >
                  <Sparkles className="h-3 w-3" />
                  Balanced Preset (40/30/20/10)
                </button>
                <button
                  type="button"
                  onClick={handleAddCriterion}
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/50 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-secondary"
                >
                  <Plus className="h-3 w-3" />
                  Add Criterion
                </button>
              </div>
            </div>

            {/* Total Weight Live Status Meter */}
            <div className="rounded-xl border border-border bg-secondary/30 p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-muted-foreground">Total Weight Sum</span>
                <span className={`font-bold flex items-center gap-1 ${isWeightValid ? "text-emerald-400" : "text-amber-400"}`}>
                  {isWeightValid ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                  {totalWeightPercent}% {isWeightValid ? "(Valid 100%)" : "(Must equal 100%)"}
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${isWeightValid ? "bg-emerald-500" : totalWeight > 1.0 ? "bg-red-500" : "bg-amber-500"}`}
                  style={{ width: `${Math.min(totalWeightPercent, 100)}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              {criteria.map((crit, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/20 p-2.5">
                  <input
                    type="text"
                    required
                    placeholder="Criterion name"
                    value={crit.name}
                    onChange={(e) => handleCriterionChange(idx, "name", e.target.value)}
                    className="flex-1 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <div className="flex items-center gap-1 bg-secondary/50 border border-border rounded-md px-2 py-1">
                    <input
                      type="number"
                      step="0.05"
                      min="0.01"
                      max="1.0"
                      value={crit.weight}
                      onChange={(e) => handleCriterionChange(idx, "weight", parseFloat(e.target.value) || 0)}
                      className="w-14 bg-transparent text-xs text-foreground focus:outline-none text-right font-mono"
                    />
                    <span className="text-[10px] text-muted-foreground">wt</span>
                  </div>
                  <select
                    value={crit.direction}
                    onChange={(e) => handleCriterionChange(idx, "direction", e.target.value)}
                    className="w-36 rounded-md border border-border bg-secondary/50 px-2 py-1.5 text-xs text-foreground focus:outline-none"
                  >
                    <option value="lower_is_better">Lower is Better (e.g. Price)</option>
                    <option value="higher_is_better">Higher is Better (e.g. Warranty)</option>
                  </select>
                  {criteria.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveCriterion(idx)}
                      className="text-muted-foreground hover:text-red-400 p-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-border/60 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !isWeightValid}
              className={`rounded-lg px-5 py-2 text-xs font-bold text-white transition-all shadow-md ${
                isWeightValid
                  ? "bg-primary hover:bg-blue-600 shadow-blue-500/25 cursor-pointer"
                  : "bg-muted cursor-not-allowed opacity-60"
              }`}
            >
              {loading ? "Creating..." : "Create RFQ"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
