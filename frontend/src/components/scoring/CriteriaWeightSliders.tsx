import React, { useState, useEffect } from "react";
import { CriterionConfig, ScoringConfigurationResponse } from "../../api/scoring";
import { Lock, Unlock, Sliders, Save, Play, RotateCcw, AlertCircle, CheckCircle2 } from "lucide-react";

interface CriteriaWeightSlidersProps {
  initialCriteria: CriterionConfig[];
  activeConfig: ScoringConfigurationResponse | null;
  onSimulate: (criteria: CriterionConfig[]) => void;
  onSaveNewVersion: (criteria: CriterionConfig[], name: string) => Promise<void>;
  isSimulating?: boolean;
}

export const CriteriaWeightSliders: React.FC<CriteriaWeightSlidersProps> = ({
  initialCriteria,
  activeConfig,
  onSimulate,
  onSaveNewVersion,
  isSimulating = false,
}) => {
  const [criteria, setCriteria] = useState<CriterionConfig[]>(initialCriteria);
  const [lockedCriteria, setLockedCriteria] = useState<Record<string, boolean>>({});
  const [configName, setConfigName] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    setCriteria(initialCriteria);
    if (activeConfig) {
      setConfigName(`${activeConfig.name} (v${activeConfig.version + 1})`);
    }
  }, [initialCriteria, activeConfig]);

  // Sum of weights (in percent)
  const totalWeightPct = criteria.reduce((sum, c) => sum + (c.weight * 100), 0);
  const isBalanced = Math.abs(totalWeightPct - 100.0) < 0.01;

  // Toggle locked status for a criterion
  const toggleLock = (criterionName: string) => {
    setLockedCriteria((prev) => ({
      ...prev,
      [criterionName]: !prev[criterionName],
    }));
  };

  // Proportional weight adjustment maintaining sum = 1.0 (100%)
  const handleWeightChange = (changedIndex: number, newWeightPct: number) => {
    const targetCriterion = criteria[changedIndex];
    const newWeight = Math.max(0, Math.min(100, newWeightPct)) / 100;

    // Calculate sum of locked criteria (excluding the target even if locked)
    let lockedSum = 0;
    const otherUnlockedIndices: number[] = [];

    criteria.forEach((c, idx) => {
      if (idx === changedIndex) return;
      if (lockedCriteria[c.name]) {
        lockedSum += c.weight;
      } else {
        otherUnlockedIndices.push(idx);
      }
    });

    // Cannot exceed 1.0 - lockedSum
    const maxAllowedWeight = Math.max(0, 1.0 - lockedSum);
    const clampedNewWeight = Math.min(newWeight, maxAllowedWeight);

    const remainingToDistribute = 1.0 - lockedSum - clampedNewWeight;
    const currentUnlockedSum = otherUnlockedIndices.reduce(
      (sum, idx) => sum + criteria[idx].weight,
      0
    );

    const nextCriteria = [...criteria];
    nextCriteria[changedIndex] = { ...targetCriterion, weight: clampedNewWeight };

    if (otherUnlockedIndices.length > 0) {
      if (currentUnlockedSum > 0.00001) {
        otherUnlockedIndices.forEach((idx) => {
          const proportion = criteria[idx].weight / currentUnlockedSum;
          nextCriteria[idx] = {
            ...criteria[idx],
            weight: remainingToDistribute * proportion,
          };
        });
      } else {
        // Equal split among other unlocked
        const equalShare = remainingToDistribute / otherUnlockedIndices.length;
        otherUnlockedIndices.forEach((idx) => {
          nextCriteria[idx] = { ...criteria[idx], weight: equalShare };
        });
      }
    }

    setCriteria(nextCriteria);
  };

  const handleReset = () => {
    setCriteria(initialCriteria);
    setLockedCriteria({});
  };

  const handleSave = async () => {
    if (!isBalanced) {
      setErrorMsg("Total weights must sum to exactly 100.0%");
      return;
    }
    setErrorMsg(null);
    setIsSaving(true);
    try {
      await onSaveNewVersion(criteria, configName || "Custom Scoring Model");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="glass-card rounded-xl p-5 space-y-5 border border-border/80">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="h-4 w-4 text-primary" />
            Criteria Weights & Proportional Balancing
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Adjust weights in real time. Unlocked criteria automatically redistribute to maintain 100% total.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold ${
              isBalanced
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}
          >
            {isBalanced ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
            <span>Total: {totalWeightPct.toFixed(1)}%</span>
          </div>

          <button
            onClick={handleReset}
            className="p-1.5 rounded-lg border border-border bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title="Reset weights to original active configuration"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-red-950/30 border border-red-800/40 text-xs text-red-300 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Sliders Grid */}
      <div className="space-y-4">
        {criteria.map((c, index) => {
          const isLocked = !!lockedCriteria[c.name];
          const weightPct = Number((c.weight * 100).toFixed(1));

          return (
            <div
              key={c.name}
              className={`p-3.5 rounded-xl border transition-all ${
                isLocked
                  ? "bg-secondary/40 border-primary/40 shadow-sm"
                  : "bg-secondary/20 border-border/60 hover:border-border"
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleLock(c.name)}
                    className={`p-1.5 rounded-md border text-xs transition-colors ${
                      isLocked
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
                    }`}
                    title={isLocked ? "Unlock criterion weight" : "Lock criterion weight"}
                    aria-label={isLocked ? `Unlock weight for ${c.name}` : `Lock weight for ${c.name}`}
                  >
                    {isLocked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                  </button>
                  <div>
                    <span className="font-semibold text-sm text-foreground">{c.name}</span>
                    <span className="text-[11px] text-muted-foreground ml-2 font-mono">
                      ({c.direction.toLowerCase()}, {c.source_field})
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={1}
                    value={weightPct}
                    disabled={isLocked}
                    onChange={(e) => handleWeightChange(index, parseFloat(e.target.value) || 0)}
                    aria-label={`Weight percentage for ${c.name}`}
                    className="w-16 rounded-md border border-border bg-card px-2 py-1 text-right text-xs font-mono font-bold text-foreground focus:outline-none focus:border-primary disabled:opacity-50"
                  />
                  <span className="text-xs font-mono text-muted-foreground">%</span>
                </div>
              </div>

              {/* Slider Input */}
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={0.5}
                  value={weightPct}
                  disabled={isLocked}
                  onChange={(e) => handleWeightChange(index, parseFloat(e.target.value))}
                  aria-label={`Weight percentage slider for ${c.name}`}
                  className="w-full h-1.5 bg-secondary/80 rounded-lg appearance-none cursor-pointer accent-primary disabled:cursor-not-allowed"
                />
              </div>

              {/* Knockout condition / Categorical map details */}
              {(c.knockout_condition || c.categorical_map) && (
                <div className="mt-2.5 pt-2 border-t border-border/40 flex flex-wrap gap-2 text-[11px] font-mono text-muted-foreground">
                  {c.knockout_condition && (
                    <span className="text-amber-400/90">
                      Knockout: {c.knockout_condition} {c.knockout_threshold}
                    </span>
                  )}
                  {c.categorical_map && (
                    <span className="text-blue-300">
                      Categorical map: {Object.entries(c.categorical_map).map(([k, v]) => `${k}=${v}`).join(", ")}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Action Footer */}
      <div className="pt-3 border-t border-border/60 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Configuration title (e.g., Cost-Prioritized Model)"
            value={configName}
            onChange={(e) => setConfigName(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary w-64"
          />
        </div>

        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={() => onSimulate(criteria)}
            disabled={isSimulating}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-border bg-secondary/70 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors"
          >
            <Play className={`h-3.5 w-3.5 text-blue-400 ${isSimulating ? "animate-spin" : ""}`} />
            Simulate Weights
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving || !isBalanced}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md shadow-primary/20 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            {isSaving ? "Saving..." : "Save As New Version"}
          </button>
        </div>
      </div>
    </div>
  );
};
