import React, { useEffect, useState } from "react";
import { useTranslation, Trans } from "react-i18next";
import { X, Camera, Clock, CheckCircle2, AlertTriangle, Eye, Plus } from "lucide-react";
import {
  ComparisonSnapshotRead,
  createComparisonSnapshot,
  listComparisonSnapshots,
} from "../../api/matrix";
import { formatDateTime } from "../../lib/formatters";
import { translateBackendError } from "../../lib/errorMessageMap";

interface SnapshotsModalProps {
  rfqId: string;
  onClose: () => void;
  onSelectSnapshot?: (snapshot: ComparisonSnapshotRead) => void;
  onSnapshotCreated: () => void;
}

export const SnapshotsModal: React.FC<SnapshotsModalProps> = ({
  rfqId,
  onClose,
  onSelectSnapshot,
  onSnapshotCreated,
}) => {
  const { t } = useTranslation();
  const [snapshots, setSnapshots] = useState<ComparisonSnapshotRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [titleInput, setTitleInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadSnapshots = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listComparisonSnapshots(rfqId);
      setSnapshots(list);
    } catch (err: any) {
      setError(translateBackendError(err, t));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshots();
  }, [rfqId]);

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createComparisonSnapshot(rfqId, titleInput.trim() || undefined);
      setSuccessMsg(t('matrix.snapshotFrozenSuccess'));
      setTitleInput("");
      onSnapshotCreated();
      loadSnapshots();
      setTimeout(() => setSuccessMsg(null), 2000);
    } catch (err: any) {
      setError(translateBackendError(err, t));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-xl rounded-2xl bg-card border border-border shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Camera className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">{t('matrix.snapshotsModalTitle')}</h2>
              <p className="text-xs text-muted-foreground">
                {t('matrix.snapshotsSubtitle')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-white hover:bg-secondary transition-colors"
            aria-label={t('common.close')}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

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

        {/* Freeze New Snapshot Form */}
        <form onSubmit={handleCreateSnapshot} className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3">
          <label className="text-xs font-bold text-white block">{t('matrix.freezeCurrentState')}</label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              placeholder={t('matrix.freezePlaceholder')}
              className="flex-1 rounded-lg border border-border bg-secondary/40 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-purple-500"
            />
            <button
              type="submit"
              disabled={creating}
              className="flex items-center gap-1.5 rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-500 transition-colors shadow-md shadow-purple-500/20 disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              {creating ? t('matrix.freezing') : t('matrix.freezeBtn')}
            </button>
          </div>
        </form>

        {/* Historical Snapshots List */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-white flex items-center justify-between">
            <span>{t('matrix.historicalSnapshots', { count: snapshots.length })}</span>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {loading ? (
              <div className="text-center py-6 text-xs text-muted-foreground">{t('matrix.loadingSnapshots')}</div>
            ) : snapshots.length === 0 ? (
              <div className="text-center py-8 border border-dashed border-border rounded-xl text-xs text-muted-foreground">
                {t('matrix.noSnapshots')}
              </div>
            ) : (
              snapshots.map((s) => (
                <div
                  key={s.id}
                  className="rounded-xl border border-border/70 bg-secondary/30 p-3.5 flex items-center justify-between hover:bg-secondary/50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-purple-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-purple-300">
                        v{s.snapshot_version}
                      </span>
                      <span className="text-xs font-semibold text-white">
                        {s.title || t('matrix.snapshotDefaultTitle', { version: s.snapshot_version })}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDateTime(s.created_at)}
                      </span>
                      <span>•</span>
                      <span>
                        <Trans
                          i18nKey="matrix.currencySnapshotInfo"
                          values={{ currency: s.reference_currency }}
                          components={{ 1: <strong className="text-foreground" /> }}
                        />
                      </span>
                      <span>•</span>
                      <span>
                        <Trans
                          i18nKey="matrix.engineSnapshotInfo"
                          values={{ version: s.normalization_engine_version }}
                          components={{ 1: <strong className="text-foreground" /> }}
                        />
                      </span>
                    </div>
                  </div>

                  {onSelectSnapshot && (
                    <button
                      type="button"
                      onClick={() => onSelectSnapshot(s)}
                      className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:text-white transition-colors border border-border"
                    >
                      <Eye className="h-3.5 w-3.5" /> {t('matrix.viewSnapshotBtn')}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border bg-secondary/40 px-4 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            {t('common.close')}
          </button>
        </div>
      </div>
    </div>
  );
};
