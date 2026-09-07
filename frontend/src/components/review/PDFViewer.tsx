import React, { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  RefreshCw,
  AlertCircle,
  FileText,
} from "lucide-react";
import { PDFEvidenceOverlay } from "./PDFEvidenceOverlay";
import { PageViewportParameters } from "../../lib/pdfCoordinateTransform";

// Initialize PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

interface PDFViewerProps {
  blob: Blob;
  filename?: string;
  activeEvidence: {
    page?: number | null;
    bbox?: [number, number, number, number] | number[] | null;
    text_snippet?: string | null;
    ocr_confidence?: number | null;
    type?: string | null;
  } | null;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ blob, filename, activeEvidence }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [zoomScale, setZoomScale] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [viewportParams, setViewportParams] = useState<PageViewportParameters | null>(null);

  // 1. Load PDF document from blob
  useEffect(() => {
    let cancelled = false;
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);
        const arrayBuffer = await blob.arrayBuffer();
        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
        const doc = await loadingTask.promise;
        if (cancelled) return;
        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setCurrentPage(1);
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || "Failed to load PDF document");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadDocument();
    return () => {
      cancelled = true;
    };
  }, [blob]);

  // 2. Auto-jump to evidence page when selected from structured panel
  useEffect(() => {
    if (activeEvidence?.page && activeEvidence.page >= 1 && activeEvidence.page <= totalPages) {
      if (activeEvidence.page !== currentPage) {
        setCurrentPage(activeEvidence.page);
      }
    }
  }, [activeEvidence, totalPages]);

  // 3. Render active page on canvas with DPI scaling and viewport parameter tracking
  const renderPage = useCallback(async () => {
    if (!pdfDoc || !canvasRef.current || !containerRef.current) return;

    try {
      const page = await pdfDoc.getPage(currentPage);
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const rotation = page.rotate || 0;
      const originalViewport = page.getViewport({ scale: 1.0, rotation });

      // Compute display scale based on container width or zoom setting
      const containerWidth = containerRef.current.clientWidth - 48; // padding
      const baseScale = containerWidth > 0 ? (containerWidth / originalViewport.width) : 1.0;
      const effectiveScale = Math.max(baseScale * zoomScale, 0.4);

      const viewport = page.getViewport({ scale: effectiveScale, rotation });

      // High-DPI screen support
      const outputScale = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;

      const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;

      const renderContext = {
        canvasContext: ctx,
        transform: transform || undefined,
        viewport,
      };

      await page.render(renderContext).promise;

      // Update centralized coordinate viewport parameters
      setViewportParams({
        viewportWidth: Math.floor(viewport.width),
        viewportHeight: Math.floor(viewport.height),
        rotation,
        originalWidth: originalViewport.width,
        originalHeight: originalViewport.height,
      });
    } catch (err: any) {
      console.error("PDF render error:", err);
    }
  }, [pdfDoc, currentPage, zoomScale]);

  useEffect(() => {
    renderPage();
  }, [renderPage]);

  // 4. ResizeObserver to re-render when split pane is dragged
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(() => {
      renderPage();
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [renderPage]);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((p) => p - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage((p) => p + 1);
  };

  const handleZoomIn = () => setZoomScale((s) => Math.min(s + 0.2, 2.5));
  const handleZoomOut = () => setZoomScale((s) => Math.max(s - 0.2, 0.5));
  const handleResetZoom = () => setZoomScale(1.0);

  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-lg overflow-hidden select-none"
    >
      {/* Viewer Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-300">
        {/* Document Filename & Page Navigation */}
        <div className="flex items-center gap-3">
          {filename && (
            <div className="flex items-center gap-1.5 text-xs text-slate-300 font-medium truncate max-w-[200px]" title={filename}>
              <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
              <span className="truncate">{filename}</span>
            </div>
          )}

          <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1 || loading}
            className="p-1.5 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
            title="Previous page"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-4 h-4 text-slate-300" />
          </button>
          <span className="font-mono text-slate-200">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= totalPages || loading}
            className="p-1.5 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
            title="Next page"
            aria-label="Next page"
          >
            <ChevronRight className="w-4 h-4 text-slate-300" />
          </button>
        </div>
      </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            disabled={zoomScale <= 0.5 || loading}
            className="p-1.5 rounded hover:bg-slate-800 disabled:opacity-30 transition"
            title="Zoom out"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5 text-slate-300" />
          </button>
          <span className="font-mono text-[11px] w-12 text-center text-slate-400">
            {Math.round(zoomScale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            disabled={zoomScale >= 2.5 || loading}
            className="p-1.5 rounded hover:bg-slate-800 disabled:opacity-30 transition"
            title="Zoom in"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5 text-slate-300" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition ml-1"
            title="Fit width"
            aria-label="Fit width"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Canvas & Overlay Workspace */}
      <div
        tabIndex={0}
        role="region"
        aria-label="Document Page Canvas Container"
        className="relative flex-1 overflow-auto p-4 flex justify-center items-start bg-slate-950/60 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {loading && (
          <div className="flex flex-col items-center justify-center h-64 gap-2 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
            <span className="text-xs">Streaming PDF pages...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-rose-400 bg-rose-950/30 border border-rose-800/50 p-4 rounded-lg text-xs max-w-md my-auto">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && (
          <div className="relative shadow-2xl rounded border border-slate-800/80 bg-white">
            <canvas ref={canvasRef} className="block" />
            {viewportParams && (
              <PDFEvidenceOverlay
                activeEvidence={activeEvidence}
                currentPage={currentPage}
                viewportParams={viewportParams}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
