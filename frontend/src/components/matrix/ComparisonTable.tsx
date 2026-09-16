import React from "react";
import { useTranslation, Trans } from "react-i18next";
import {
  FileSpreadsheet,
  AlertTriangle,
  Scale,
  Clock,
  CreditCard,
  Percent,
  Package,
  Layers,
} from "lucide-react";
import {
  ComparisonMatrixResponse,
  MatrixLineItemCell,
  MatrixRequiredRow,
  MatrixSupplierHeader,
} from "../../api/matrix";
import { formatCurrency, formatNumber } from "../../lib/formatters";

interface ComparisonTableProps {
  matrix: ComparisonMatrixResponse;
  highlightMissing: boolean;
  highlightWarnings: boolean;
  showExtraItems: boolean;
  onSelectCell: (cell: MatrixLineItemCell, row: MatrixRequiredRow, supplier: MatrixSupplierHeader) => void;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
  matrix,
  highlightMissing,
  highlightWarnings,
  showExtraItems,
  onSelectCell,
}) => {
  const { t } = useTranslation();
  const { reference_currency, suppliers, required_line_items, extra_line_items } = matrix;

  if (suppliers.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center space-y-4">
        <Layers className="h-10 w-10 text-muted-foreground mx-auto" />
        <h3 className="text-base font-bold text-white">{t('matrix.noQuotationsTitle')}</h3>
        <p className="text-xs text-muted-foreground max-w-md mx-auto">
          {t('matrix.noQuotationsDesc')}
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl border border-border/80 overflow-hidden shadow-2xl space-y-0">
      {/* Scrollable Container with Sticky Columns */}
      <div className="overflow-x-auto focus:outline-none" tabIndex={0} role="region" aria-label={t('matrix.tableAria')}>
        <table className="w-full text-left text-xs border-collapse">
          {/* Supplier Headers */}
          <thead>
            <tr className="border-b border-border/80 bg-secondary/40">
              {/* Sticky Left Corner */}
              <th className="sticky left-0 z-20 bg-card/95 backdrop-blur-md p-4 w-72 min-w-[280px] border-r border-border/80">
                <div className="flex items-center gap-2 text-white font-bold text-sm">
                  <FileSpreadsheet className="h-4 w-4 text-blue-400" />
                  {t('matrix.rfqRequirementScope')}
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5">
                  <Trans
                    i18nKey="matrix.baseCurrencyInfo"
                    values={{ currency: reference_currency, count: suppliers.length }}
                    components={{ 1: <strong className="text-foreground" /> }}
                  />
                </div>
              </th>

              {/* Dynamic Supplier Columns */}
              {suppliers.map((supp) => {
                const isComplete = supp.rfq_coverage_pct >= 100;
                return (
                  <th
                    key={supp.quotation_id}
                    className="p-4 w-72 min-w-[280px] border-r border-border/60 bg-secondary/20 align-top"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-white truncate" title={supp.supplier_name}>
                          {supp.supplier_name}
                        </span>
                        <span className="rounded bg-blue-500/10 px-2 py-0.5 text-[10px] font-mono font-bold text-blue-400 border border-blue-500/20 uppercase">
                          {supp.original_currency}
                        </span>
                      </div>

                      {/* Coverage Progress Bar */}
                      <div className="space-y-1 pt-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground flex items-center gap-1">
                            <Percent className="h-3 w-3" /> {t('matrix.coverageLabel')}
                          </span>
                          <span
                            className={`font-semibold font-mono ${
                              isComplete ? "text-emerald-400" : "text-amber-400"
                            }`}
                          >
                            {supp.rfq_coverage_pct}% ({supp.quoted_items_count}/{supp.total_rfq_items})
                          </span>
                        </div>
                        <div className="w-full bg-secondary/60 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              isComplete ? "bg-emerald-500" : "bg-amber-500"
                            }`}
                            style={{ width: `${supp.rfq_coverage_pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody>
            {/* Commercial Terms Summary Section */}
            <tr className="bg-secondary/30 border-b border-border/80 font-semibold text-muted-foreground text-[11px]">
              <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80 uppercase tracking-wider text-muted-foreground">
                {t('matrix.commercialSummaryEnvelope')}
              </td>
              {suppliers.map((supp) => (
                <td key={supp.quotation_id} className="p-3 border-r border-border/60 text-muted-foreground">
                  <span className="text-[10px] uppercase font-bold tracking-wider">{t('matrix.commercialOverview')}</span>
                </td>
              ))}
            </tr>

            {/* Total Normalized Subtotal */}
            <tr className="border-b border-border/40 hover:bg-secondary/10 transition-colors">
              <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80">
                <div className="font-semibold text-foreground text-xs">{t('matrix.normalizedSubtotal')}</div>
                <div className="text-[10px] text-muted-foreground">{t('matrix.normalizedSubtotalDesc')}</div>
              </td>
              {suppliers.map((supp) => (
                <td key={supp.quotation_id} className="p-3 border-r border-border/60">
                  <div className="font-mono text-base font-bold text-white">
                    ${supp.normalized_line_item_subtotal.toFixed(2)}{" "}
                    <span className="text-xs font-normal text-muted-foreground">{reference_currency}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {t('matrix.quotedOriginal')}{" "}
                    <span className="font-mono font-medium text-foreground">
                      {supp.quoted_grand_total.toFixed(2)} {supp.original_currency}
                    </span>
                  </div>
                </td>
              ))}
            </tr>

            {/* Comparable Grand Total */}
            <tr className="border-b border-border/40 hover:bg-secondary/10 transition-colors">
              <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80">
                <div className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <Scale className="h-3.5 w-3.5 text-blue-400" />
                  {t('matrix.comparableTotal')}
                </div>
                <div className="text-[10px] text-muted-foreground">{t('matrix.comparableTotalDesc')}</div>
              </td>
              {suppliers.map((supp) => (
                <td key={supp.quotation_id} className="p-3 border-r border-border/60">
                  {supp.normalized_comparable_total !== null && supp.normalized_comparable_total !== undefined ? (
                    <div className="font-mono text-base font-bold text-emerald-400">
                      ${supp.normalized_comparable_total.toFixed(2)}{" "}
                      <span className="text-xs font-normal text-muted-foreground">{reference_currency}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[11px] text-amber-400">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      <span>
                        {supp.rfq_coverage_pct < 100
                          ? t('matrix.withheldIncomplete')
                          : supp.has_unknown_commercial_components
                          ? t('matrix.withheldExtra')
                          : t('matrix.withheldUnresolved')}
                      </span>
                    </div>
                  )}
                </td>
              ))}
            </tr>

            {/* Payment Terms Row */}
            <tr className="border-b border-border/40 hover:bg-secondary/10 transition-colors">
              <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80">
                <div className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <CreditCard className="h-3.5 w-3.5 text-purple-400" />
                  {t('matrix.paymentTerms')}
                </div>
                <div className="text-[10px] text-muted-foreground">{t('matrix.paymentTermsDesc')}</div>
              </td>
              {suppliers.map((supp) => (
                <td key={supp.quotation_id} className="p-3 border-r border-border/60 space-y-1">
                  <span className="inline-block rounded bg-purple-500/10 px-2 py-0.5 text-xs font-semibold text-purple-300 border border-purple-500/20">
                    {supp.payment_terms_normalized}
                  </span>
                  {supp.payment_terms_original && supp.payment_terms_original !== supp.payment_terms_normalized && (
                    <div className="text-[10px] text-muted-foreground truncate" title={supp.payment_terms_original}>
                      {t('matrix.quotedValue', { value: supp.payment_terms_original })}
                    </div>
                  )}
                </td>
              ))}
            </tr>

            {/* Overall Lead Time Row */}
            <tr className="border-b-2 border-border/80 hover:bg-secondary/10 transition-colors">
              <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80">
                <div className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-amber-400" />
                  {t('matrix.overallDeliveryLeadTime')}
                </div>
                <div className="text-[10px] text-muted-foreground">{t('matrix.overallDeliveryLeadTimeDesc')}</div>
              </td>
              {suppliers.map((supp) => (
                <td key={supp.quotation_id} className="p-3 border-r border-border/60 space-y-1">
                  <span className="inline-block rounded bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300 border border-amber-500/20">
                    {supp.overall_lead_time_normalized}
                  </span>
                  {supp.overall_lead_time_original && supp.overall_lead_time_original !== supp.overall_lead_time_normalized && (
                    <div className="text-[10px] text-muted-foreground truncate" title={supp.overall_lead_time_original}>
                      {t('matrix.quotedValue', { value: supp.overall_lead_time_original })}
                    </div>
                  )}
                </td>
              ))}
            </tr>

            {/* Section Header: Required Items */}
            <tr className="bg-secondary/40 border-b border-border/80 font-bold text-white text-xs">
              <td colSpan={suppliers.length + 1} className="p-3">
                <div className="flex items-center gap-2">
                  <Package className="h-4 w-4 text-blue-400" />
                  <span>{t('matrix.requiredRfqLineItems', { count: required_line_items.length })}</span>
                </div>
              </td>
            </tr>

            {/* Required Line Items Data Rows */}
            {required_line_items.map((row) => (
              <tr key={row.rfq_line_item_id} className="border-b border-border/40 hover:bg-secondary/15 transition-colors">
                {/* Sticky Left: RFQ Line Item Specification */}
                <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3.5 border-r border-border/80 space-y-1">
                  <div className="flex items-start gap-2">
                    <span className="font-mono text-xs font-bold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                      #{row.position}
                    </span>
                    <div>
                      <div className="font-bold text-foreground text-xs leading-snug">{row.description}</div>
                      <div className="text-[11px] text-muted-foreground mt-0.5 font-mono">
                        <Trans
                          i18nKey="matrix.requiredQuantity"
                          values={{ qty: row.required_quantity, unit: row.required_unit }}
                          components={{ 1: <strong className="text-foreground" /> }}
                        />
                      </div>
                    </div>
                  </div>
                </td>

                {/* Supplier Cells */}
                {suppliers.map((supp) => {
                  const cell = row.supplier_cells[supp.quotation_id];
                  if (!cell || !cell.is_quoted) {
                    return (
                      <td
                        key={supp.quotation_id}
                        className={`p-3.5 border-r border-border/60 ${
                          highlightMissing ? "bg-red-500/10" : ""
                        }`}
                      >
                        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-2.5 text-center space-y-1">
                          <span className="text-[11px] font-bold text-red-400 block">{t('matrix.notQuoted')}</span>
                          <span className="text-[10px] text-muted-foreground">{t('matrix.itemMissingQuotation')}</span>
                        </div>
                      </td>
                    );
                  }

                  const hasWarnings = cell.warnings.length > 0;
                  const isUnresolved = cell.overall_cell_status === "unresolved";

                  return (
                    <td
                      key={supp.quotation_id}
                      onClick={() => onSelectCell(cell, row, supp)}
                      className={`p-3.5 border-r border-border/60 cursor-pointer hover:bg-blue-500/10 transition-colors group relative ${
                        highlightWarnings && (hasWarnings || isUnresolved)
                          ? "bg-amber-500/10"
                          : ""
                      }`}
                    >
                      <div className="space-y-1.5">
                        {/* Primary Normalized Unit Price & Extended Price */}
                        <div className="flex items-baseline justify-between">
                          <div className="font-mono text-sm font-bold text-white group-hover:text-blue-300 transition-colors">
                            {cell.normalized_unit_price !== null && cell.normalized_unit_price !== undefined
                              ? `$${cell.normalized_unit_price.toFixed(4)}`
                              : t('matrix.unresolved')}
                          </div>
                          {cell.normalized_extended_price !== null && cell.normalized_extended_price !== undefined && (
                            <span className="font-mono text-xs font-semibold text-blue-400">
                              {t('matrix.extPrice', { amount: formatCurrency(cell.normalized_extended_price, reference_currency) })}
                            </span>
                          )}
                        </div>

                        {/* Secondary Original Quoted Info */}
                        <div className="text-[11px] text-muted-foreground flex items-center justify-between font-mono">
                          <span>
                            {formatCurrency(cell.quoted_unit_price, cell.original_currency)} / {cell.quoted_unit}
                          </span>
                          <span>(Qty: {cell.quoted_quantity})</span>
                        </div>

                        {/* Badges Bar */}
                        <div className="flex flex-wrap items-center gap-1 pt-0.5">
                          {cell.original_currency !== reference_currency && cell.fx_rate_used && (
                            <span className="rounded bg-secondary/80 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border">
                              FX: {formatNumber(cell.fx_rate_used, { maximumFractionDigits: 4 })}
                            </span>
                          )}

                          {cell.quoted_unit !== row.required_unit && cell.canonical_unit && (
                            <span className="rounded bg-secondary/80 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border">
                              UOM: {cell.canonical_unit}
                            </span>
                          )}

                          {cell.is_human_overridden && (
                            <span className="rounded bg-purple-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-purple-300 border border-purple-500/30">
                              {t('matrix.overrideBadge')}
                            </span>
                          )}

                          {cell.line_lead_time_display && (
                            <span className="rounded bg-secondary/80 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
                              {cell.line_lead_time_display}
                            </span>
                          )}

                          {hasWarnings && (
                            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30 flex items-center gap-0.5">
                              <AlertTriangle className="h-3 w-3" /> {t('matrix.warningBadge')}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}

            {/* Extra Unmapped Items Section */}
            {showExtraItems && extra_line_items.length > 0 && (
              <>
                <tr className="bg-secondary/40 border-b border-border/80 font-bold text-white text-xs">
                  <td colSpan={suppliers.length + 1} className="p-3">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4 text-purple-400" />
                      <span>{t('matrix.extraUnmappedItems', { count: extra_line_items.length })}</span>
                    </div>
                  </td>
                </tr>

                {extra_line_items.map((extra) => (
                  <tr key={extra.line_item_id} className="border-b border-border/40 hover:bg-secondary/15 transition-colors">
                    <td className="sticky left-0 z-10 bg-card/95 backdrop-blur-md p-3 border-r border-border/80">
                      <div className="font-semibold text-foreground text-xs">{extra.description_raw}</div>
                      <div className="text-[10px] text-muted-foreground">{t('matrix.unmappedSupplierOffering')}</div>
                    </td>
                    {suppliers.map((supp) => {
                      if (supp.quotation_id === extra.quotation_id) {
                        return (
                          <td key={supp.quotation_id} className="p-3 border-r border-border/60">
                            <div className="font-mono text-xs font-bold text-white">
                              {formatCurrency(extra.total_price, extra.currency)}
                            </div>
                            <div className="text-[11px] text-muted-foreground font-mono">
                              {extra.quantity} {extra.unit} @ {formatCurrency(extra.unit_price, extra.currency)}
                            </div>
                          </td>
                        );
                      }
                      return (
                        <td key={supp.quotation_id} className="p-3 border-r border-border/60 text-muted-foreground font-mono text-[11px]">
                          —
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
