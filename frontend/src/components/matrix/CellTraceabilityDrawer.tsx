import React, { useState } from "react";
import { useTranslation, Trans } from "react-i18next";
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
import { formatCurrency } from "../../lib/formatters";
import { translateBackendError } from "../../lib/errorMessageMap";

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
  const { t } = useTranslation();
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
      setError(t('matrix.auditReasonPlaceholder'));
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

      setActionMessage(t('matrix.overrideSuccess'));
      onRefresh();
      setTimeout(() => {
        setActionMessage(null);
        setActiveTab("trace");
      }, 1500);
    } catch (err: any) {
      setError(translateBackendError(err, t));
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
      setActionMessage(t('matrix.revertSuccess'));
      onRefresh();
      setTimeout(() => setActionMessage(null), 1500);
    } catch (err: any) {
      setError(translateBackendError(err, t));
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
            <h2 className="text-base font-bold text-white">{t('matrix.traceDrawerTitle')}</h2>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {supplier.supplier_name} • #{row.position} {row.description}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-muted-foreground hover:text-white hover:bg-secondary transition-colors"
          aria-label={t('common.close')}
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
          {t('matrix.tabEvidence')}
        </button>
        <button
          onClick={() => setActiveTab("override")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "override"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {cell.is_human_overridden ? t('matrix.tabManageOverride') : t('matrix.tabApplyOverride')}
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
                  {t('matrix.normalizedComparable')}
                </div>
                <div className="text-xl font-mono font-bold text-white">
                  {cell.normalized_unit_price !== null && cell.normalized_unit_price !== undefined
                    ? formatCurrency(cell.normalized_unit_price, referenceCurrency)
                    : t('matrix.unresolved')}
                </div>
                <div className="text-xs text-muted-foreground">
                  <Trans
                    i18nKey="matrix.extendedLabel"
                    values={{
                      amount: cell.normalized_extended_price !== null && cell.normalized_extended_price !== undefined
                        ? formatCurrency(cell.normalized_extended_price, referenceCurrency)
                        : "N/A"
                    }}
                    components={{ 1: <strong className="text-foreground" /> }}
                  />
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {t('matrix.basisLabel', { qty: row.required_quantity, unit: cell.canonical_unit || row.required_unit })}
                </div>
              </div>

              {/* Quoted Raw Value */}
              <div className="rounded-xl border border-border/80 bg-secondary/30 p-4 space-y-2">
                <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">
                  {t('matrix.quotedOriginalTitle')}
                </div>
                <div className="text-xl font-mono font-bold text-foreground">
                  {cell.quoted_unit_price !== null && cell.quoted_unit_price !== undefined
                    ? formatCurrency(cell.quoted_unit_price, cell.original_currency)
                    : t('matrix.notQuoted')}
                </div>
                <div className="text-xs text-muted-foreground">
                  <Trans
                    i18nKey="matrix.quotedTotalLabel"
                    values={{
                      amount: cell.quoted_total_price ? formatCurrency(cell.quoted_total_price, cell.original_currency) : "N/A"
                    }}
                    components={{ 1: <strong className="text-foreground" /> }}
                  />
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {t('matrix.basisLabel', { qty: cell.quoted_quantity, unit: cell.quoted_unit })}
                </div>
              </div>
            </div>

            {/* Overridden Banner */}
            {cell.is_human_overridden && (
              <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-400 flex items-center gap-1.5">
                    <Scale className="h-4 w-4" /> {t('matrix.humanOverrideActive')}
                  </span>
                  <button
                    onClick={handleRevertOverride}
                    disabled={submitting}
                    className="flex items-center gap-1 rounded bg-purple-500/20 px-2 py-1 text-[11px] font-semibold text-purple-300 hover:bg-purple-500/30 transition-colors"
                  >
                    <RotateCcw className="h-3 w-3" /> {t('matrix.revertBtn')}
                  </button>
                </div>
                {cell.override_reason && (
                  <p className="text-xs text-muted-foreground italic">
                    {t('matrix.reasonPrefix', { reason: cell.override_reason })}
                  </p>
                )}
              </div>
            )}

            {/* Normalization Math & Provenance */}
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <Coins className="h-4 w-4 text-emerald-400" />
                {t('matrix.conversionParams')}
              </div>

              <div className="space-y-2 text-xs divide-y divide-border/40">
                {/* FX Rate */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">{t('matrix.fxRateUsed')}</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.fx_rate_used ? `1 ${cell.original_currency} = ${cell.fx_rate_used} ${referenceCurrency}` : t('matrix.sameCurrency')}
                  </span>
                </div>

                {/* UOM Conversion Factor */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">{t('matrix.uomFactorLabel')}</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.uom_conversion_factor ? `1 ${cell.quoted_unit} = ${cell.uom_conversion_factor} ${cell.canonical_unit}` : t('matrix.directMatch')}
                  </span>
                </div>

                {/* Lead Time */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">{t('matrix.leadTimeInterpretation')}</span>
                  <span className="font-semibold text-foreground">
                    {cell.line_lead_time_display || t('matrix.notSpecified')}
                  </span>
                </div>

                {/* Math Discrepancy Flag */}
                {cell.has_math_discrepancy && (
                  <div className="pt-2 text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>
                      {t('matrix.mathDiscrepancyWarning', {
                        quoted: cell.quoted_total_price,
                        calculated: cell.calculated_total_price
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Source Document Evidence */}
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <FileText className="h-4 w-4 text-blue-400" />
                {t('matrix.extractionEvidence')}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>{t('matrix.sourcePage')}</span>
                  <span className="font-mono font-semibold text-foreground">
                    {cell.source_page !== null && cell.source_page !== undefined ? t('matrix.pagePrefix', { page: cell.source_page }) : t('matrix.extractedDocument')}
                  </span>
                </div>

                {cell.source_evidence && (
                  <div className="rounded-lg bg-black/40 p-3 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-32">
                    <pre>{JSON.stringify(cell.source_evidence, null, 2)}</pre>
                  </div>
                )}

                <div className="pt-2">
                  <a
                    href={cell.source_document_id ? `/api/v1/quotations/${supplier.quotation_id}/documents/${cell.source_document_id}/download` : `/quotations/${supplier.quotation_id}/review`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    {t(cell.source_document_id ? 'matrix.downloadOriginalDocument' : 'matrix.viewOriginalDocument')} <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Human Override Form */
          <form onSubmit={handleApplyOverride} className="space-y-4">
            <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
              <label className="text-xs font-bold text-white block">{t('matrix.overrideFieldTarget')}</label>
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
                  {t('matrix.uomFactorBtn')}
                  <span className="block text-[10px] text-muted-foreground font-normal">{t('matrix.uomFactorHint')}</span>
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
                  {t('matrix.customFxBtn')}
                  <span className="block text-[10px] text-muted-foreground font-normal">{t('matrix.customFxHint')}</span>
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
                  {t('matrix.directPriceBtn')}
                  <span className="block text-[10px] text-muted-foreground font-normal">
                    {t('matrix.directPriceHint', { currency: referenceCurrency })}
                  </span>
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
                  {t('matrix.leadTimeDaysBtn')}
                  <span className="block text-[10px] text-muted-foreground font-normal">{t('matrix.leadTimeDaysHint')}</span>
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
              <label className="text-xs font-bold text-white block">{t('matrix.auditReasonLabel')}</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder={t('matrix.auditReasonPlaceholder')}
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
              {submitting ? t('matrix.applyingOverride') : t('matrix.saveOverride')}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
