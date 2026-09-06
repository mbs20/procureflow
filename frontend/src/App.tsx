import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { RFQListPage } from "./pages/RFQListPage";
import { RFQDetailPage } from "./pages/RFQDetailPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="rfqs" element={<RFQListPage />} />
          <Route path="rfqs/:id" element={<RFQDetailPage />} />
          <Route
            path="quotations"
            element={
              <div className="glass-card rounded-xl p-8 text-center space-y-3">
                <h2 className="text-xl font-bold text-white">Document Ingestion Pipeline</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Multi-supplier document uploads (PDF, XLSX, CSV) and asynchronous Celery processing.
                </p>
              </div>
            }
          />
          <Route
            path="review"
            element={
              <div className="glass-card rounded-xl p-8 text-center space-y-3">
                <h2 className="text-xl font-bold text-white">Human-in-the-Loop Review</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Side-by-side original document viewer with editable extracted fields and confidence indicators.
                </p>
              </div>
            }
          />
          <Route
            path="matrix"
            element={
              <div className="glass-card rounded-xl p-8 text-center space-y-3">
                <h2 className="text-xl font-bold text-white">Normalized Comparison Matrix</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Apples-to-apples comparison table across currencies, delivery lead times, and terms.
                </p>
              </div>
            }
          />
          <Route
            path="decisions"
            element={
              <div className="glass-card rounded-xl p-8 text-center space-y-3">
                <h2 className="text-xl font-bold text-white">Decisions & Award Records</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Deterministic scoring ranks, AI explanation narratives, and immutable decision justifications.
                </p>
              </div>
            }
          />
          <Route
            path="audit"
            element={
              <div className="glass-card rounded-xl p-8 text-center space-y-3">
                <h2 className="text-xl font-bold text-white">Immutable Audit Trail</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Append-only event stream tracking all extractions, modifications, and evaluations.
                </p>
              </div>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
