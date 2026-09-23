import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  fetchRFQs,
  fetchRFQ,
  RFQ,
  PaginatedRFQs,
} from "../api/rfq";
import {
  fetchScoringRuns,
  ScoringRunResponse,
} from "../api/scoring";
import {
  generateNarrative,
  listNarratives,
  getCurrentAward,
  listAwards,
  NarrativeGenerationResponse,
  AwardDecisionResponse,
  NarrativeType,
} from "../api/decision";
import { NarrativeCard } from "../components/decision/NarrativeCard";
import { AwardConfirmationModal } from "../components/decision/AwardConfirmationModal";
import { DecisionTimeline } from "../components/decision/DecisionTimeline";
import { formatDate } from "../lib/formatters";
import { translateRFQStatus } from "../lib/statusTranslations";
import {
  Award,
  Sparkles,
  ArrowLeft,
  ChevronDown,
  RefreshCw,
  AlertCircle,
  FileCheck,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";

export const DecisionWorkspacePage: React.FC = () => {
  const { t } = useTranslation();
  const { id: routeRfqId } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [selectedRfqId, setSelectedRfqId] = useState<string>(routeRfqId || "");
  const [rfq, setRfq] = useState<RFQ | null>(null);

  const [scoringRuns, setScoringRuns] = useState<ScoringRunResponse[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");

  const [narratives, setNarratives] = useState<NarrativeGenerationResponse[]>([]);
  const [selectedNarrativeId, setSelectedNarrativeId] = useState<string>("");

  const [currentAward, setCurrentAward] = useState<AwardDecisionResponse | null>(null);
  const [allAwards, setAllAwards] = useState<AwardDecisionResponse[]>([]);

  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generate Narrative form state
  const [narrativeType, setNarrativeType] = useState<NarrativeType>("decision_support_memo");
  const [humanNote, setHumanNote] = useState("");
  const [includeSensitivity, setIncludeSensitivity] = useState(false);

  // Award modal
  const [showAwardModal, setShowAwardModal] = useState(false);

  // Load RFQ options
  useEffect(() => {
    fetchRFQs().then((res: PaginatedRFQs) => {
      setRfqs(res.items);
      if (!selectedRfqId && res.items.length > 0) {
        setSelectedRfqId(res.items[0].id);
      }
    });
  }, []);

  // When selectedRfqId changes
  useEffect(() => {
    if (!selectedRfqId) return;
    loadWorkspace(selectedRfqId);
  }, [selectedRfqId]);

  const loadWorkspace = async (rfqId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [rfqData, runs, narrs, activeAward, awards] = await Promise.all([
        fetchRFQ(rfqId),
        fetchScoringRuns(rfqId),
        listNarratives(rfqId),
        getCurrentAward(rfqId),
        listAwards(rfqId),
      ]);

      setRfq(rfqData);
      setScoringRuns(runs);
      if (runs.length > 0) {
        setSelectedRunId(runs[0].id);
      } else {
        setSelectedRunId("");
      }

      setNarratives(narrs);
      if (narrs.length > 0) {
        setSelectedNarrativeId(narrs[0].id);
      } else {
        setSelectedNarrativeId("");
      }

      setCurrentAward(activeAward);
      setAllAwards(awards);
    } catch (err: any) {
      setError(err.message || t("decision.loadError"));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNarrative = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRfqId || !selectedRunId) return;

    setGenerating(true);
    setError(null);
    try {
      const gen = await generateNarrative(selectedRfqId, {
        scoring_run_id: selectedRunId,
        narrative_type: narrativeType,
        include_sensitivity: includeSensitivity,
        human_unverified_note: humanNote.trim() || undefined,
      });

      // Refresh narratives
      const updated = await listNarratives(selectedRfqId);
      setNarratives(updated);
      setSelectedNarrativeId(gen.id);
      setHumanNote("");
    } catch (err: any) {
      setError(err.message || t("decision.generateError"));
    } finally {
      setGenerating(false);
    }
  };

  const selectedRun = scoringRuns.find((r) => r.id === selectedRunId);
  const selectedNarrative = narratives.find((n) => n.id === selectedNarrativeId);

  // Extract suppliers for award modal
  const runSuppliers = selectedRun?.scores || [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/80 pb-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link to="/rfqs" className="hover:text-foreground flex items-center gap-1 transition">
              <ArrowLeft className="w-3.5 h-3.5" /> {t("decision.backToRfqs")}
            </Link>
            <span>/</span>
            <span className="text-foreground">{t("decision.decisionsAndAwardBreadcrumb")}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            {t("decision.title")}
          </h1>
          <p className="text-xs text-muted-foreground">
            {t("decision.subtitle")}
          </p>
        </div>

        {/* RFQ Selector */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              aria-label={t("decision.selectRfq")}
              value={selectedRfqId}
              onChange={(e) => {
                setSelectedRfqId(e.target.value);
                navigate(`/rfqs/${e.target.value}/decisions`);
              }}
              className="appearance-none bg-slate-900 border border-border/80 rounded-xl px-4 py-2 pr-10 text-xs text-white font-medium focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer"
            >
              {rfqs.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.title} ({translateRFQStatus(q.status, t)})
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 text-muted-foreground absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <button
            onClick={() => selectedRfqId && loadWorkspace(selectedRfqId)}
            disabled={loading}
            className="p-2 rounded-xl bg-secondary hover:bg-secondary/80 text-muted-foreground hover:text-white border border-border/60 transition"
            title={t("decision.refreshWorkspace")}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Current Award Status Banner */}
      {currentAward ? (
        <div className="glass-card rounded-2xl p-6 border border-emerald-500/40 bg-emerald-950/20 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                <FileCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    {t("decision.officialAwardedSupplier")}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {t("decision.rfqStatusLabel", { status: rfq ? translateRFQStatus(rfq.status, t) : "" })}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white mt-0.5">
                  {currentAward.awarded_supplier_name}
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[11px] text-muted-foreground block">{t("decision.evaluationRank")}</span>
                <span className="text-lg font-bold text-primary">
                  {t("scoring.rankCol")} #{currentAward.awarded_supplier_rank ?? "1"}
                </span>
              </div>
            </div>
          </div>

          {!currentAward.is_based_on_latest_run && (
            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-xs text-amber-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                {t("decision.newerRunWarning")}
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card rounded-2xl p-6 border border-border/80 flex flex-wrap items-center justify-between gap-4 bg-secondary/20">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              {t("decision.humanDecisionPending")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t(selectedRun ? "decision.humanDecisionPendingDesc" : "decision.scoringRequiredBeforeDecision")}
            </p>
          </div>

          <button
            onClick={() => setShowAwardModal(true)}
            disabled={!selectedRun || runSuppliers.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-bold text-xs shadow-lg shadow-amber-500/20 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Award className="w-4 h-4" />
            {t("decision.draftAndConfirmAwardBtn")}
          </button>
        </div>
      )}

      {/* Main Grid: Narrative Generation Panel & Active Narrative */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Generator Controls & List */}
        <div className="space-y-6">
          {/* Generator Card */}
          <div className="glass-card rounded-xl border border-border/80 p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-border/60 pb-3">
              <Sparkles className="w-4 h-4 text-primary" />
              <h2 className="font-bold text-sm text-white">{t("decision.generateNarrativeTitle")}</h2>
            </div>

            {scoringRuns.length === 0 ? (
              <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 space-y-2">
                <p>{t("decision.noScoringRunsYet")}</p>
                <Link
                  to={`/rfqs/${selectedRfqId}/scoring`}
                  className="inline-block text-primary hover:underline font-semibold"
                >
                  {t("decision.goToScoringLink")}
                </Link>
              </div>
            ) : (
              <form onSubmit={handleGenerateNarrative} className="space-y-3.5 text-xs">
                {/* Scoring Run Selection */}
                <div className="space-y-1">
                  <label htmlFor="scoringRunSelect" className="text-muted-foreground font-medium block">
                    {t("decision.authoritativeRun")}
                  </label>
                  <select
                    id="scoringRunSelect"
                    aria-label={t("decision.authoritativeRun")}
                    value={selectedRunId}
                    onChange={(e) => setSelectedRunId(e.target.value)}
                    className="w-full bg-slate-900 border border-border rounded-lg p-2 text-white font-mono focus:ring-1 focus:ring-primary focus:outline-none"
                  >
                    {scoringRuns.map((r) => (
                      <option key={r.id} value={r.id}>
                        Run #{r.run_number} — {r.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Narrative Type */}
                <div className="space-y-1">
                  <label htmlFor="narrativeTypeSelect" className="text-muted-foreground font-medium block">
                    {t("decision.memoTypeLabel")}
                  </label>
                  <select
                    id="narrativeTypeSelect"
                    aria-label={t("decision.memoTypeLabel")}
                    value={narrativeType}
                    onChange={(e) => setNarrativeType(e.target.value as NarrativeType)}
                    className="w-full bg-slate-900 border border-border rounded-lg p-2 text-white capitalize focus:ring-1 focus:ring-primary focus:outline-none"
                  >
                    <option value="decision_support_memo">{t("decision.typeDecisionMemo")}</option>
                    <option value="comparison_summary">{t("decision.typeComparisonSummary")}</option>
                    <option value="tradeoff_analysis">{t("decision.typeTradeoff")}</option>
                    <option value="decision_considerations">{t("decision.typeDecisionConsiderations")}</option>
                    <option value="sensitivity_summary">{t("decision.typeSensitivitySummary")}</option>
                  </select>
                </div>

                {/* Unverified Human Note */}
                <div className="space-y-1">
                  <label className="text-muted-foreground font-medium block">
                    {t("decision.humanGuidanceLabel")}
                  </label>
                  <textarea
                    rows={2}
                    value={humanNote}
                    onChange={(e) => setHumanNote(e.target.value)}
                    placeholder={t("decision.humanGuidancePlaceholder")}
                    className="w-full bg-slate-900 border border-border rounded-lg p-2 text-white focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>

                {/* Include Sensitivity Toggle */}
                <div className="flex items-center gap-2 pt-1 select-none">
                  <input
                    type="checkbox"
                    id="sensToggle"
                    checked={includeSensitivity}
                    onChange={(e) => setIncludeSensitivity(e.target.checked)}
                    className="rounded border-border bg-slate-900 text-primary focus:ring-0"
                  />
                  <label htmlFor="sensToggle" className="text-muted-foreground cursor-pointer">
                    {t("decision.includeSensitivityLabel")}
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={generating || !selectedRunId}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-xs transition disabled:opacity-50"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {generating ? t("decision.generatingMemoBtn") : t("decision.generateMemoBtn")}
                </button>
              </form>
            )}
          </div>

          {/* Historical Narratives List */}
          <div className="glass-card rounded-xl border border-border/80 p-5 space-y-3">
            <h2 className="font-bold text-xs uppercase tracking-wider text-muted-foreground">
              {t("decision.narrativeGenerationsCount", { count: narratives.length })}
            </h2>
            {narratives.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">{t("decision.noNarrativesYet")}</p>
            ) : (
              <div className="space-y-2">
                {narratives.map((n) => {
                  const isSelected = n.id === selectedNarrativeId;
                  return (
                    <div
                      key={n.id}
                      onClick={() => setSelectedNarrativeId(n.id)}
                      className={`cursor-pointer p-3 rounded-lg border text-xs transition ${
                        isSelected
                          ? "bg-primary/20 border-primary text-white"
                          : "bg-secondary/20 border-border/60 text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <strong className="capitalize text-white">
                          {n.narrative_type.replace(/_/g, " ")}
                        </strong>
                        <span className="text-[10px] font-mono opacity-80">
                          #{n.generation_number}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] mt-1 text-muted-foreground">
                        <span>{formatDate(n.generated_at)}</span>
                        <span>{t("decision.claimsCount", { count: n.claims.length })}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Selected Narrative Card & Decision Timeline */}
        <div className="lg:col-span-2 space-y-8">
          {selectedNarrative ? (
            <NarrativeCard
              narrative={selectedNarrative}
              rfqId={selectedRfqId}
              onRevisionSaved={() => selectedRfqId && loadWorkspace(selectedRfqId)}
            />
          ) : (
            <div className="glass-card rounded-xl border border-border/80 p-12 text-center text-muted-foreground text-xs space-y-2">
              <Sparkles className="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
              <p className="font-semibold text-foreground">{t("decision.noNarrativeSelected")}</p>
              <p>{t("decision.noNarrativeSelectedDesc")}</p>
            </div>
          )}

          {/* Decision Timeline if awards exist */}
          {allAwards.map((award) => (
            <DecisionTimeline
              key={award.id}
              award={award}
              rfqId={selectedRfqId}
              onAwardRevoked={() => selectedRfqId && loadWorkspace(selectedRfqId)}
            />
          ))}
        </div>
      </div>

      {/* Award Confirmation Modal */}
      {showAwardModal && selectedRun && (
        <AwardConfirmationModal
          rfqId={selectedRfqId}
          scoringRunId={selectedRun.id}
          scoringRunProvenanceHash={selectedRun.provenance_hash}
          suppliers={runSuppliers.map((s) => ({
            quotation_id: s.quotation_id,
            supplier_name: s.supplier_name,
            rank: s.rank,
            total_score: s.exact_total_score || s.composite_score,
            eligibility_status: s.status,
          }))}
          onClose={() => setShowAwardModal(false)}
          onAwardConfirmed={(confirmed: AwardDecisionResponse) => {
            setCurrentAward(confirmed);
            if (selectedRfqId) loadWorkspace(selectedRfqId);
          }}
        />
      )}
    </div>
  );
};
