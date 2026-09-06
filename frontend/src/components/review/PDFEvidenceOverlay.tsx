import React from "react";
import {
  transformEvidenceBboxToViewport,
  PageViewportParameters,
  BoundingBoxCoordinates,
} from "../../lib/pdfCoordinateTransform";

interface PDFEvidenceOverlayProps {
  activeEvidence: {
    page?: number | null;
    bbox?: [number, number, number, number] | number[] | null;
    text_snippet?: string | null;
    ocr_confidence?: number | null;
    type?: string | null;
  } | null;
  currentPage: number;
  viewportParams: PageViewportParameters;
}

export const PDFEvidenceOverlay: React.FC<PDFEvidenceOverlayProps> = ({
  activeEvidence,
  currentPage,
  viewportParams,
}) => {
  if (!activeEvidence || activeEvidence.page !== currentPage || !activeEvidence.bbox) {
    return null;
  }

  const coords: BoundingBoxCoordinates | null = transformEvidenceBboxToViewport(
    activeEvidence.bbox,
    viewportParams
  );

  if (!coords) return null;

  const isOCR = activeEvidence.type === "ocr_pdf" || activeEvidence.ocr_confidence !== undefined;

  return (
    <div
      className="absolute inset-0 pointer-events-none z-10"
      style={{
        width: `${viewportParams.viewportWidth}px`,
        height: `${viewportParams.viewportHeight}px`,
      }}
      aria-hidden="true"
    >
      <svg
        className="w-full h-full"
        style={{
          width: `${viewportParams.viewportWidth}px`,
          height: `${viewportParams.viewportHeight}px`,
        }}
      >
        <defs>
          <filter id="glow-pulse" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow
              dx="0"
              dy="0"
              stdDeviation="4"
              floodColor={isOCR ? "#06b6d4" : "#3b82f6"}
              floodOpacity="0.8"
            />
          </filter>
        </defs>

        <rect
          x={coords.x}
          y={coords.y}
          width={Math.max(coords.width, 10)}
          height={Math.max(coords.height, 10)}
          fill={isOCR ? "rgba(6, 182, 212, 0.2)" : "rgba(59, 130, 246, 0.25)"}
          stroke={isOCR ? "#06b6d4" : "#3b82f6"}
          strokeWidth={2}
          strokeDasharray="4 2"
          filter="url(#glow-pulse)"
          rx={3}
          className="animate-pulse"
        />
      </svg>

      {/* Floating Citation Badge / Tooltip */}
      <div
        className="absolute pointer-events-auto bg-slate-900/95 text-white border border-blue-500/50 rounded-md px-2 py-1 text-xs shadow-xl backdrop-blur-md max-w-xs flex flex-col gap-0.5 animate-fadeIn"
        style={{
          left: `${Math.min(Math.max(coords.x, 8), viewportParams.viewportWidth - 160)}px`,
          top: `${Math.max(coords.y - 34, 4)}px`,
        }}
      >
        <div className="flex items-center gap-1.5 font-medium text-[11px] text-blue-300">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          <span>Authoritative Source Evidence (Page {currentPage})</span>
          {isOCR && activeEvidence.ocr_confidence && (
            <span className="ml-auto text-[10px] px-1 py-0.2 bg-cyan-950 text-cyan-300 border border-cyan-700/60 rounded">
              OCR {Math.round(activeEvidence.ocr_confidence * 100)}%
            </span>
          )}
        </div>
        {activeEvidence.text_snippet && (
          <p className="text-slate-300 line-clamp-2 text-[10px] italic">
            "{activeEvidence.text_snippet}"
          </p>
        )}
      </div>
    </div>
  );
};
