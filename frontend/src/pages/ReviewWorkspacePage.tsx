import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  History,
  FileText,
  Plus,
  Edit2,
  Trash2,
  RotateCcw,
  Eye,
} from "lucide-react";
import {
  SupplierQuotation,
  ExtractedQuotation,
  ExtractedLineItem,
  ExtractionValidationStatus,
  AuditLogEntry,
  fetchQuotation,
  fetchLatestExtraction,
  fetchValidationStatus,
  fetchAuditLogs,
  downloadQuotationDocumentBlob,
  createLineItem,
  correctLineItem,
  softDeleteLineItem,
  restoreLineItem,
  approveExtraction,
  rejectExtraction,
} from "../api/quotation";
import { RFQ, fetchRFQ } from "../api/rfq";
import { PDFViewer } from "../components/review/PDFViewer";
import { SpreadsheetViewer } from "../components/review/SpreadsheetViewer";
import { ValidationAlertCenter } from "../components/review/ValidationAlertCenter";
import { LineItemEditDialog } from "../components/review/LineItemEditDialog";
import { LineItemAddDialog } from "../components/review/LineItemAddDialog";
import { ExtractionDecisionModal } from "../components/review/ExtractionDecisionModal";
import { AuditHistoryDrawer } from "../components/review/AuditHistoryDrawer";

