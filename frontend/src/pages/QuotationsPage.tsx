import React, { useState, useEffect } from "react";
import {
  FileText,
  Upload,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ExternalLink,
  ChevronRight,
  Layers,
  Sparkles,
  MapPin,
  Edit2,
  Save,
  X,
  FileSpreadsheet,
} from "lucide-react";
import {
  SupplierQuotation,
  ExtractedQuotation,
  QuotationStatus,
  fetchQuotations,
  createQuotation,
  uploadQuotationDocument,
  triggerExtraction,
  fetchLatestExtraction,
  correctLineItem,
  updateQuotationStatus,
} from "../api/quotation";
import { RFQ, fetchRFQs } from "../api/rfq";

export const QuotationsPage: React.FC = () => {
  const [quotations, setQuotations] = useState<SupplierQuotation[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [selectedRfqId, setSelectedRfqId] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadSupplierName, setUploadSupplierName] = useState<string>("");
  const [uploadSupplierRef, setUploadSupplierRef] = useState<string>("");
  const [uploadRfqId, setUploadRfqId] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Inspection & Review Drawer state
  const [selectedQuotation, setSelectedQuotation] = useState<SupplierQuotation | null>(null);
  const [latestExtraction, setLatestExtraction] = useState<ExtractedQuotation | null>(null);
  const [loadingExtraction, setLoadingExtraction] = useState<boolean>(false);
  const [activeEvidence, setActiveEvidence] = useState<{ title: string; data: any } | null>(null);

  // Inline line-item editing state
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState<number>(0);
  const [editPrice, setEditPrice] = useState<number>(0);
  const [savingItem, setSavingItem] = useState<boolean>(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadQuotations();
  }, [selectedRfqId, statusFilter]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [rfqRes, quotesRes] = await Promise.all([
        fetchRFQs({ page_size: 50 }),
        fetchQuotations(),
      ]);
      setRfqs(rfqRes.items);
      setQuotations(quotesRes);
      if (rfqRes.items.length > 0) {
        setUploadRfqId(rfqRes.items[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load quotations");
    } finally {
      setLoading(false);
    }
  };

  const loadQuotations = async () => {
    try {
      const params: any = {};
      if (selectedRfqId) params.rfq_id = selectedRfqId;
      if (statusFilter !== "all") params.status = statusFilter as QuotationStatus;
      const quotes = await fetchQuotations(params);
      setQuotations(quotes);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleOpenDrawer = async (q: SupplierQuotation) => {
    setSelectedQuotation(q);
    setLatestExtraction(null);
    setActiveEvidence(null);
    setEditingItemId(null);

    if (q.status !== "uploaded") {
      setLoadingExtraction(true);
      try {
        const ext = await fetchLatestExtraction(q.id);
        setLatestExtraction(ext);
      } catch (err) {
        console.warn("No extraction found yet");
      } finally {
        setLoadingExtraction(false);
      }
    }
  };

  const handleTriggerExtract = async (qId: string) => {
    try {
      await triggerExtraction(qId);
      await loadQuotations();
      // Refresh current drawer if open
      if (selectedQuotation && selectedQuotation.id === qId) {
        setLoadingExtraction(true);
        setTimeout(async () => {
          try {
            const updated = await fetchQuotations();
            setQuotations(updated);
            const currentQ = updated.find((item) => item.id === qId);
            if (currentQ) setSelectedQuotation(currentQ);
            const ext = await fetchLatestExtraction(qId);
            setLatestExtraction(ext);
          } catch (e) {
            console.error(e);
          } finally {
            setLoadingExtraction(false);
          }
        }, 1200);
      }
    } catch (err: any) {
      alert(err.message || "Failed to trigger extraction");
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadRfqId || !uploadSupplierName.trim() || !selectedFile) {
      setUploadError("Please provide RFQ, Supplier Name, and a valid document file.");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      // 1. Create quotation container
      const newQuote = await createQuotation({
        rfq_id: uploadRfqId,
        supplier_name: uploadSupplierName.trim(),
        supplier_reference: uploadSupplierRef.trim() || undefined,
      });

      // 2. Upload and attach document
      await uploadQuotationDocument(newQuote.id, selectedFile);

      // 3. Reset form and refresh
      setShowUploadModal(false);
      setUploadSupplierName("");
      setUploadSupplierRef("");
      setSelectedFile(null);
      await loadQuotations();

      // Open drawer for the newly created quotation
      handleOpenDrawer(newQuote);
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleSaveLineItemEdit = async (itemId: string) => {
    if (!selectedQuotation) return;
    setSavingItem(true);
    try {
      await correctLineItem(selectedQuotation.id, itemId, {
        quantity: editQty,
        unit_price: editPrice,
      });
      // Refresh extraction
      const ext = await fetchLatestExtraction(selectedQuotation.id);
      setLatestExtraction(ext);
      setEditingItemId(null);
    } catch (err: any) {
      alert(err.message || "Failed to update line item");
    } finally {
      setSavingItem(false);
    }
  };

  const handleReviewDecision = async (status: "approved" | "rejected") => {
    if (!selectedQuotation) return;
    try {
      const updated = await updateQuotationStatus(selectedQuotation.id, status);
      setSelectedQuotation(updated);
      await loadQuotations();
    } catch (err: any) {
      alert(err.message || `Failed to update status to ${status}`);
    }
  };

  const getStatusBadge = (status: QuotationStatus) => {
    switch (status) {
      case "needs_review":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            Needs Review
          </span>
        );
      case "approved":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Approved
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            Rejected
          </span>
        );
      case "extracting":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Extracting...
          </span>
        );
      case "queued":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3.5 h-3.5" />
            Queued
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <XCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-300 border border-slate-500/20">
            <FileText className="w-3.5 h-3.5" />
            Uploaded
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6 rounded-2xl border border-white/5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/20 text-primary border border-primary/30">
              Phase 2
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Supplier Quotations & Ingestion
            </h1>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Upload supplier documents (PDF, modern Excel .xlsx, CSV). Process multi-tier deterministic,
            OCR, and LLM extractions with authoritative parser coordinate evidence and human review.
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-colors shadow-lg shadow-primary/20"
        >
          <Upload className="w-4 h-4" />
          Upload Quotation
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl glass-card border border-white/5">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            RFQ Scope:
          </label>
          <select
            value={selectedRfqId}
            onChange={(e) => setSelectedRfqId(e.target.value)}
            className="bg-secondary/60 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">All RFQs ({rfqs.length})</option>
            {rfqs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title} ({r.reference_currency})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 bg-secondary/40 p-1 rounded-lg border border-white/5 text-xs">
          {["all", "needs_review", "uploaded", "approved", "rejected", "failed"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-md capitalize transition-colors ${
                statusFilter === st
                  ? "bg-primary text-white font-medium"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Quotations List Table */}
      <div className="glass-card rounded-2xl overflow-hidden border border-white/5">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-6 h-6 animate-spin text-primary" />
            <span>Loading quotation records...</span>
          </div>
        ) : quotations.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <FileSpreadsheet className="w-12 h-12 text-muted-foreground/40 mx-auto" />
            <h3 className="text-base font-medium text-white">No quotations found</h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              Upload supplier quotations in PDF, modern Excel (.xlsx), or CSV format to begin parsing.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-secondary/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="p-4">Supplier</th>
                  <th className="p-4">Reference</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Documents</th>
                  <th className="p-4">Created</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {quotations.map((q) => (
                  <tr
                    key={q.id}
                    className="hover:bg-white/[0.02] transition-colors cursor-pointer"
                    onClick={() => handleOpenDrawer(q)}
                  >
                    <td className="p-4 font-semibold text-white">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary/70" />
                        {q.supplier_name}
                      </div>
                    </td>
                    <td className="p-4 text-muted-foreground font-mono text-xs">
                      {q.supplier_reference || "—"}
                    </td>
                    <td className="p-4">{getStatusBadge(q.status)}</td>
                    <td className="p-4">
                      {q.documents && q.documents.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {q.documents.map((doc) => (
                            <a
                              key={doc.id}
                              href={`/api/v1/quotations/${q.id}/documents/${doc.id}/download`}
                              onClick={(e) => e.stopPropagation()}
                              download
                              className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-secondary/60 hover:bg-secondary text-primary border border-white/5 transition-colors"
                              title={`${doc.filename} (${(doc.size_bytes / 1024).toFixed(1)} KB)`}
                            >
                              <ExternalLink className="w-3 h-3" />
                              {doc.filename.length > 20
                                ? doc.filename.slice(0, 17) + "..."
                                : doc.filename}
                            </a>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">None</span>
                      )}
                    </td>
                    <td className="p-4 text-xs text-muted-foreground">
                      {new Date(q.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleTriggerExtract(q.id)}
                          disabled={!q.documents || q.documents.length === 0}
                          className="px-2.5 py-1 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-white border border-white/5 transition-colors disabled:opacity-40"
                          title="Extract or re-extract (idempotent archive history)"
                        >
                          <RefreshCw className="w-3.5 h-3.5 inline mr-1" />
                          {q.status === "needs_review" || q.status === "approved" ? "Re-extract" : "Extract"}
                        </button>
                        <button
                          onClick={() => handleOpenDrawer(q)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5 transition-colors"
                          title="View Extraction & Evidence"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl p-6 max-w-lg w-full border border-white/10 space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-bold text-white">Upload Supplier Quotation</h2>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-muted-foreground hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Target RFQ <span className="text-rose-400">*</span>
                </label>
                <select
                  required
                  value={uploadRfqId}
                  onChange={(e) => setUploadRfqId(e.target.value)}
                  className="w-full bg-secondary/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {rfqs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title} ({r.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Supplier Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Acme Industrial Parts Ltd."
                  value={uploadSupplierName}
                  onChange={(e) => setUploadSupplierName(e.target.value)}
                  className="w-full bg-secondary/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Supplier Reference / Quotation ID (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g., QUOTE-2026-902"
                  value={uploadSupplierRef}
                  onChange={(e) => setUploadSupplierRef(e.target.value)}
                  className="w-full bg-secondary/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Quotation File <span className="text-rose-400">*</span>
                </label>
                <div className="border-2 border-dashed border-white/15 rounded-xl p-6 text-center hover:border-primary/50 transition-colors bg-secondary/20">
                  <input
                    type="file"
                    required
                    accept=".pdf,.xlsx,.csv"
                    onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                    className="hidden"
                    id="quotation-file-input"
                  />
                  <label htmlFor="quotation-file-input" className="cursor-pointer space-y-2 block">
                    <FileText className="w-8 h-8 text-primary/70 mx-auto" />
                    <div className="text-sm font-medium text-white">
                      {selectedFile ? selectedFile.name : "Click or drag quotation file to upload"}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Supported formats: PDF (.pdf), modern Excel (.xlsx), CSV (.csv)
                    </p>
                  </label>
                </div>
              </div>

              {/* Excel Format Note */}
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 space-y-1">
                <span className="font-semibold">Format Note:</span> Modern Excel (<span className="font-mono">.xlsx</span>) is fully supported. Legacy <span className="font-mono">.xls</span> must be saved as <span className="font-mono">.xlsx</span> prior to ingestion.
              </div>

              {uploadError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
                  {uploadError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-muted-foreground hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-5 py-2 rounded-xl text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20 disabled:opacity-50 flex items-center gap-2"
                >
                  {uploading && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {uploading ? "Saving..." : "Save & Attach Document"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Drawer: Detailed Extraction & Human Review */}
      {selectedQuotation && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-3xl bg-slate-950/95 backdrop-blur-xl border-l border-white/10 shadow-2xl flex flex-col">
          {/* Drawer Header */}
          <div className="p-6 border-b border-white/10 flex items-start justify-between bg-slate-900/60">
            <div>
              <div className="flex items-center gap-2 mb-1">
                {getStatusBadge(selectedQuotation.status)}
                {latestExtraction && (
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-secondary text-white border border-white/10">
                    Run v{latestExtraction.extraction_version}
                  </span>
                )}
                {latestExtraction?.extraction_model && (
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                    {latestExtraction.extraction_model}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-white">
                {selectedQuotation.supplier_name}
              </h2>
              <p className="text-xs text-muted-foreground font-mono">
                Ref: {selectedQuotation.supplier_reference || "N/A"} • Quotation ID: {selectedQuotation.id}
              </p>
            </div>
            <button
              onClick={() => setSelectedQuotation(null)}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleTriggerExtract(selectedQuotation.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-white border border-white/10 flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Trigger / Retry Extraction
                </button>
                {selectedQuotation.documents.length > 0 && (
                  <a
                    href={`/api/v1/quotations/${selectedQuotation.id}/documents/${selectedQuotation.documents[0].id}/download`}
                    download
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary/60 hover:bg-secondary text-primary border border-white/10 flex items-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Download Original
                  </a>
                )}
              </div>

              {/* Human Review Decision Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReviewDecision("approved")}
                  disabled={selectedQuotation.status !== "needs_review"}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approve Quotation
                </button>
                <button
                  onClick={() => handleReviewDecision("rejected")}
                  disabled={selectedQuotation.status !== "needs_review"}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/80 hover:bg-rose-600 text-white shadow-lg shadow-rose-500/20 disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Reject
                </button>
              </div>
            </div>

            {/* Validation Warnings Callout */}
            {latestExtraction?.raw_llm_output?.validation_warnings &&
              latestExtraction.raw_llm_output.validation_warnings.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-amber-200">
                    <AlertTriangle className="w-4 h-4" />
                    Ingestion Warnings & Anomalies Detected:
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-amber-300/90 pl-1">
                    {latestExtraction.raw_llm_output.validation_warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

            {/* Extraction Results */}
            {loadingExtraction ? (
              <div className="py-12 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-6 h-6 animate-spin text-primary" />
                <span>Reading extracted data & coordinates...</span>
              </div>
            ) : !latestExtraction ? (
              <div className="p-8 text-center text-muted-foreground space-y-2">
                <Layers className="w-8 h-8 mx-auto text-muted-foreground/40" />
                <p>No extraction performed yet. Click "Trigger / Retry Extraction" to start parsing.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Confidence & Notes Summary */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-xl bg-secondary/30 border border-white/5 space-y-1">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">
                      Overall Extraction Confidence
                    </span>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-primary" />
                      {(Number(latestExtraction.overall_confidence) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-secondary/30 border border-white/5 space-y-1">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">
                      Line Items Extracted
                    </span>
                    <div className="text-lg font-bold text-white">
                      {latestExtraction.line_items.length} items
                    </div>
                  </div>
                </div>

                {/* Line Items Table */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                    Extracted Line Items (With Authoritative Parser Coordinates)
                  </h3>
                  <div className="border border-white/10 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-secondary/40 text-muted-foreground border-b border-white/10">
                          <th className="p-3">Item Description</th>
                          <th className="p-3">Qty</th>
                          <th className="p-3">Unit Price</th>
                          <th className="p-3">Total</th>
                          <th className="p-3">Confidence</th>
                          <th className="p-3">Evidence</th>
                          <th className="p-3 text-right">Edit</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {latestExtraction.line_items.map((item) => (
                          <tr key={item.id} className="hover:bg-white/[0.02]">
                            <td className="p-3 font-medium text-white max-w-xs">
                              {item.description_raw}
                              {item.human_corrected && (
                                <span className="ml-2 text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                                  corrected
                                </span>
                              )}
                            </td>
                            <td className="p-3 text-muted-foreground">
                              {editingItemId === item.id ? (
                                <input
                                  type="number"
                                  value={editQty}
                                  onChange={(e) => setEditQty(Number(e.target.value))}
                                  className="w-16 bg-black/60 border border-white/20 rounded px-1 py-0.5 text-white"
                                />
                              ) : (
                                `${item.quantity} ${item.unit}`
                              )}
                            </td>
                            <td className="p-3 font-mono text-white">
                              {editingItemId === item.id ? (
                                <input
                                  type="number"
                                  step="0.01"
                                  value={editPrice}
                                  onChange={(e) => setEditPrice(Number(e.target.value))}
                                  className="w-20 bg-black/60 border border-white/20 rounded px-1 py-0.5 text-white"
                                />
                              ) : (
                                `${Number(item.unit_price).toFixed(2)} ${item.currency}`
                              )}
                            </td>
                            <td className="p-3 font-mono font-semibold text-white">
                              <div>{Number(item.total_price).toFixed(2)}</div>
                              {item.has_discrepancy && (
                                <div
                                  className="text-[10px] text-amber-400 font-sans font-normal flex items-center gap-1 mt-0.5"
                                  title="Quoted total differs from calculated quantity × unit price"
                                >
                                  <span>Calc: {item.calculated_total_price != null ? Number(item.calculated_total_price).toFixed(2) : (Number(item.quantity) * Number(item.unit_price)).toFixed(2)}</span>
                                  <span className="text-[9px] px-1 py-0.2 rounded bg-amber-500/20 text-amber-300">discrepancy</span>
                                </div>
                              )}
                            </td>
                            <td className="p-3">
                              {(() => {
                                const ev = item.source_evidence || item.source_bbox;
                                if (!ev) return <span className="text-muted-foreground text-[11px]">—</span>;
                                return (
                                  <button
                                    onClick={() =>
                                      setActiveEvidence({
                                        title: item.description_raw,
                                        data: ev,
                                      })
                                    }
                                    className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-secondary/80 hover:bg-secondary text-primary border border-white/5 transition-colors"
                                    title="View Authoritative Parser Coordinates"
                                  >
                                    <MapPin className="w-3 h-3" />
                                    {ev.type === "spreadsheet"
                                      ? `Row ${ev.row_idx || ev.row || 1}`
                                      : ev.type === "ocr_pdf"
                                      ? `OCR P.${ev.page || 1}`
                                      : `Page ${ev.page || 1}`}
                                  </button>
                                );
                              })()}
                            </td>
                            <td className="p-3 text-right">
                              {editingItemId === item.id ? (
                                <div className="flex items-center justify-end gap-1">
                                  <button
                                    onClick={() => handleSaveLineItemEdit(item.id)}
                                    disabled={savingItem}
                                    className="p-1 rounded text-emerald-400 hover:bg-emerald-500/10"
                                    title="Save"
                                  >
                                    <Save className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => setEditingItemId(null)}
                                    className="p-1 rounded text-muted-foreground hover:bg-white/5"
                                    title="Cancel"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => {
                                    setEditingItemId(item.id);
                                    setEditQty(Number(item.quantity));
                                    setEditPrice(Number(item.unit_price));
                                  }}
                                  className="p-1 rounded text-muted-foreground hover:text-white hover:bg-white/5"
                                  title="Human Correction"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Extracted Fields (Commercial Terms) */}
                {latestExtraction.fields && latestExtraction.fields.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                      Commercial & Delivery Terms
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      {latestExtraction.fields.map((f) => (
                        <div key={f.id} className="p-3 rounded-xl bg-secondary/30 border border-white/5 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-white capitalize">
                              {f.field_name.replace("_", " ")}
                            </span>
                            {(() => {
                              const fev = f.source_evidence || f.source_bbox;
                              if (!fev) return null;
                              return (
                                <button
                                  onClick={() =>
                                    setActiveEvidence({
                                      title: f.field_name,
                                      data: fev,
                                    })
                                  }
                                  className="text-[10px] text-primary hover:underline flex items-center gap-1"
                                >
                                  <MapPin className="w-2.5 h-2.5" />
                                  Evidence
                                </button>
                              );
                            })()}
                          </div>
                          <p className="text-xs text-muted-foreground">{f.raw_value || "—"}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Evidence Coordinates Modal */}
      {activeEvidence && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl p-6 max-w-md w-full border border-white/10 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-bold text-white">Authoritative Parser Coordinates</h3>
              </div>
              <button
                onClick={() => setActiveEvidence(null)}
                className="text-muted-foreground hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <p className="text-muted-foreground">
                Originating from parser/OCR output (not LLM-invented):
              </p>
              <pre className="p-3 rounded-xl bg-black/60 border border-white/10 text-emerald-400 font-mono overflow-x-auto text-[11px]">
                {JSON.stringify(activeEvidence.data, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveEvidence(null)}
                className="px-4 py-1.5 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuotationsPage;
