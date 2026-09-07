import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { RFQListPage } from "./pages/RFQListPage";
import { RFQDetailPage } from "./pages/RFQDetailPage";
import { QuotationsPage } from "./pages/QuotationsPage";
import { ReviewWorkspacePage } from "./pages/ReviewWorkspacePage";
import { ComparisonMatrixPage } from "./pages/ComparisonMatrixPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="quotations/:id/review" element={<ReviewWorkspacePage />} />
        <Route path="review/:id" element={<ReviewWorkspacePage />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="rfqs" element={<RFQListPage />} />
          <Route path="rfqs/:id" element={<RFQDetailPage />} />
          <Route path="rfqs/:id/matrix" element={<ComparisonMatrixPage />} />
          <Route path="quotations" element={<QuotationsPage />} />
          <Route path="review" element={<QuotationsPage />} />
          <Route path="matrix" element={<ComparisonMatrixPage />} />
          <Route path="matrix/:id" element={<ComparisonMatrixPage />} />
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
