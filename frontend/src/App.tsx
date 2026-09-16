import React from "react";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { RFQListPage } from "./pages/RFQListPage";
import { RFQDetailPage } from "./pages/RFQDetailPage";
import { QuotationsPage } from "./pages/QuotationsPage";
import { ReviewWorkspacePage } from "./pages/ReviewWorkspacePage";
import { ComparisonMatrixPage } from "./pages/ComparisonMatrixPage";
import { ScoringEvaluationPage } from "./pages/ScoringEvaluationPage";
import { DecisionWorkspacePage } from "./pages/DecisionWorkspacePage";

const AuditPlaceholder: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="glass-card rounded-xl p-8 text-center space-y-3">
      <h2 className="text-xl font-bold text-white">{t("audit.title")}</h2>
      <p className="text-sm text-muted-foreground max-w-md mx-auto">
        {t("audit.desc")}
      </p>
    </div>
  );
};

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
          <Route path="rfqs/:id/scoring" element={<ScoringEvaluationPage />} />
          <Route path="rfqs/:id/decisions" element={<DecisionWorkspacePage />} />
          <Route path="quotations" element={<QuotationsPage />} />
          <Route path="review" element={<QuotationsPage />} />
          <Route path="matrix" element={<ComparisonMatrixPage />} />
          <Route path="matrix/:id" element={<ComparisonMatrixPage />} />
          <Route path="scoring" element={<ScoringEvaluationPage />} />
          <Route path="scoring/:id" element={<ScoringEvaluationPage />} />
          <Route path="decisions" element={<DecisionWorkspacePage />} />
          <Route path="decisions/:id" element={<DecisionWorkspacePage />} />
          <Route path="audit" element={<AuditPlaceholder />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
