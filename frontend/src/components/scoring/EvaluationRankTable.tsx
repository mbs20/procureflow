import React from "react";
import { useTranslation } from "react-i18next";
import { SupplierScore } from "../../api/scoring";
import { CheckCircle2, ShieldAlert, FileText } from "lucide-react";
import { formatNumber } from "../../lib/formatters";

interface EvaluationRankTableProps {
  scores: SupplierScore[];
  onSelectSupplier: (supplier: SupplierScore) => void;
}

export const EvaluationRankTable: React.FC<EvaluationRankTableProps> = ({
  scores,
  onSelectSupplier,
}) => {
  const { t } = useTranslation();
  // Sort scores by rank ascending, placing unranked/ineligible at bottom
  const sortedScores = [...scores].sort((a, b) => {
    if (a.rank !== null && a.rank !== undefined && b.rank !== null && b.rank !== undefined) {
      return a.rank - b.rank;
    }
    if (a.rank !== null && a.rank !== undefined) return -1;
    if (b.rank !== null && b.rank !== undefined) return 1;
    return b.composite_score - a.composite_score;
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            {t('scoring.rankingTableTitle')}
          </h2>
          <p className="text-xs text-muted-foreground">
            {t('scoring.rankingTableSubtitle')}
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-secondary text-muted-foreground border border-border">
          {t('scoring.standardRankingBadge')}
        </span>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card/40 backdrop-blur-sm shadow-xl">
        <table className="w-full text-left border-collapse" role="table" aria-label={t('scoring.tableAria')}>
          <thead>
            <tr className="border-b border-border/80 bg-secondary/30 text-[11px] uppercase font-bold tracking-wider text-muted-foreground">
              <th scope="col" className="py-3.5 px-4 w-16 text-center">{t('scoring.rankHeader')}</th>
              <th scope="col" className="py-3.5 px-4">{t('scoring.supplierHeader')}</th>
              <th scope="col" className="py-3.5 px-4">{t('scoring.eligibilityStatusHeader')}</th>
              <th scope="col" className="py-3.5 px-4 text-right">{t('scoring.compositeScoreHeader')}</th>
              <th scope="col" className="py-3.5 px-4">{t('scoring.criteriaContributionsHeader')}</th>
              <th scope="col" className="py-3.5 px-4 text-center w-28">{t('scoring.auditHeader')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40 text-sm">
            {sortedScores.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-muted-foreground text-sm">
                  {t('scoring.noSuppliersEvaluated')}
                </td>
              </tr>
            ) : (
              sortedScores.map((s) => {
                const isIneligible = !s.is_eligible;

                return (
                  <tr
                    key={s.quotation_id}
                    className={`transition-colors hover:bg-secondary/40 cursor-pointer ${
                      isIneligible ? "bg-red-950/10 opacity-80" : ""
                    }`}
                    onClick={() => onSelectSupplier(s)}
                  >
                    {/* Rank */}
                    <td className="py-4 px-4 text-center">
                      {s.rank ? (
                        <span
                          className={`inline-flex items-center justify-center h-8 w-8 rounded-lg font-mono font-bold text-sm ${
                            s.rank === 1
                              ? "bg-primary/20 text-primary border border-primary/40 shadow-sm"
                              : "bg-secondary text-muted-foreground border border-border"
                          }`}
                        >
                          #{s.rank}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground font-mono">—</span>
                      )}
                    </td>

                    {/* Supplier Name */}
                    <td className="py-4 px-4">
                      <div className="font-semibold text-foreground text-sm">{s.supplier_name}</div>
                      <div className="text-[11px] text-muted-foreground font-mono truncate max-w-xs">
                        ID: {s.quotation_id.slice(0, 8)}...
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-4 px-4">
                      {s.is_eligible ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="h-3 w-3" />
                          {t('scoring.eligible')}
                        </span>
                      ) : (
                        <div className="space-y-1">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                            <ShieldAlert className="h-3 w-3" />
                            {s.status === "knockout_failed" ? t('scoring.knockoutFailed') : t('scoring.ineligible')}
                          </span>
                          {s.knockout_reasons && s.knockout_reasons.length > 0 && (
                            <div className="text-[11px] text-red-300 font-mono">
                              {s.knockout_reasons.join(", ")}
                            </div>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Composite Score */}
                    <td className="py-4 px-4 text-right">
                      <div className="font-mono font-extrabold text-base text-foreground">
                        {formatNumber(s.composite_score, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <span className="text-xs font-normal text-muted-foreground ml-1">/ 100</span>
                      </div>
                    </td>

                    {/* Criteria Contributions */}
                    <td className="py-4 px-4">
                      <div className="flex flex-wrap gap-1.5 max-w-md">
                        {Object.entries(s.breakdown).map(([cName, b]) => (
                          <span
                            key={cName}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-secondary/70 border border-border/50 text-[11px] font-mono text-muted-foreground"
                            title={`${cName}: ${b.normalized_score.toFixed(1)}/100 (weighted contribution: +${b.weighted_contribution.toFixed(2)})`}
                          >
                            <span className="text-foreground">{cName}:</span>
                            <span className="text-blue-400 font-semibold">
                              {formatNumber(b.weighted_contribution, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                            </span>
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* Audit Button */}
                    <td className="py-4 px-4 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectSupplier(s);
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border bg-secondary/50 text-xs font-medium text-foreground hover:bg-secondary hover:text-white transition-colors"
                        aria-label={t('scoring.inspectAuditAria', { name: s.supplier_name })}
                      >
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        {t('scoring.auditBtn')}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
