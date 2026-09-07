import React, { useEffect, useState, useRef } from "react";
import * as XLSX from "xlsx";
import Papa from "papaparse";
import { FileSpreadsheet, RefreshCw, AlertCircle } from "lucide-react";

interface SpreadsheetViewerProps {
  blob: Blob;
  filename?: string;
  activeEvidence: {
    sheet?: string | null;
    row?: number | null;
    cells?: string[] | null;
    type?: string | null;
  } | null;
}

interface SheetData {
  sheetNames: string[];
  activeSheet: string;
  rows: string[][];
}

export const SpreadsheetViewer: React.FC<SpreadsheetViewerProps> = ({
  blob,
  filename = "",
  activeEvidence,
}) => {
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());

  const [sheetData, setSheetData] = useState<SheetData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Read-only parsing of XLSX or CSV blob
  useEffect(() => {
    let cancelled = false;

    const parseSpreadsheet = async () => {
      try {
        setLoading(true);
        setError(null);

        const isCSV =
          filename.toLowerCase().endsWith(".csv") ||
          blob.type.includes("csv") ||
          blob.type.includes("text");

        if (isCSV) {
          const text = await blob.text();
          const parsed = Papa.parse<string[]>(text, { skipEmptyLines: false });
          if (cancelled) return;
          setSheetData({
            sheetNames: ["CSV Data"],
            activeSheet: "CSV Data",
            rows: parsed.data as string[][],
          });
        } else {
          // XLSX workbook
          const arrayBuffer = await blob.arrayBuffer();
          const workbook = XLSX.read(arrayBuffer, { type: "array" });
          if (cancelled) return;

          const sheetNames = workbook.SheetNames;
          const initialSheet =
            activeEvidence?.sheet && sheetNames.includes(activeEvidence.sheet)
              ? activeEvidence.sheet
              : sheetNames[0] || "Sheet1";

          const ws = workbook.Sheets[initialSheet];
          const rawRows: string[][] = XLSX.utils.sheet_to_json(ws, {
            header: 1,
            defval: "",
          });

          setSheetData({
            sheetNames,
            activeSheet: initialSheet,
            rows: rawRows,
          });
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || "Failed to parse spreadsheet");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    parseSpreadsheet();
    return () => {
      cancelled = true;
    };
  }, [blob, filename]);

  // 2. Switch sheet when activeEvidence points to another sheet
  useEffect(() => {
    if (
      sheetData &&
      activeEvidence?.sheet &&
      activeEvidence.sheet !== sheetData.activeSheet &&
      sheetData.sheetNames.includes(activeEvidence.sheet)
    ) {
      // Switch to targeted sheet
      const loadSheet = async () => {
        try {
          const arrayBuffer = await blob.arrayBuffer();
          const workbook = XLSX.read(arrayBuffer, { type: "array" });
          const ws = workbook.Sheets[activeEvidence.sheet!];
          const rawRows: string[][] = XLSX.utils.sheet_to_json(ws, {
            header: 1,
            defval: "",
          });
          setSheetData((prev) =>
            prev
              ? {
                  ...prev,
                  activeSheet: activeEvidence.sheet!,
                  rows: rawRows,
                }
              : null
          );
        } catch (e) {
          console.error("Failed to switch sheet:", e);
        }
      };
      loadSheet();
    }
  }, [activeEvidence, blob, sheetData]);

  // 3. Auto-scroll to cited row when activeEvidence changes
  useEffect(() => {
    if (activeEvidence?.row && rowRefs.current.has(activeEvidence.row)) {
      const rowElem = rowRefs.current.get(activeEvidence.row);
      if (rowElem) {
        rowElem.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeEvidence]);

  const handleSheetSwitch = async (sheetName: string) => {
    if (!sheetData || sheetName === sheetData.activeSheet) return;
    try {
      setLoading(true);
      const arrayBuffer = await blob.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer, { type: "array" });
      const ws = workbook.Sheets[sheetName];
      const rawRows: string[][] = XLSX.utils.sheet_to_json(ws, {
        header: 1,
        defval: "",
      });
      setSheetData({
        ...sheetData,
        activeSheet: sheetName,
        rows: rawRows,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Helper to get Excel column letter (0 -> A, 1 -> B, ...)
  const getColLetter = (colIndex: number): string => {
    let letter = "";
    let temp = colIndex;
    while (temp >= 0) {
      letter = String.fromCharCode((temp % 26) + 65) + letter;
      temp = Math.floor(temp / 26) - 1;
    }
    return letter;
  };

  const isCellCited = (rowIdx: number, colIdx: number): boolean => {
    if (!activeEvidence || !activeEvidence.cells) return false;
    const cellCoord = `${getColLetter(colIdx)}${rowIdx + 1}`;
    return activeEvidence.cells.includes(cellCoord);
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-lg overflow-hidden select-none">
      {/* Top Header / Sheet Switcher */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-300 overflow-x-auto">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">
            Read-Only Document Source: {filename || "Spreadsheet"}
          </span>
        </div>

        {sheetData && sheetData.sheetNames.length > 1 && (
          <div className="flex items-center gap-1">
            {sheetData.sheetNames.map((name) => (
              <button
                key={name}
                onClick={() => handleSheetSwitch(name)}
                className={`px-2.5 py-1 rounded text-xs transition ${
                  sheetData.activeSheet === name
                    ? "bg-emerald-950 text-emerald-300 border border-emerald-700 font-medium"
                    : "hover:bg-slate-800 text-slate-400"
                }`}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Spreadsheet Grid Container */}
      <div
        ref={tableContainerRef}
        tabIndex={0}
        role="region"
        aria-label="Spreadsheet Grid Table Container"
        className="flex-1 overflow-auto bg-slate-950 p-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      >
        {loading && (
          <div className="flex flex-col items-center justify-center h-64 gap-2 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-emerald-500" />
            <span className="text-xs">Parsing spreadsheet grid...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-rose-400 bg-rose-950/30 border border-rose-800/50 p-4 rounded-lg text-xs max-w-md my-auto">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && sheetData && (
          <div className="inline-block min-w-full align-middle">
            <table className="min-w-full border-collapse font-mono text-[11px] text-slate-300">
              <thead>
                <tr className="bg-slate-900/90 sticky top-0 z-10 border-b border-slate-800">
                  <th className="w-12 px-2 py-1.5 text-center text-slate-500 font-medium border-r border-slate-800 bg-slate-900">
                    #
                  </th>
                  {sheetData.rows[0]?.map((_, colIdx) => (
                    <th
                      key={colIdx}
                      className="px-3 py-1.5 text-left text-slate-400 font-medium border-r border-slate-800"
                    >
                      {getColLetter(colIdx)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sheetData.rows.map((row, rowIdx) => {
                  const rowNumber = rowIdx + 1;
                  const isRowCited = activeEvidence?.row === rowNumber;

                  return (
                    <tr
                      key={rowIdx}
                      ref={(el) => {
                        if (el) rowRefs.current.set(rowNumber, el);
                        else rowRefs.current.delete(rowNumber);
                      }}
                      className={`border-b border-slate-800/50 transition-colors ${
                        isRowCited
                          ? "bg-blue-950/40 text-blue-100 font-semibold"
                          : "hover:bg-slate-900/60"
                      }`}
                    >
                      {/* Row Index Number */}
                      <td
                        className={`w-12 px-2 py-1 text-center font-bold border-r border-slate-800 select-none ${
                          isRowCited
                            ? "bg-blue-900/60 text-blue-300 border-blue-600"
                            : "bg-slate-900/40 text-slate-500"
                        }`}
                      >
                        {rowNumber}
                      </td>

                      {/* Row Cells */}
                      {row.map((cellValue, colIdx) => {
                        const cellCited = isCellCited(rowIdx, colIdx);

                        return (
                          <td
                            key={colIdx}
                            className={`px-3 py-1 border-r border-slate-800/40 truncate max-w-xs ${
                              cellCited
                                ? "bg-blue-600/30 text-blue-200 ring-2 ring-blue-500 ring-inset rounded-sm"
                                : ""
                            }`}
                            title={String(cellValue)}
                          >
                            {String(cellValue)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