export const ReviewWorkspacePage: React.FC = () => {
  const { id: quotationId } = useParams<{ id: string }>();

  const [quotation, setQuotation] = useState<SupplierQuotation | null>(null);
  const [rfq, setRfq] = useState<RFQ | null>(null);
  const [extraction, setExtraction] = useState<ExtractedQuotation | null>(null);
  const [validationStatus, setValidationStatus] = useState<ExtractionValidationStatus | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  // Document Blob state for viewer
  const [documentBlob, setDocumentBlob] = useState<Blob | null>(null);
  const [activeDocFilename, setActiveDocFilename] = useState<string>("");
  const [activeDocMime, setActiveDocMime] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");

  // Evidence focus
  const [activeEvidence, setActiveEvidence] = useState<any | null>(null);
  const [selectedLineItemId, setSelectedLineItemId] = useState<string | null>(null);

  // Filter & layout state
  const [filterMode, setFilterMode] = useState<"all" | "attention" | "excluded">("all");
  const [splitRatio, setSplitRatio] = useState<number>(50); // 50% left / 50% right
  const [isDraggingDivider, setIsDraggingDivider] = useState<boolean>(false);

  // Dialog states
  const [editingItem, setEditingItem] = useState<ExtractedLineItem | null>(null);
  const [showAddDialog, setShowAddDialog] = useState<boolean>(false);
  const [decisionModalType, setDecisionModalType] = useState<"approve" | "reject" | null>(null);
  const [showAuditDrawer, setShowAuditDrawer] = useState<boolean>(false);

  // Loading & error
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Initial Data Loading
  const loadAllData = useCallback(async () => {
    if (!quotationId) return;
    try {
      setLoading(true);
      setError(null);

      const quoteData = await fetchQuotation(quotationId);
      setQuotation(quoteData);

      if (quoteData.rfq_id) {
        const rfqData = await fetchRFQ(quoteData.rfq_id).catch(() => null);
        setRfq(rfqData);
      }

      // Fetch extraction, validation status, and audit logs
      const [extData, valData, logsData] = await Promise.all([
        fetchLatestExtraction(quotationId).catch(() => null),
        fetchValidationStatus(quotationId).catch(() => null),
        fetchAuditLogs(quotationId).catch(() => []),
      ]);

      setExtraction(extData);
      setValidationStatus(valData);
      setAuditLogs(logsData);

      // Select and download first document if available
      if (quoteData.documents && quoteData.documents.length > 0) {
        const docToLoad = quoteData.documents[0];
        setSelectedDocId(docToLoad.id);
        setActiveDocFilename(docToLoad.filename);
        setActiveDocMime(docToLoad.mime_type);

        const { blob } = await downloadQuotationDocumentBlob(quotationId, docToLoad.id);
        setDocumentBlob(blob);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load quotation review workspace");
    } finally {
      setLoading(false);
    }
  }, [quotationId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Handle document switching
  const handleSwitchDocument = async (docId: string) => {
    if (!quotation || !quotationId) return;
    const doc = quotation.documents.find((d) => d.id === docId);
    if (!doc) return;
    try {
      setSelectedDocId(doc.id);
      setActiveDocFilename(doc.filename);
      setActiveDocMime(doc.mime_type);
      const { blob } = await downloadQuotationDocumentBlob(quotationId, doc.id);
      setDocumentBlob(blob);
    } catch (err: any) {
      console.error(err);
    }
  };

  // 2. Keyboard Navigation & Safety (Constraint 6)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Safety check: Never fire shortcuts if typing in input, textarea, select or active modal
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable ||
        document.querySelector('[role="dialog"]')
      ) {
        return;
      }

      const activeItems = (extraction?.line_items || []).filter((i) => !i.is_removed);
      if (activeItems.length === 0) return;

      const currentIndex = activeItems.findIndex((i) => i.id === selectedLineItemId);

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = currentIndex < activeItems.length - 1 ? currentIndex + 1 : 0;
        const nextItem = activeItems[nextIndex];
        setSelectedLineItemId(nextItem.id);
        if (nextItem.source_evidence) {
          setActiveEvidence(nextItem.source_evidence);
        }
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : activeItems.length - 1;
        const prevItem = activeItems[prevIndex];
        setSelectedLineItemId(prevItem.id);
        if (prevItem.source_evidence) {
          setActiveEvidence(prevItem.source_evidence);
        }
      } else if (e.key === "e" && selectedLineItemId) {
        e.preventDefault();
        const item = activeItems.find((i) => i.id === selectedLineItemId);
        if (item) setEditingItem(item);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [extraction, selectedLineItemId]);

  // 3. Split-Pane Divider Dragging
  const handleMouseDownDivider = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingDivider(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingDivider) return;
      const windowWidth = window.innerWidth;
      const newRatio = (e.clientX / windowWidth) * 100;
      if (newRatio >= 25 && newRatio <= 75) {
        setSplitRatio(newRatio);
      }
    };

    const handleMouseUp = () => {
      setIsDraggingDivider(false);
    };

    if (isDraggingDivider) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingDivider]);

  // 4. Item Selection & Evidence Highlighting
  const handleSelectLineItem = (item: ExtractedLineItem) => {
    setSelectedLineItemId(item.id);
    if (item.source_evidence) {
      setActiveEvidence(item.source_evidence);
    }
  };

  // 5. Line Item Save
  const handleSaveLineItem = async (itemId: string, patch: Partial<ExtractedLineItem>) => {
    if (!quotationId) return;
    await correctLineItem(quotationId, itemId, patch);
    await loadAllData();
  };

  // 6. Line Item Soft Delete
  const handleSoftDeleteLineItem = async (itemId: string) => {
    if (!quotationId) return;
    const reason = window.prompt("Reason for excluding this line item:", "Non-matching or duplicate");
    if (reason === null) return;
    await softDeleteLineItem(quotationId, itemId, reason);
    await loadAllData();
  };

  // 7. Line Item Restore
  const handleRestoreLineItem = async (itemId: string) => {
    if (!quotationId) return;
    await restoreLineItem(quotationId, itemId);
    await loadAllData();
  };

  // 8. Add Missed Line Item
  const handleAddLineItem = async (data: any) => {
    if (!quotationId) return;
    await createLineItem(quotationId, data);
    await loadAllData();
  };

  // 9. Approve Extraction
  const handleApproveExtraction = async (acknowledgedWarnings: string[]) => {
    if (!quotationId) return;
    await approveExtraction(quotationId, acknowledgedWarnings);
    await loadAllData();
  };

  // 10. Reject Extraction
  const handleRejectExtraction = async (reason: string) => {
    if (!quotationId) return;
    await rejectExtraction(quotationId, reason);
    await loadAllData();
  };

  const isPDF =
    activeDocFilename.toLowerCase().endsWith(".pdf") ||
    activeDocMime.includes("pdf");

  const lineItems = extraction?.line_items || [];
  const activeLineItems = lineItems.filter((i) => !i.is_removed);
  const excludedLineItems = lineItems.filter((i) => i.is_removed);

  const filteredLineItems =
    filterMode === "attention"
      ? activeLineItems.filter(
          (i) => i.has_discrepancy || i.confidence < 0.8 || !i.rfq_line_item_id
        )
      : filterMode === "excluded"
      ? excludedLineItems
      : activeLineItems;

  const discrepanciesCount = activeLineItems.filter((i) => i.has_discrepancy).length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white gap-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-400 font-mono">Initializing Human Review Workspace...</p>
      </div>
    );
  }

  if (error || !quotation) {
    return (
      <div className="p-8 max-w-lg mx-auto my-12 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Review Workspace Error</h2>
        <p className="text-xs text-slate-400">{error || "Quotation not found"}</p>
        <Link
          to="/quotations"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-semibold rounded-lg transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Quotations
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Workspace Header */}
      <header className="flex items-center justify-between px-4 py-2.5 bg-slate-900/95 border-b border-slate-800 z-20 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to="/quotations"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Back to quotations"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white tracking-wide">
                {quotation.supplier_name}
              </h1>
              {quotation.supplier_reference && (
                <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
                  Ref: {quotation.supplier_reference}
                </span>
              )}
              {/* Review Status Pill */}
              <span
                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  quotation.status === "approved"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : quotation.status === "rejected"
                    ? "bg-rose-950 text-rose-300 border-rose-800"
                    : "bg-amber-950 text-amber-300 border-amber-800 animate-pulse"
                }`}
              >
                {quotation.status === "approved"
                  ? "Extraction Approved"
                  : quotation.status === "rejected"
                  ? "Extraction Rejected"
                  : "Needs Review"}
              </span>
            </div>
            {rfq && (
              <p className="text-[11px] text-slate-400 truncate max-w-md">
                RFQ: {rfq.title} ({rfq.reference_currency})
              </p>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {/* Document Switcher */}
          {quotation.documents.length > 1 && (
            <select
              value={selectedDocId}
              onChange={(e) => handleSwitchDocument(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none"
            >
              {quotation.documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          )}

          {/* Audit Trail Button */}
          <button
            onClick={() => setShowAuditDrawer(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-lg border border-slate-700/80 transition"
          >
            <History className="w-3.5 h-3.5 text-blue-400" />
            <span>Audit Trail ({auditLogs.length})</span>
          </button>

          {/* Decision Buttons (Strictly explicit human action with confirmation modal) */}
          {quotation.status === "needs_review" && (
            <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
              <button
                onClick={() => setDecisionModalType("reject")}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/80 rounded-lg transition shadow-sm"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Reject Extraction</span>
              </button>

              <button
                onClick={() => setDecisionModalType("approve")}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-600 rounded-lg transition shadow-md shadow-emerald-700/20"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Approve Extraction</span>
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Split-Pane Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* LEFT PANE: Document Viewer */}
        <section
          style={{ width: `${splitRatio}%` }}
          className="h-full flex flex-col overflow-hidden p-2 bg-slate-950"
          aria-label="Original Document Viewer"
        >
          {documentBlob ? (
            isPDF ? (
              <PDFViewer
                blob={documentBlob}
                filename={activeDocFilename}
                activeEvidence={activeEvidence}
              />
            ) : (
              <SpreadsheetViewer
                blob={documentBlob}
                filename={activeDocFilename}
                activeEvidence={activeEvidence}
              />
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-full border border-slate-800 rounded-lg text-slate-500 text-xs">
              <FileText className="w-8 h-8 mb-2 text-slate-600" />
              <span>No document file loaded</span>
            </div>
          )}
        </section>

        {/* RESIZABLE DIVIDER */}
        <div
          onMouseDown={handleMouseDownDivider}
          className={`w-1.5 hover:w-2 bg-slate-800 hover:bg-blue-500 transition-all cursor-col-resize select-none relative z-10 ${
            isDraggingDivider ? "bg-blue-500 w-2" : ""
          }`}
          title="Drag to resize split pane"
        />

        {/* RIGHT PANE: Structured Data & Human Verification Panel */}
        <section
          style={{ width: `${100 - splitRatio}%` }}
          className="h-full flex flex-col overflow-y-auto bg-slate-900/60 border-l border-slate-800 p-4 space-y-4"
          aria-label="Extracted Structured Data and Verification"
        >
          {/* Validation & Discrepancy Alert Center */}
          <ValidationAlertCenter
            validationStatus={validationStatus}
            discrepanciesCount={discrepanciesCount}
            onAcknowledgeWarning={async (warn) => {
              if (!quotationId) return;
              await approveExtraction(quotationId, [warn]).catch(() => {});
              await loadAllData();
            }}
          />

          {/* Header Metadata & Commercial Terms */}
          {extraction && extraction.fields.length > 0 && (
            <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg text-xs space-y-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Commercial Terms & Validity
              </span>
              <div className="grid grid-cols-2 gap-3 pt-1">
                {extraction.fields.map((field) => (
                  <div key={field.id} className="flex flex-col">
                    <span className="text-slate-400 capitalize text-[11px]">
                      {field.field_name.replace("_", " ")}:
                    </span>
                    <div className="flex items-center gap-1.5 font-medium text-slate-200">
                      <span>{field.raw_value || "Not specified"}</span>
                      {field.human_corrected && (
                        <span className="text-[9px] px-1 bg-blue-950 text-blue-300 border border-blue-800 rounded">
                          Edited
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Line Items Verification Header & Filters */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                Extracted Line Items ({activeLineItems.length})
              </h2>
              {discrepanciesCount > 0 && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-800">
                  {discrepanciesCount} Math Mismatch
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Filter Tabs */}
              <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[11px]">
                <button
                  onClick={() => setFilterMode("all")}
                  className={`px-2 py-0.5 rounded ${
                    filterMode === "all"
                      ? "bg-slate-800 text-white font-medium"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  All ({activeLineItems.length})
                </button>
                <button
                  onClick={() => setFilterMode("attention")}
                  className={`px-2 py-0.5 rounded ${
                    filterMode === "attention"
                      ? "bg-slate-800 text-amber-300 font-medium"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Attention ({activeLineItems.filter((i) => i.has_discrepancy || i.confidence < 0.8).length})
                </button>
                {excludedLineItems.length > 0 && (
                  <button
                    onClick={() => setFilterMode("excluded")}
                    className={`px-2 py-0.5 rounded ${
                      filterMode === "excluded"
                        ? "bg-slate-800 text-slate-300 font-medium"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Excluded ({excludedLineItems.length})
                  </button>
                )}
              </div>

              {/* Add Missed Item CTA */}
              <button
                onClick={() => setShowAddDialog(true)}
                className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-300 bg-blue-950/60 hover:bg-blue-900 border border-blue-800/80 rounded-lg transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Item</span>
              </button>
            </div>
          </div>

          {/* Line Items List Table */}
          <div className="flex-1 space-y-2">
            {filteredLineItems.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-lg border border-slate-800">
                No line items match the selected filter.
              </div>
            ) : (
              filteredLineItems.map((item) => {
                const isSelected = selectedLineItemId === item.id;
                const calcTotal = item.calculated_total_price ?? (item.quantity * item.unit_price);
                const hasMismatch = item.has_discrepancy;

                return (
                  <div
                    key={item.id}
                    onClick={() => handleSelectLineItem(item)}
                    className={`p-3 rounded-lg border transition cursor-pointer select-none text-xs ${
                      item.is_removed
                        ? "bg-slate-950/40 border-slate-800 opacity-60 line-through"
                        : isSelected
                        ? "bg-slate-900/90 border-blue-500 shadow-md ring-1 ring-blue-500"
                        : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 flex-1">
                        {/* Description & Tags */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white">
                            {item.description_raw}
                          </span>
                          {item.human_corrected && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-950 text-blue-300 border border-blue-800">
                              Corrected
                            </span>
                          )}
                          {item.confidence < 0.75 && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">
                              Low Conf ({Math.round(item.confidence * 100)}%)
                            </span>
                          )}
                          {item.is_removed && (
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800 not-italic">
                              Removed{item.removal_reason ? `: ${item.removal_reason}` : ""}
                            </span>
                          )}
                        </div>

                        {/* RFQ Match Info */}
                        {rfq && (
                          <div className="text-[11px] text-slate-400">
                            {item.rfq_line_item_id ? (
                              <span className="text-emerald-400 font-medium">
                                Matched to RFQ #{rfq.line_items.find((r) => r.id === item.rfq_line_item_id)?.position} (
                                {rfq.line_items.find((r) => r.id === item.rfq_line_item_id)?.description})
                              </span>
                            ) : (
                              <span className="text-amber-400/90 italic">
                                Unlinked: Select RFQ requirement in Edit
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                        {item.source_evidence && (
                          <button
                            onClick={() => handleSelectLineItem(item)}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-950/80 hover:bg-blue-900 border border-blue-800/80 text-blue-300 hover:text-blue-200 text-[10px] font-mono transition"
                            title="Jump to document evidence"
                            aria-label="Jump to document evidence"
                          >
                            <Eye className="w-3 h-3" />
                            <span>
                              {item.source_evidence.page_number
                                ? `p. ${item.source_evidence.page_number}`
                                : item.source_evidence.cell_range || "Evidence"}
                            </span>
                          </button>
                        )}
                        <button
                          onClick={() => setEditingItem(item)}
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
                          title="Edit line item"
                          aria-label="Edit line item"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {item.is_removed ? (
                          <button
                            onClick={() => handleRestoreLineItem(item.id)}
                            className="p-1 rounded hover:bg-slate-800 text-emerald-400 hover:text-emerald-300 transition"
                            title="Restore excluded item"
                            aria-label="Restore excluded item"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSoftDeleteLineItem(item.id)}
                            className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition"
                            title="Soft-delete this line item (preserves in audit history)"
                            aria-label="Soft-delete this line item (preserves in audit history)"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Numeric breakdown & Preserved Quoted vs Calculated */}
                    <div className="mt-2 pt-2 border-t border-slate-800/80 grid grid-cols-4 gap-2 text-[11px] font-mono">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Qty:</span>
                        <span className="text-slate-200">
                          {item.quantity} {item.unit}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Unit Price:</span>
                        <span className="text-slate-200">${item.unit_price}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Supplier Quoted:</span>
                        <span className={`font-bold ${hasMismatch ? "text-rose-400" : "text-white"}`}>
                          ${item.total_price}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Calculated:</span>
                        <span className="text-slate-300">${calcTotal.toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Math Discrepancy Banner */}
                    {hasMismatch && !item.is_removed && (
                      <div className="mt-2 p-1.5 bg-rose-950/30 border border-rose-800/40 rounded flex items-center justify-between text-[10px] text-rose-300">
                        <span className="flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                          <span>
                            Math Mismatch: Quoted (${item.total_price}) != Calc (${calcTotal.toFixed(2)})
                          </span>
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingItem(item);
                          }}
                          className="text-blue-400 hover:underline font-semibold"
                        >
                          Resolve in Edit
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>

      {/* Dialog Modals */}
      <LineItemEditDialog
        isOpen={Boolean(editingItem)}
        item={editingItem}
        rfqLineItems={rfq?.line_items || []}
        onClose={() => setEditingItem(null)}
        onSave={handleSaveLineItem}
      />

      <LineItemAddDialog
        isOpen={showAddDialog}
        currency={quotation.documents[0]?.filename || "USD"}
        rfqLineItems={rfq?.line_items || []}
        onClose={() => setShowAddDialog(false)}
        onAdd={handleAddLineItem}
      />

      <ExtractionDecisionModal
        isOpen={Boolean(decisionModalType)}
        type={decisionModalType || "approve"}
        supplierName={quotation.supplier_name}
        validationStatus={validationStatus}
        onClose={() => setDecisionModalType(null)}
        onConfirmApprove={handleApproveExtraction}
        onConfirmReject={handleRejectExtraction}
      />

      <AuditHistoryDrawer
        isOpen={showAuditDrawer}
        logs={auditLogs}
        onClose={() => setShowAuditDrawer(false)}
      />
    </div>
  );
};
