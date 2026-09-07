import React, { useState } from "react";
import { X, Coins, CheckCircle2, AlertTriangle, Plus, Trash2 } from "lucide-react";
import { RFQFXRateSetRead, updateRFQFXRates } from "../../api/matrix";

interface FXRateConfigModalProps {
  rfqId: string;
  currentRateSet?: RFQFXRateSetRead | null;
  onClose: () => void;
  onSaved: () => void;
}

export const FXRateConfigModal: React.FC<FXRateConfigModalProps> = ({
  rfqId,
  currentRateSet,
  onClose,
  onSaved,
}) => {
  const baseCurrency = currentRateSet?.base_currency || "USD";
  const [rates, setRates] = useState<Array<{ currency: string; rate: string }>>(() => {
    if (currentRateSet?.rates) {
      return Object.entries(currentRateSet.rates).map(([curr, rate]) => ({
        currency: curr,
        rate: rate.toString(),
      }));
    }
    return [
      { currency: "EUR", rate: "1.0850" },
      { currency: "MAD", rate: "0.1000" },
      { currency: "GBP", rate: "1.2800" },
    ];
  });

  const [providerId, setProviderId] = useState<string>(
    currentRateSet?.provider_id || "rfq_custom_rates"
  );
  const [effectiveDate, setEffectiveDate] = useState<string>(
    currentRateSet?.effective_date || new Date().toISOString().split("T")[0]
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleRateChange = (index: number, field: "currency" | "rate", value: string) => {
    const updated = [...rates];
    updated[index][field] = value;
    setRates(updated);
  };

  const handleAddRate = () => {
    setRates([...rates, { currency: "", rate: "" }]);
  };

  const handleRemoveRate = (index: number) => {
    setRates(rates.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const ratesMap: Record<string, number> = {
      [baseCurrency]: 1.0,
    };

    for (const r of rates) {
      const code = r.currency.trim().toUpperCase();
      const val = parseFloat(r.rate);
      if (!code || isNaN(val) || val <= 0) {
        setError(`Invalid currency rate entry for '${r.currency}'`);
        setSubmitting(false);
        return;
      }
      ratesMap[code] = val;
    }

    try {
      await updateRFQFXRates(rfqId, {
        base_currency: baseCurrency,
        effective_date: effectiveDate,
        provider_id: providerId,
        is_synthetic: false,
        rates: ratesMap,
      });

      setSuccessMsg("New FX rate set version saved successfully.");
      onSaved();
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || "Failed to update FX rates");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-2xl bg-card border border-border shadow-2xl p-6 space-y-5">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Coins className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Configure RFQ Exchange Rates</h2>
              <p className="text-xs text-muted-foreground">
                Base Reference Currency: <strong className="text-foreground">{baseCurrency}</strong> • Current Version: v{currentRateSet?.version || 1}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-white hover:bg-secondary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Notices */}
        {currentRateSet?.is_synthetic && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <strong>Synthetic Test Rates Active:</strong> The current rate set uses synthetic demo data. Configuring a new version will save authoritative project rates.
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-muted-foreground block mb-1">Effective Date</label>
              <input
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs text-foreground focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-muted-foreground block mb-1">Provider / Rate Source ID</label>
              <input
                type="text"
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
                placeholder="e.g. committee_frozen_rates"
                className="w-full rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs text-foreground focus:outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-white">Currency Conversion Rates</label>
              <button
                type="button"
                onClick={handleAddRate}
                className="inline-flex items-center gap-1 rounded bg-secondary px-2 py-1 text-[11px] font-semibold text-foreground hover:text-white transition-colors"
              >
                <Plus className="h-3 w-3" /> Add Currency
              </button>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {rates.map((r, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground font-mono">1</span>
                  <input
                    type="text"
                    maxLength={3}
                    value={r.currency}
                    onChange={(e) => handleRateChange(idx, "currency", e.target.value.toUpperCase())}
                    placeholder="EUR"
                    className="w-20 rounded-lg border border-border bg-secondary/40 px-3 py-1.5 text-xs text-foreground uppercase font-mono font-bold focus:outline-none focus:border-blue-500"
                    required
                  />
                  <span className="text-xs text-muted-foreground font-mono">=</span>
                  <input
                    type="number"
                    step="any"
                    value={r.rate}
                    onChange={(e) => handleRateChange(idx, "rate", e.target.value)}
                    placeholder="1.0850"
                    className="flex-1 rounded-lg border border-border bg-secondary/40 px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:border-blue-500"
                    required
                  />
                  <span className="text-xs font-mono font-semibold text-muted-foreground">{baseCurrency}</span>
                  {rates.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveRate(idx)}
                      className="p-1.5 text-muted-foreground hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg bg-secondary/30 p-3 text-[11px] text-muted-foreground">
            Saving creates version <strong>v{(currentRateSet?.version || 1) + 1}</strong> of the RFQ rate set. Historical comparison snapshots will remain frozen to their respective versions.
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border bg-secondary/40 px-4 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-primary px-4 py-2 text-xs font-bold text-white hover:bg-blue-600 transition-colors shadow-md shadow-blue-500/20 disabled:opacity-50"
            >
              {submitting ? "Saving Version..." : "Save New Rate Set Version"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
