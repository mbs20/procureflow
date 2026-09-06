import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Layers,
  Plus,
  Search,
  Archive,
  Copy,
  RefreshCw,
  Clock,
  ArrowUpRight,
  Filter,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { RFQ, fetchRFQs, archiveRFQ, unarchiveRFQ, cloneRFQ } from "../api/rfq";
import { CreateRFQModal } from "../components/rfq/CreateRFQModal";

export const RFQListPage: React.FC = () => {
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<string>("all");
  const [search, setSearch] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadRFQs = async () => {
    setLoading(true);
    setError(null);
    try {
      const includeArchived = activeTab === "archived";
      const statusFilter = activeTab !== "all" && activeTab !== "archived" ? activeTab : undefined;
      const data = await fetchRFQs({
        include_archived: includeArchived,
        status: statusFilter,
        category: search || undefined,
      });
      setRfqs(data.items);
    } catch (err: any) {
      setError(err.message || "Failed to load RFQs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRFQs();
  }, [activeTab, search]);

  const handleArchive = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await archiveRFQ(id);
      setActionMessage("RFQ archived successfully");
      loadRFQs();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUnarchive = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await unarchiveRFQ(id);
      setActionMessage("RFQ restored to active");
      loadRFQs();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleClone = async (id: string, title: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const cloned = await cloneRFQ(id, `${title} (Copy)`);
      setActionMessage(`Cloned as "${cloned.title}"`);
      loadRFQs();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const getStatusBadge = (status: string, isArchived: boolean) => {
    if (isArchived) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-zinc-500/10 px-2 py-0.5 text-[11px] font-semibold text-zinc-400 border border-zinc-500/20">
          <Archive className="h-3 w-3" />
          Archived
        </span>
      );
    }
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Active
          </span>
        );
      case "evaluating":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-400 border border-blue-500/20">
            Evaluating
          </span>
        );
      case "decided":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-purple-500/10 px-2 py-0.5 text-[11px] font-semibold text-purple-400 border border-purple-500/20">
            Decided
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-400 border border-amber-500/20">
            Draft
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="h-6 w-6 text-blue-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white">Procurement Requests & RFQs</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Create sourcing events, define required line items, and set weighted evaluation rubrics.
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-blue-500/25 hover:bg-blue-600 transition-all"
        >
          <Plus className="h-4 w-4" />
          Create New RFQ
        </button>
      </div>

      {actionMessage && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div className="flex items-center gap-1 bg-secondary/40 p-1 rounded-xl border border-border/50 text-xs overflow-x-auto">
          {[
            { key: "all", label: "All RFQs" },
            { key: "draft", label: "Draft" },
            { key: "active", label: "Active" },
            { key: "evaluating", label: "Evaluating" },
            { key: "decided", label: "Decided" },
            { key: "archived", label: "Archived (Soft Delete)" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeTab === tab.key
                  ? "bg-primary text-white shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter by category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-secondary/30 pl-8 pr-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* RFQ List Cards */}
      {loading ? (
        <div className="flex items-center justify-center p-12 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-400" />
        </div>
      ) : rfqs.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center space-y-4">
          <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-secondary/60 text-muted-foreground">
            <Filter className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">No Procurement Requests Found</h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
              {activeTab === "archived"
                ? "No soft-deleted archived RFQs in this category."
                : "Get started by creating your first RFQ with required line items and evaluation criteria."}
            </p>
          </div>
          {activeTab !== "archived" && (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white shadow hover:bg-blue-600 transition-all"
            >
              <Plus className="h-4 w-4" />
              Create RFQ Now
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {rfqs.map((rfq) => (
            <div
              key={rfq.id}
              className="glass-card rounded-xl p-5 hover:border-blue-500/40 transition-all group"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/rfqs/${rfq.id}`}
                      className="text-base font-bold text-white hover:text-blue-400 transition-colors flex items-center gap-1.5"
                    >
                      <span>{rfq.title}</span>
                      <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity text-blue-400" />
                    </Link>
                    {getStatusBadge(rfq.status, rfq.is_archived)}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1">
                    {rfq.description || "No specific scope notes provided."}
                  </p>
                  <div className="flex flex-wrap items-center gap-4 pt-1 text-[11px] text-muted-foreground">
                    <span className="rounded bg-secondary/60 px-2 py-0.5 border border-border">
                      Category: <strong className="text-foreground">{rfq.category}</strong>
                    </span>
                    <span className="rounded bg-secondary/60 px-2 py-0.5 border border-border">
                      Currency: <strong className="text-foreground">{rfq.reference_currency}</strong>
                    </span>
                    <span>
                      Items: <strong className="text-foreground">{rfq.line_items?.length || 0}</strong>
                    </span>
                    <span>
                      Criteria: <strong className="text-foreground">{rfq.criteria?.length || 0}</strong>
                    </span>
                    <span className="flex items-center gap-1 text-slate-400">
                      <Clock className="h-3 w-3" />
                      {new Date(rfq.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/rfqs/${rfq.id}`}
                    className="rounded-lg bg-secondary/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
                  >
                    View Details
                  </Link>

                  <button
                    onClick={(e) => handleClone(rfq.id, rfq.title, e)}
                    title="Clone as new template"
                    className="rounded-lg bg-secondary/40 p-2 text-muted-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>

                  {rfq.is_archived ? (
                    <button
                      onClick={(e) => handleUnarchive(rfq.id, e)}
                      title="Restore from archive"
                      className="rounded-lg bg-secondary/40 p-2 text-muted-foreground hover:bg-emerald-500/20 hover:text-emerald-400 transition-colors border border-border"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                  ) : (
                    <button
                      onClick={(e) => handleArchive(rfq.id, e)}
                      title="Archive RFQ (soft delete)"
                      className="rounded-lg bg-secondary/40 p-2 text-muted-foreground hover:bg-red-500/20 hover:text-red-400 transition-colors border border-border"
                    >
                      <Archive className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <CreateRFQModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setActionMessage("New RFQ created successfully!");
          loadRFQs();
          setTimeout(() => setActionMessage(null), 3000);
        }}
      />
    </div>
  );
};
