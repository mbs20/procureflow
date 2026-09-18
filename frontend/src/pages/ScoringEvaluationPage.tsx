import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  fetchActiveScoringConfiguration,
  createScoringConfiguration,
  fetchScoringRuns,
  createScoringRun,
  simulateScoring,
  runSensitivityAnalysis,
  ScoringConfigurationResponse,
  ScoringRunResponse,
  SupplierScore,
  CriterionConfig,
  SensitivityResponse,
  BreakevenResult,
} from "../api/scoring";
import {
  listComparisonSnapshots,
  ComparisonSnapshotRead,
} from "../api/matrix";
import { RFQ, fetchRFQs, PaginatedRFQs } from "../api/rfq";
import { useTranslation } from "react-i18next";
import { translateBackendError } from "../lib/errorMessageMap";
import { EvaluationRankTable } from "../components/scoring/EvaluationRankTable";
import { ScoreAuditDrawer } from "../components/scoring/ScoreAuditDrawer";
import { CriteriaWeightSliders } from "../components/scoring/CriteriaWeightSliders";
import { SensitivitySweepChart } from "../components/scoring/SensitivitySweepChart";
import { BreakevenCalculatorCard } from "../components/scoring/BreakevenCalculatorCard";
import { ScoringRunsModal } from "../components/scoring/ScoringRunsModal";
import {
  Sliders,
  TrendingUp,
  Calculator,
  History,
  Camera,
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  ChevronDown,
} from "lucide-react";

