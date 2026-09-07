import React, { useState } from "react";
import {
  X,
  ShieldCheck,
  FileText,
  Coins,
  Scale,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import {
  MatrixLineItemCell,
  MatrixRequiredRow,
  MatrixSupplierHeader,
  applyNormalizationOverride,
  revertNormalizationOverride,
} from "../../api/matrix";

interface CellTraceabilityDrawerProps {
  rfqId: string;
  referenceCurrency: string;
  cell: MatrixLineItemCell;
  row: MatrixRequiredRow;
  supplier: MatrixSupplierHeader;
  onClose: () => void;
  onRefresh: () => void;
}

export const CellTraceabilityDrawer: React.FC<CellTraceabilityDrawerProps> = ({
  rfqId,
  referenceCurrency,
  cell,
  row,
  supplier,
  onClose,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<"trace" | "override">("trace");
  const [overrideType, setOverrideType] = useState<"uom_factor" | "fx_rate" | "unit_price" | "lead_time">("uom_factor");
  const [overrideValue, setOverrideValue] = useState<string>("");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [revertReason] = useState<string>("Reverted to deterministic default");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleApplyOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideValue || !overrideReason.trim()) {
      setError("Please provide both an override value and a justification reason.");
      return;
    }
    if (!cell.line_item_id) {
      setError("No line item ID available for this cell.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const numVal = parseFloat(overrideValue);
      let payloadValue: Record<string, any> = {};

      if (overrideType === "uom_factor") {
        payloadValue = { conversion_factor: numVal };
      } else if (overrideType === "fx_rate") {
        payloadValue = { fx_rate: numVal };
      } else if (overrideType === "unit_price") {
        payloadValue = { normalized_unit_price: numVal };
      } else if (overrideType === "lead_time") {
        payloadValue = { lead_time_days: parseInt(overrideValue, 10) };
      }

      await applyNormalizationOverride(rfqId, {
        quotation_id: supplier.quotation_id,
        line_item_id: cell.line_item_id,
        field_name: overrideType === "uom_factor" ? "conversion_factor" : overrideType,
        override_value: payloadValue,
        override_reason: overrideReason,
      });

      setActionMessage("Human normalization override applied successfully.");
      onRefresh();
      setTimeout(() => {
        setActionMessage(null);
        setActiveTab("trace");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to apply override");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevertOverride = async () => {
    if (!cell.override_id) return;
    setSubmitting(true);
    setError(null);
    try {
      await revertNormalizationOverride(
        rfqId,
        cell.override_id,
        revertReason || "Reverted to deterministic default"
      );
      setActionMessage("Override reverted to deterministic baseline.");
      onRefresh();
      setTimeout(() => setActionMessage(null), 1500);
    } catch (err: any) {
      setError(err.message || "Failed to revert override");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-card border-l border-border shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-5 border-b border-border/70 flex items-center justify-between bg-secondary/20">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-blue-400" />
            <h2 className="text-base font-bold text-white">Cell Traceability & Provenance</h2>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {supplier.supplier_name} • #{row.position} {row.description}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-muted-foreground hover:text-white hover:bg-secondary transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border/70 bg-secondary/10 px-5 pt-2">
        <button
          onClick={() => setActiveTab("trace")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "trace"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Evidence & Normalization
        </button>
        <button
          onClick={() => setActiveTab("override")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "override"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {cell.is_human_overridden ? "Manage Override (Active)" : "Apply Manual Override"}
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {actionMessage && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-400">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {activeTab === "trace" ? (
          <>
            {/* Dual Representation Card */}
            <div className="grid grid-cols-2 gap-3">
              {/* Normalized Value */}
              <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-4 space-y-2">
                <div className="text-[10px] uppercase font-bold tracking-wider text-blue-400">
                  Normalized Comparable
                </div>
                <div className="text-xl font-mono font-bold text-white">
                  {cell.normalized_unit_price !== null && cell.normalized_unit_price !== undefined
                    ? `${cell.normalized_unit_price.toFixed(4)} ${referenceCurrency}`
                    : "Unresolved"}
                </div>
                <div className="text-xs text-muted-foreground">
                  Extended: <strong className="text-foreground">{cell.normalized_extended_price !== null && cell.normalized_extended_price !== undefined ? `$${cell.normalized_extended_price.toFixed(2)} ${referenceCurrency}` : "N/A"}</strong>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Basis: {row.required_quantity} {cell.canonical_unit || row.required_unit}
                </div>
              </div>

              {/* Quoted Raw Value */}
              <div className="rounded-xl border border-border/80 bg-secondary/30 p-4 space-y-2">
                <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">
                  Quoted Original
                </div>
                <div className="text-xl font-mono font-bold text-foreground">
                  {cell.quoted_unit_price !== null && cell.quoted_unit_price !== undefined
                    ? `${cell.quoted_unit_price.toFixed(2)} ${cell.original_currency}`
                    : "Not Quoted"}
                </div>
                <div className="text-xs text-muted-foreground">
                  Quoted Total: <strong className="text-foreground">{cell.quoted_total_price ? `${cell.quoted_total_price.toFixed(2)} ${cell.original_currency}` : "N/A"}</strong>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Basis: {cell.quoted_quantity} {cell.quoted_unit}
                </div>
              </div>
            </div>

            {/* Overridden Banner */}
            {cell.is_human_overridden && (
              <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-400 flex items-center gap-1.5">
                    <Scale className="h-4 w-4" /> Human Override Active
                  </span>
                  <button
                    onClick={handleRevertOverride}
                    disabled={submitting}
                    className="flex items-center gap-1 rounded bg-purple-500/20 px-2 py-1 text-[11px] font-semibold text-purple-300 hover:bg-purple-500/30 transition-colors"
                  >
                    <RotateCcw className="h-3 w-3" /> Revert
                  </button>
                </div>
                {cell.override_reason && (
                  <p className="text-xs text-muted-foreground italic">
                    Reason: "{cell.override_reason}"
                  </p>
                )}
              </div>
            )}

            {/* Normalization Math & Provenance */}
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <Coins className="h-4 w-4 text-emerald-400" />
                Normalization Conversion Parameters
              </div>

              <div className="space-y-2 text-xs divide-y divide-border/40">
                {/* FX Rate */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">FX Rate Used:</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.fx_rate_used ? `1 ${cell.original_currency} = ${cell.fx_rate_used} ${referenceCurrency}` : "Same currency (1.0000)"}
                  </span>
                </div>

                {/* UOM Conversion Factor */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">UOM Conversion Factor:</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.uom_conversion_factor ? `1 ${cell.quoted_unit} = ${cell.uom_conversion_factor} ${cell.canonical_unit}` : "1.0000 (Direct match)"}
                  </span>
                </div>

                {/* Lead Time */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">Lead Time Interpretation:</span>
                  <span className="font-semibold text-foreground">
                    {cell.line_lead_time_display || "Not specified"}
                  </span>
                </div>

                {/* Math Discrepancy Flag */}
                {cell.has_math_discrepancy && (
                  <div className="pt-2 text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>
                      Quoted total ({cell.quoted_total_price}) differs from unit price × qty calculation ({cell.calculated_total_price}).
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Source Document Evidence */}
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <FileText className="h-4 w-4 text-blue-400" />
                Phase 3 Extraction Evidence
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Source Page:</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.source_page !== null && cell.source_page !== undefined ? `Page ${cell.source_page}` : "Extracted document"}
                  </span>
                </div>

                {cell.source_evidence && (
                  <div className="rounded-lg bg-black/40 p-3 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-32">
                    <pre>{JSON.stringify(cell.source_evidence, null, 2)}</pre>
                  </div>
                )}

                <div className="pt-2">
                  <a
                    href={`/api/v1/quotations/${supplier.quotation_id}/documents`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View Original Document <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Human Override Form */
          <form onSubmit={handleApplyOverride} className="space-y-4">
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <label className="text-xs font-bold text-white block">Override Field Target</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setOverrideType("uom_factor")}
                  className={`rounded-lg p-2.5 text-xs font-semibold border transition-all text-left ${
                    overrideType === "uom_factor"
                      ? "border-blue-500 bg-blue-500/10 text-white"
                      : "border-border bg-secondary/30 text-muted-foreground hover:bg-secondary/50"
                  }`}
                >
                  UOM Conversion Factor
                  <span className="block text-[10px] text-muted-foreground font-normal">e.g. 1 box = 24 pcs</span>
                </button>

                <button
                  type="button"
                  onClick={() => setOverrideType("fx_rate")}
                  className={`rounded-lg p-2.5 text-xs font-semibold border transition-all text-left ${
                    overrideType === "fx_rate"
                      ? "border-blue-500 bg-blue-500/10 text-white"
                      : "border-border bg-secondary/30 text-muted-foreground hover:bg-secondary/50"
                  }`}
                >
                  Custom FX Rate
                  <span className="block text-[10px] text-muted-foreground font-normal">e.g. 1 EUR = 1.10 USD</span>
                </button>

                <button
                  type="button"
                  onClick={() => setOverrideType("unit_price")}
                  className={`rounded-lg p-2.5 text-xs font-semibold border transition-all text-left ${
                    overrideType === "unit_price"
                      ? "border-blue-500 bg-blue-500/10 text-white"
                      : "border-border bg-secondary/30 text-muted-foreground hover:bg-secondary/50"
                  }`}
                >
                  Direct Normalized Price
                  <span className="block text-[10px] text-muted-foreground font-normal">Manual price in {referenceCurrency}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setOverrideType("lead_time")}
                  className={`rounded-lg p-2.5 text-xs font-semibold border transition-all text-left ${
                    overrideType === "lead_time"
                      ? "border-blue-500 bg-blue-500/10 text-white"
                      : "border-border bg-secondary/30 text-muted-foreground hover:bg-secondary/50"
                  }`}
                >
                  Lead Time Days
                  <span className="block text-[10px] text-muted-foreground font-normal">Expedited or confirmed days</span>
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-white block">
                {overrideType === "uom_factor" && `Conversion Factor (1 ${cell.quoted_unit || "unit"} = X ${row.required_unit})`}
                {overrideType === "fx_rate" && `Exchange Rate (1 ${cell.original_currency} = X ${referenceCurrency})`}
                {overrideType === "unit_price" && `Normalized Unit Price (${referenceCurrency})`}
                {overrideType === "lead_time" && "Lead Time (Calendar Days)"}
              </label>
              <input
                type="number"
                step="any"
                value={overrideValue}
                onChange={(e) => setOverrideValue(e.target.value)}
                placeholder="Enter value..."
                className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-white block">Audit Justification Reason</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="State the reason for this manual correction (mandatory for audit trail)..."
                rows={3}
                className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-primary py-2.5 text-xs font-bold text-white hover:bg-blue-600 transition-colors shadow-md shadow-blue-500/20 disabled:opacity-50"
            >
              {submitting ? "Applying Override..." : "Save Normalization Override"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
