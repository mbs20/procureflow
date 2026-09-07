import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Scale,
  RefreshCw,
  Coins,
  Camera,
  Download,
  AlertCircle,
  Filter,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";
import {
  ComparisonMatrixResponse,
  MatrixLineItemCell,
  MatrixRequiredRow,
  MatrixSupplierHeader,
  fetchComparisonMatrix,
} from "../api/matrix";
import { RFQ, fetchRFQs, PaginatedRFQs } from "../api/rfq";
import { ComparisonTable } from "../components/matrix/ComparisonTable";
import { CellTraceabilityDrawer } from "../components/matrix/CellTraceabilityDrawer";
import { FXRateConfigModal } from "../components/matrix/FXRateConfigModal";
import { SnapshotsModal } from "../components/matrix/SnapshotsModal";

export const ComparisonMatrixPage: React.FC = () => {
  const { id: routeRfqId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [rfqList, setRfqList] = useState<RFQ[]>([]);
  const [selectedRfqId, setSelectedRfqId] = useState<string>(routeRfqId || "");
  const [matrix, setMatrix] = useState<ComparisonMatrixResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Drawers state
  const [isFXModalOpen, setIsFXModalOpen] = useState(false);
  const [isSnapshotsModalOpen, setIsSnapshotsModalOpen] = useState(false);
  const [selectedCellInfo, setSelectedCellInfo] = useState<{
    cell: MatrixLineItemCell;
    row: MatrixRequiredRow;
    supplier: MatrixSupplierHeader;
  } | null>(null);

  // Filters
  const [highlightMissing, setHighlightMissing] = useState(true);
  const [highlightWarnings, setHighlightWarnings] = useState(true);
  const [showExtraItems, setShowExtraItems] = useState(true);

  // Load RFQs for dropdown
  useEffect(() => {
    fetchRFQs({ page: 1, page_size: 50 }).then((data: PaginatedRFQs) => {
      setRfqList(data.items);
      if (!selectedRfqId && data.items.length > 0) {
        setSelectedRfqId(data.items[0].id);
      }
    }).catch((err: unknown) => console.error("Failed to load RFQs", err));
  }, []);

  // Update selected RFQ if route param changes
  useEffect(() => {
    if (routeRfqId && routeRfqId !== selectedRfqId) {
      setSelectedRfqId(routeRfqId);
    }
  }, [routeRfqId]);

  // Load comparison matrix when selected RFQ changes
  const loadMatrix = async (rfqId: string) => {
    if (!rfqId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchComparisonMatrix(rfqId);
      setMatrix(data);
    } catch (err: any) {
      setError(err.message || "Failed to load comparison matrix");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedRfqId) {
      loadMatrix(selectedRfqId);
    }
  }, [selectedRfqId]);

  const handleRFQChange = (newRfqId: string) => {
    setSelectedRfqId(newRfqId);
    navigate(`/rfqs/${newRfqId}/matrix`);
  };

  const handleExportCSV = () => {
    if (!matrix) return;
    const rows = [
      ["Requirement Position", "Description", "Required Qty", "Required Unit", ...matrix.suppliers.map(s => s.supplier_name)],
    ];

    for (const r of matrix.required_line_items) {
      const rowData = [
        r.position.toString(),
        `"${r.description}"`,
        r.required_quantity.toString(),
        r.required_unit,
        ...matrix.suppliers.map(s => {
          const cell = r.supplier_cells[s.quotation_id];
          return cell?.is_quoted && cell.normalized_unit_price !== null && cell.normalized_unit_price !== undefined
            ? cell.normalized_unit_price.toString()
            : "NOT_QUOTED";
        }),
      ];
      rows.push(rowData);
    }

    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `comparison_matrix_${matrix.rfq_id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header & RFQ Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-lg shadow-blue-500/10">
            <Scale className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Normalized Comparison Matrix</h1>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                Phase 4 Leveling
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Apples-to-apples commercial & technical comparison with strict data provenance.
            </p>
          </div>
        </div>

        {/* RFQ Selector & Top Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* RFQ Dropdown */}
          <div className="relative">
            <select
              value={selectedRfqId}
              onChange={(e) => handleRFQChange(e.target.value)}
              aria-label="Select RFQ to compare"
              className="appearance-none rounded-xl border border-border bg-secondary/50 px-3.5 py-2 pr-8 text-xs font-semibold text-foreground focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              {rfqList.map((rfq) => (
                <option key={rfq.id} value={rfq.id} className="bg-card text-foreground">
                  {rfq.title} ({rfq.reference_currency})
                </option>
              ))}
            </select>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground absolute right-2.5 top-3 pointer-events-none" />
          </div>

          <button
            onClick={() => setIsFXModalOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors"
          >
            <Coins className="h-3.5 w-3.5 text-emerald-400" />
            FX Rates (v{matrix?.fx_rate_set?.version || 1})
          </button>

          <button
            onClick={() => setIsSnapshotsModalOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors"
          >
            <Camera className="h-3.5 w-3.5 text-purple-400" />
            Snapshots ({matrix?.snapshots_count || 0})
          </button>

          <button
            onClick={handleExportCSV}
            disabled={!matrix || matrix.suppliers.length === 0}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </button>

          <button
            onClick={() => selectedRfqId && loadMatrix(selectedRfqId)}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/40 text-muted-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
            title="Refresh Matrix"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Metrics Summary Strip */}
      {matrix && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="glass-card rounded-xl p-4 space-y-1">
            <div className="text-[10px] uppercase font-bold text-muted-foreground">Suppliers Compared</div>
            <div className="text-xl font-mono font-bold text-white">{matrix.suppliers.length} Approved Quotations</div>
          </div>

          <div className="glass-card rounded-xl p-4 space-y-1">
            <div className="text-[10px] uppercase font-bold text-muted-foreground">Reference Currency</div>
            <div className="text-xl font-mono font-bold text-blue-400">
              {matrix.reference_currency}{" "}
              <span className="text-xs font-normal text-muted-foreground">
                ({matrix.fx_rate_set?.is_synthetic ? "Synthetic FX" : "Authoritative FX"})
              </span>
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 space-y-1">
            <div className="text-[10px] uppercase font-bold text-muted-foreground">Human Overrides</div>
            <div className="text-xl font-mono font-bold text-purple-400">
              {matrix.active_overrides_count} Active
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 space-y-1">
            <div className="text-[10px] uppercase font-bold text-muted-foreground">Engine Integrity</div>
            <div className="text-xl font-mono font-bold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> Deterministic v{matrix.normalization_engine_version}
            </div>
          </div>
        </div>
      )}

      {/* Filter / Quality Bar */}
      <div className="glass-card rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-muted-foreground font-semibold">
          <Filter className="h-4 w-4 text-blue-400" />
          <span>Matrix Display Filters:</span>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer text-foreground">
            <input
              type="checkbox"
              checked={highlightMissing}
              onChange={(e) => setHighlightMissing(e.target.checked)}
              className="rounded border-border bg-secondary accent-blue-500 h-3.5 w-3.5"
            />
            <span>Highlight Missing / Not Quoted</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-foreground">
            <input
              type="checkbox"
              checked={highlightWarnings}
              onChange={(e) => setHighlightWarnings(e.target.checked)}
              className="rounded border-border bg-secondary accent-blue-500 h-3.5 w-3.5"
            />
            <span>Highlight Warnings & Discrepancies</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-foreground">
            <input
              type="checkbox"
              checked={showExtraItems}
              onChange={(e) => setShowExtraItems(e.target.checked)}
              className="rounded border-border bg-secondary accent-blue-500 h-3.5 w-3.5"
            />
            <span>Show Extra Unmapped Items</span>
          </label>
        </div>
      </div>

      {/* Main Table or Loading / Error State */}
      {loading ? (
        <div className="flex items-center justify-center p-24 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-400" />
        </div>
      ) : error ? (
        <div className="glass-card rounded-2xl p-12 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Failed to Compile Matrix</h2>
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
      ) : matrix ? (
        <ComparisonTable
          matrix={matrix}
          highlightMissing={highlightMissing}
          highlightWarnings={highlightWarnings}
          showExtraItems={showExtraItems}
          onSelectCell={(cell, row, supplier) => setSelectedCellInfo({ cell, row, supplier })}
        />
      ) : null}

      {/* Traceability Drawer */}
      {selectedCellInfo && matrix && (
        <CellTraceabilityDrawer
          rfqId={matrix.rfq_id}
          referenceCurrency={matrix.reference_currency}
          cell={selectedCellInfo.cell}
          row={selectedCellInfo.row}
          supplier={selectedCellInfo.supplier}
          onClose={() => setSelectedCellInfo(null)}
          onRefresh={() => loadMatrix(selectedRfqId)}
        />
      )}

      {/* FX Rate Config Modal */}
      {isFXModalOpen && (
        <FXRateConfigModal
          rfqId={selectedRfqId}
          currentRateSet={matrix?.fx_rate_set}
          onClose={() => setIsFXModalOpen(false)}
          onSaved={() => loadMatrix(selectedRfqId)}
        />
      )}

      {/* Snapshots Modal */}
      {isSnapshotsModalOpen && (
        <SnapshotsModal
          rfqId={selectedRfqId}
          onClose={() => setIsSnapshotsModalOpen(false)}
          onSnapshotCreated={() => loadMatrix(selectedRfqId)}
        />
      )}
    </div>
  );
};