export const ScoringEvaluationPage: React.FC = () => {
  const { t } = useTranslation();
  const { id: routeRfqId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // RFQ state
  const [rfqList, setRfqList] = useState<RFQ[]>([]);
  const [selectedRfqId, setSelectedRfqId] = useState<string>(routeRfqId || "");

  // Snapshots & Config state
  const [snapshots, setSnapshots] = useState<ComparisonSnapshotRead[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>("");
  const [activeConfig, setActiveConfig] = useState<ScoringConfigurationResponse | null>(null);
  const [scoringRuns, setScoringRuns] = useState<ScoringRunResponse[]>([]);
  const [selectedRun, setSelectedRun] = useState<ScoringRunResponse | null>(null);

  // Active displayed evaluation scores
  const [displayedScores, setDisplayedScores] = useState<SupplierScore[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Tab & Drawer state
  const [activeTab, setActiveTab] = useState<"weights" | "sensitivity" | "breakeven">("weights");
  const [auditSupplier, setAuditSupplier] = useState<SupplierScore | null>(null);
  const [isRunsModalOpen, setIsRunsModalOpen] = useState(false);

  // Sensitivity & Breakeven state
  const [selectedSweepCriterion, setSelectedSweepCriterion] = useState<string>("Commercial Price");
  const [sensitivityResult, setSensitivityResult] = useState<SensitivityResponse | null>(null);
  const [isSensitivityLoading, setIsSensitivityLoading] = useState(false);
  const [breakevenResult, setBreakevenResult] = useState<BreakevenResult | null>(null);
  const [isBreakevenLoading, setIsBreakevenLoading] = useState(false);

  // Load RFQs for dropdown
  useEffect(() => {
    fetchRFQs({ page: 1, page_size: 50 })
      .then((data: PaginatedRFQs) => {
        setRfqList(data.items);
        if (!selectedRfqId && data.items.length > 0) {
          setSelectedRfqId(data.items[0].id);
        }
      })
      .catch((err) => setErrorMessage(translateBackendError(err, t)))
      .finally(() => setIsLoading(false));
  }, []);

  // Update selected RFQ if route param changes
  useEffect(() => {
    if (routeRfqId && routeRfqId !== selectedRfqId) {
      setSelectedRfqId(routeRfqId);
    }
  }, [routeRfqId]);

  // Load RFQ scoring data when RFQ changes
  const loadRFQData = async (rfqId: string) => {
    if (!rfqId) return;
    setIsLoading(true);
    setErrorMessage(null);
    setActiveConfig(null);
    setDisplayedScores([]);
    setSelectedRun(null);
    setScoringRuns([]);
    setSnapshots([]);
    setSensitivityResult(null);
    setBreakevenResult(null);

    try {
      // 1. Fetch snapshots
      const snaps = await listComparisonSnapshots(rfqId);
      setSnapshots(snaps);

      const targetSnapId = snaps.length > 0 ? snaps[0].id : "";
      setSelectedSnapshotId(targetSnapId);

      // 2. Fetch Active Scoring Configuration (or create default if none)
      const cfg = await fetchActiveScoringConfiguration(rfqId);
      setActiveConfig(cfg);

      // 3. Fetch Historical Scoring Runs
      const runs = await fetchScoringRuns(rfqId);
      setScoringRuns(runs);

      if (runs.length > 0) {
        // Display the most recent frozen run by default
        const latestRun = runs[0];
        setSelectedRun(latestRun);
        setDisplayedScores(latestRun.scores);
        setSelectedSnapshotId(latestRun.comparison_snapshot_id);
      } else if (targetSnapId && cfg) {
        // Simulate live in-memory scores if no frozen runs exist yet
        const simRes = await simulateScoring(rfqId, {
          comparison_snapshot_id: targetSnapId,
          transient_criteria: cfg.criteria,
        });
        setDisplayedScores(simRes.scores);
      }
    } catch (err: any) {
      setErrorMessage(translateBackendError(err, t));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedRfqId) {
      loadRFQData(selectedRfqId);
    }
  }, [selectedRfqId]);

  const handleRFQChange = (newRfqId: string) => {
    setSelectedRfqId(newRfqId);
    navigate(`/rfqs/${newRfqId}/scoring`);
  };

  const handleSnapshotChange = async (newSnapId: string) => {
    setSelectedSnapshotId(newSnapId);
    setSelectedRun(null); // Return to transient simulation mode
    if (activeConfig) {
      setIsSimulating(true);
      try {
        const simRes = await simulateScoring(selectedRfqId, {
          comparison_snapshot_id: newSnapId,
          transient_criteria: activeConfig.criteria,
        });
        setDisplayedScores(simRes.scores);
      } catch (err: any) {
        setErrorMessage(translateBackendError(err, t));
      } finally {
        setIsSimulating(false);
      }
    }
  };

  // Interactive in-memory weight simulation
  const handleSimulateWeights = async (newCriteria: CriterionConfig[]) => {
    if (!selectedRfqId || !selectedSnapshotId) return;
    setIsSimulating(true);
    setErrorMessage(null);
    try {
      const simRes = await simulateScoring(selectedRfqId, {
        comparison_snapshot_id: selectedSnapshotId,
        transient_criteria: newCriteria,
      });
      setDisplayedScores(simRes.scores);
      setSelectedRun(null); // Clear selected frozen run indicator
    } catch (err: any) {
      setErrorMessage(translateBackendError(err, t));
    } finally {
      setIsSimulating(false);
    }
  };

  // Save new version of Scoring Configuration
  const handleSaveNewConfigVersion = async (
    criteria: CriterionConfig[],
    name: string
  ) => {
    if (!selectedRfqId || !selectedSnapshotId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const newCfg = await createScoringConfiguration(selectedRfqId, {
        name,
        criteria,
      });
      setActiveConfig(newCfg);
      // Re-simulate with new criteria
      const simRes = await simulateScoring(selectedRfqId, {
        comparison_snapshot_id: selectedSnapshotId,
        transient_criteria: newCfg.criteria,
      });
      setDisplayedScores(simRes.scores);
      setSelectedRun(null);
    } catch (err: any) {
      setErrorMessage(translateBackendError(err, t));
    } finally {
      setIsLoading(false);
    }
  };

  // Execute and freeze new scoring run
  const handleExecuteRun = async (snapshotId: string, notes?: string) => {
    if (!selectedRfqId || !activeConfig) return;
    try {
      const newRun = await createScoringRun(selectedRfqId, {
        scoring_configuration_id: activeConfig.id,
        comparison_snapshot_id: snapshotId,
        notes,
      });
      setScoringRuns((prev) => [newRun, ...prev]);
      setSelectedRun(newRun);
      setDisplayedScores(newRun.scores);
    } catch (err: any) {
      throw err;
    }
  };

  // Load a frozen historical run
  const handleSelectHistoricalRun = (run: ScoringRunResponse) => {
    setSelectedRun(run);
    setDisplayedScores(run.scores);
    setSelectedSnapshotId(run.comparison_snapshot_id);
  };

  // Run sensitivity sweep
  const handleRunSensitivity = async (criterionName: string) => {
    if (!selectedRfqId || !selectedSnapshotId) return;
    setIsSensitivityLoading(true);
    try {
      const res = await runSensitivityAnalysis(selectedRfqId, {
        comparison_snapshot_id: selectedSnapshotId,
        scoring_configuration_id: activeConfig?.id,
        sweep_criterion: criterionName,
        min_weight: 0.0,
        max_weight: 0.9,
        step: 0.05,
      });
      setSensitivityResult(res);
    } catch (err: any) {
      setErrorMessage(translateBackendError(err, t));
    } finally {
      setIsSensitivityLoading(false);
    }
  };

  // Run breakeven search
  const handleCalculateBreakeven = async (targetSupplierId: string) => {
    if (!selectedRfqId || !selectedSnapshotId) return;
    setIsBreakevenLoading(true);
    try {
      const res = await runSensitivityAnalysis(selectedRfqId, {
        comparison_snapshot_id: selectedSnapshotId,
        scoring_configuration_id: activeConfig?.id,
        sweep_criterion: activeConfig?.criteria.find(c => c.source_field === "normalized_comparable_total")?.criterion_id || "Commercial Price",
        target_supplier_id: targetSupplierId,
      });
      if (res.breakeven) {
        setBreakevenResult(res.breakeven);
      }
    } catch (err: any) {
      setErrorMessage(translateBackendError(err, t));
    } finally {
      setIsBreakevenLoading(false);
    }
  };

  // Automatically trigger sensitivity when switching to sensitivity tab if empty
  useEffect(() => {
    if (activeTab === "sensitivity" && !sensitivityResult && activeConfig) {
      const firstCrit = activeConfig.criteria[0]?.criterion_id || activeConfig.criteria[0]?.name || "Commercial Price";
      setSelectedSweepCriterion(firstCrit);
      handleRunSensitivity(firstCrit);
    }
  }, [activeTab]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              to={`/rfqs/${selectedRfqId}/matrix`}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-white transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> {t('scoring.backToMatrix')}
            </Link>
            <span className="text-muted-foreground">•</span>
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-wider">
              {t('scoring.phase5Badge')}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Sliders className="h-6 w-6 text-primary" />
            {t('scoring.title')}
          </h1>
          <p className="text-xs text-muted-foreground max-w-2xl">
            {t('scoring.subtitle')}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* RFQ Selector */}
          <div className="relative">
            <select
              value={selectedRfqId}
              onChange={(e) => handleRFQChange(e.target.value)}
              aria-label={t('scoring.selectRfqAria')}
              className="appearance-none rounded-xl border border-border bg-secondary/50 px-3.5 py-2 pr-8 text-xs font-semibold text-foreground focus:outline-none focus:border-primary cursor-pointer"
            >
              {rfqList.map((rfq) => (
                <option key={rfq.id} value={rfq.id} className="bg-card text-foreground">
                  {rfq.title} ({rfq.reference_currency})
                </option>
              ))}
            </select>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground absolute right-2.5 top-3 pointer-events-none" />
          </div>

          {/* Snapshot Selector */}
          <div className="relative">
            <select
              value={selectedSnapshotId}
              onChange={(e) => handleSnapshotChange(e.target.value)}
              aria-label={t('scoring.selectSnapshotAria')}
              className="appearance-none rounded-xl border border-border bg-secondary/50 px-3.5 py-2 pr-8 text-xs font-semibold text-foreground focus:outline-none focus:border-primary cursor-pointer"
            >
              {snapshots.map((s) => (
                <option key={s.id} value={s.id} className="bg-card text-foreground">
                  {t('scoring.snapshotOption', {
                    version: s.snapshot_version,
                    title: s.title || t('scoring.frozenMatrix')
                  })}
                </option>
              ))}
            </select>
            <Camera className="h-3.5 w-3.5 text-purple-400 absolute right-2.5 top-3 pointer-events-none" />
          </div>

          {/* Historical Runs Button */}
          <button
            onClick={() => setIsRunsModalOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors"
          >
            <History className="h-3.5 w-3.5 text-blue-400" />
            {t('scoring.historicalRuns', { count: scoringRuns.length })}
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => selectedRfqId && loadRFQData(selectedRfqId)}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/40 text-muted-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
            title={t('scoring.refreshTitle')}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading || isSimulating ? "animate-spin text-primary" : ""}`} />
          </button>
        </div>
      </div>

      {/* State & Provenance Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="glass-card rounded-xl p-3.5 border border-border/80 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-bold text-muted-foreground">{t('scoring.scoringConfigCard')}</div>
            <div className="text-sm font-bold text-foreground">
              {activeConfig ? `${activeConfig.name} (v${activeConfig.version})` : t(isLoading ? "common.loading" : "stabilization.noConfiguration")}
            </div>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            {activeConfig ? t('scoring.activeBadge') : t('stabilization.notReady')}
          </span>
        </div>

        <div className="glass-card rounded-xl p-3.5 border border-border/80 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-bold text-muted-foreground">{t('scoring.evaluationSourceCard')}</div>
            <div className="text-sm font-bold text-foreground">
              {snapshots.find((s) => s.id === selectedSnapshotId)
                ? `Snapshot v${snapshots.find((s) => s.id === selectedSnapshotId)?.snapshot_version}`
                : t('scoring.frozenMatrix')}
            </div>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
            {t('scoring.immutableBadge')}
          </span>
        </div>

        <div className="glass-card rounded-xl p-3.5 border border-border/80 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-bold text-muted-foreground">{t('scoring.executionStatusCard')}</div>
            <div className="text-sm font-bold text-foreground">
              {selectedRun ? t('scoring.frozenRunPrefix', { id: selectedRun.id.slice(0, 8) }) : t('scoring.liveSimulation')}
            </div>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-mono ${
              selectedRun
                ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
          >
            {selectedRun ? t('scoring.auditableRun') : t('scoring.transientBadge')}
          </span>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/40 text-xs text-red-300 flex items-center gap-2.5">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {!isLoading && !selectedSnapshotId && <div role="status" className="rounded-xl border p-4"><p>{t('stabilization.noSnapshot')}</p><Link className="text-primary underline" to={`/rfqs/${selectedRfqId}/matrix`}>{t('stabilization.createSnapshot')}</Link></div>}
      {!isLoading && selectedSnapshotId && !activeConfig && !errorMessage && <div role="status" className="rounded-xl border p-4"><p>{t('stabilization.noConfiguration')}</p><button onClick={() => handleSaveNewConfigVersion([{criterion_id:'price',name:t('stabilization.price'),weight:1,direction:'MINIMIZE',source_type:'price',source_field:'normalized_comparable_total'}], t('stabilization.priceModel'))} className="text-primary underline">{t('stabilization.createConfiguration')}</button></div>}
      {/* Main Ranking Table */}
      <div className="space-y-2">
        <EvaluationRankTable
          scores={displayedScores}
          onSelectSupplier={(s) => setAuditSupplier(s)}
        />
      </div>

      {/* Advanced Analysis Tabs Navigation */}
      <div className="pt-2">
        <div className="flex border-b border-border/70 space-x-2">
          <button
            onClick={() => setActiveTab("weights")}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
              activeTab === "weights"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sliders className="h-4 w-4" />
            {t('scoring.tabWeights')}
          </button>

          <button
            onClick={() => setActiveTab("sensitivity")}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
              activeTab === "sensitivity"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <TrendingUp className="h-4 w-4" />
            {t('scoring.tabSensitivity')}
          </button>

          <button
            onClick={() => setActiveTab("breakeven")}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
              activeTab === "breakeven"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Calculator className="h-4 w-4" />
            {t('scoring.tabBreakeven')}
          </button>
        </div>

        {/* Tab 1: Weights Editor & Simulator */}
        {activeTab === "weights" && activeConfig && selectedSnapshotId && (
          <div className="pt-4">
            <CriteriaWeightSliders
              initialCriteria={activeConfig.criteria}
              activeConfig={activeConfig}
              onSimulate={handleSimulateWeights}
              onSaveNewVersion={handleSaveNewConfigVersion}
              isSimulating={isSimulating}
            />
          </div>
        )}

        {/* Tab 2: Sensitivity Sweep */}
        {activeTab === "sensitivity" && activeConfig && selectedSnapshotId && (
          <div className="pt-4 space-y-4">
            <div className="flex items-center gap-3 glass-card rounded-xl p-4 border border-border/70">
              <label htmlFor="sensitivity-sweep-criterion-select" className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                {t('scoring.criterionToSweep')}
              </label>
              <select
                id="sensitivity-sweep-criterion-select"
                value={selectedSweepCriterion}
                onChange={(e) => {
                  setSelectedSweepCriterion(e.target.value);
                  handleRunSensitivity(e.target.value);
                }}
                className="rounded-xl border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground focus:outline-none focus:border-primary cursor-pointer"
              >
                {activeConfig.criteria.map((c) => (
                  <option key={c.criterion_id || c.name} value={c.criterion_id || c.name}>
                    {c.name} (Direction: {c.direction})
                  </option>
                ))}
              </select>

              <button
                onClick={() => handleRunSensitivity(selectedSweepCriterion)}
                disabled={isSensitivityLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-secondary text-xs font-semibold text-foreground hover:bg-secondary/80 hover:text-white transition-colors"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isSensitivityLoading ? "animate-spin" : ""}`} />
                {t('scoring.recomputeSweep')}
              </button>
            </div>

            <SensitivitySweepChart
              sensitivityData={sensitivityResult}
              isLoading={isSensitivityLoading}
            />
          </div>
        )}

        {/* Tab 3: Breakeven Calculator */}
        {activeTab === "breakeven" && activeConfig && selectedSnapshotId && (
          <div className="pt-4">
            <BreakevenCalculatorCard
              scores={displayedScores}
              onCalculateBreakeven={handleCalculateBreakeven}
              breakevenResult={breakevenResult}
              isLoading={isBreakevenLoading}
            />
          </div>
        )}
      </div>

      {/* Slide-out Score Audit Drawer */}
      <ScoreAuditDrawer
        isOpen={!!auditSupplier}
        onClose={() => setAuditSupplier(null)}
        supplierScore={auditSupplier}
        snapshotVersion={snapshots.find((s) => s.id === selectedSnapshotId)?.snapshot_version}
        configVersion={activeConfig?.version}
      />

      {/* Historical Runs Modal */}
      <ScoringRunsModal
        isOpen={isRunsModalOpen}
        onClose={() => setIsRunsModalOpen(false)}
        runs={scoringRuns}
        activeConfig={activeConfig}
        snapshots={snapshots}
        selectedSnapshotId={selectedSnapshotId}
        onExecuteRun={handleExecuteRun}
        onSelectRun={handleSelectHistoricalRun}
        selectedRunId={selectedRun?.id}
      />
    </div>
  );
};
