import React, { useState } from "react";
import { ScoringRunResponse, ScoringConfigurationResponse } from "../../api/scoring";
import { ComparisonSnapshotRead } from "../../api/matrix";
import { X, History, CheckCircle2, Play, Hash, Calendar } from "lucide-react";

interface ScoringRunsModalProps {
  isOpen: boolean;
  onClose: () => void;
  runs: ScoringRunResponse[];
  activeConfig: ScoringConfigurationResponse | null;
  snapshots: ComparisonSnapshotRead[];
  selectedSnapshotId: string;
  onExecuteRun: (snapshotId: string, notes?: string) => Promise<void>;
  onSelectRun: (run: ScoringRunResponse) => void;
  selectedRunId?: string | null;
}

export const ScoringRunsModal: React.FC<ScoringRunsModalProps> = ({
  isOpen,
  onClose,
  runs,
  activeConfig,
  snapshots,
  selectedSnapshotId,
  onExecuteRun,
  onSelectRun,
  selectedRunId,
}) => {
  const [snapshotToRun, setSnapshotToRun] = useState<string>(selectedSnapshotId || (snapshots[0]?.id || ""));
  const [notes, setNotes] = useState<string>("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCreateRun = async () => {
    if (!snapshotToRun) {
      setErrorMsg("Please select a frozen comparison snapshot to evaluate");
      return;
    }
    setErrorMsg(null);
    setIsExecuting(true);
    try {
      await onExecuteRun(snapshotToRun, notes);
      setNotes("");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute scoring run");
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="scoring-runs-modal-title"
    >
      <div className="w-full max-w-3xl rounded-2xl bg-card border border-border shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-6 border-b border-border/80 flex items-center justify-between bg-card/50">
          <div>
            <h2 id="scoring-runs-modal-title" className="text-xl font-bold text-white flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Historical Scoring Runs & Executions
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Append-only audit trail binding immutable ComparisonSnapshots to versioned ScoringConfigurations.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted-foreground hover:text-white hover:bg-secondary/80 transition-colors"
            aria-label="Close scoring runs modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Create New Scoring Run Form */}
          <div className="glass-card rounded-xl p-5 space-y-4 border border-border/80 bg-secondary/20">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Play className="h-4 w-4 text-emerald-400" />
              Execute New Scoring Run
            </h3>

            {errorMsg && (
              <div className="p-3 rounded-lg bg-red-950/30 border border-red-800/40 text-xs text-red-300">
                {errorMsg}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground mb-1 block">
                  Target Comparison Snapshot
                </label>
                <select
                  value={snapshotToRun}
                  onChange={(e) => setSnapshotToRun(e.target.value)}
                  className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground focus:outline-none focus:border-primary"
                >
                  {snapshots.map((s) => (
                    <option key={s.id} value={s.id}>
                      v{s.snapshot_version} ({s.title || "Frozen Matrix Snapshot"})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground mb-1 block">
                  Active Scoring Configuration
                </label>
                <div className="rounded-xl border border-border bg-card/60 px-3.5 py-2 text-xs font-semibold text-foreground flex items-center justify-between">
                  <span>{activeConfig ? `${activeConfig.name} (v${activeConfig.version})` : "No active config"}</span>
                  <span className="text-[10px] text-emerald-400 uppercase font-mono">Active</span>
                </div>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1 block">Run Notes (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Formal Phase 5 baseline evaluation run"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex justify-end pt-1">
              <button
                onClick={handleCreateRun}
                disabled={isExecuting || !activeConfig}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md shadow-primary/20 disabled:opacity-50"
              >
                <Play className={`h-3.5 w-3.5 ${isExecuting ? "animate-spin" : ""}`} />
                {isExecuting ? "Executing & Freezing Run..." : "Execute & Freeze Scoring Run"}
              </button>
            </div>
          </div>

          {/* Historical Runs List */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Frozen Evaluation Runs ({runs.length})
            </h3>

            {runs.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted-foreground glass-card rounded-xl">
                No scoring runs executed yet. Select a snapshot and execute a run above.
              </div>
            ) : (
              <div className="space-y-2.5">
                {runs.map((r) => {
                  const isSelected = selectedRunId === r.id;
                  const dateStr = new Date(r.created_at).toLocaleString();

                  return (
                    <div
                      key={r.id}
                      className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isSelected
                          ? "bg-primary/10 border-primary shadow-sm"
                          : "bg-secondary/20 border-border/70 hover:border-border hover:bg-secondary/30"
                      }`}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-sm">
                            Run #{r.id.slice(0, 8)}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-secondary text-muted-foreground font-mono">
                            Config v{r.scoring_configuration_version} • Snapshot v{r.comparison_snapshot_version}
                          </span>
                          {isSelected && (
                            <span className="text-[10px] uppercase font-bold text-primary flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" /> Active View
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" /> {dateStr}
                          </span>
                          {r.comparison_snapshot_hash && (
                            <span className="flex items-center gap-1" title={r.comparison_snapshot_hash}>
                              <Hash className="h-3 w-3" /> {r.comparison_snapshot_hash.slice(0, 10)}...
                            </span>
                          )}
                        </div>

                        {r.notes && (
                          <div className="text-xs text-foreground/80 italic">"{r.notes}"</div>
                        )}
                      </div>

                      <div>
                        <button
                          onClick={() => {
                            onSelectRun(r);
                            onClose();
                          }}
                          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "border border-border bg-secondary/50 text-foreground hover:bg-secondary hover:text-white"
                          }`}
                        >
                          {isSelected ? "Currently Viewing" : "Load Frozen View"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-border/80 bg-card/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-secondary text-sm font-semibold text-foreground hover:bg-secondary/80 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
