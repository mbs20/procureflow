/**
 * Visual translation helpers for API statuses and enum values.
 * Stored database/API values remain unmodified; display strings are localized.
 */

import i18n from "./i18n";

export function translateQuotationStatus(status: string | null | undefined, _t?: any): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  switch (status?.toUpperCase()) {
    case "DRAFT":
      return isFr ? "Brouillon" : "Draft";
    case "PROCESSING":
      return isFr ? "En cours de traitement" : "Processing";
    case "NEEDS_REVIEW":
      return isFr ? "À vérifier" : "Needs review";
    case "APPROVED":
      return isFr ? "Approuvé" : "Approved";
    case "REJECTED":
      return isFr ? "Rejeté" : "Rejected";
    case "FAILED":
      return isFr ? "Échoué" : "Failed";
    default:
      return status || "-";
  }
}

export function translateRFQStatus(status: string | null | undefined, isArchivedOrT?: boolean | any): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  if (typeof isArchivedOrT === "boolean" && isArchivedOrT) {
    return isFr ? "Archivé" : "Archived";
  }

  switch (status?.toLowerCase()) {
    case "draft":
      return isFr ? "Brouillon" : "Draft";
    case "active":
      return isFr ? "Actif" : "Active";
    case "evaluating":
      return isFr ? "En évaluation" : "Evaluating";
    case "decided":
      return isFr ? "Attribué" : "Decided";
    case "archived":
      return isFr ? "Archivé" : "Archived";
    default:
      return status || "-";
  }
}

export function translateAwardStatus(status: string | null | undefined, _t?: any): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  switch (status?.toUpperCase()) {
    case "PROPOSED":
      return isFr ? "Proposé" : "Proposed";
    case "CONFIRMED":
      return isFr ? "Confirmé" : "Confirmed";
    case "REVOKED":
      return isFr ? "Révoqué" : "Revoked";
    case "SUPERSEDED":
      return isFr ? "Remplacé" : "Superseded";
    case "REVISED":
      return isFr ? "Révisé" : "Revised";
    default:
      return status || "-";
  }
}

export function translateKnockoutStatus(
  statusOrFailed: boolean | string | null | undefined,
  _t?: any
): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  if (typeof statusOrFailed === "boolean") {
    return statusOrFailed
      ? (isFr ? "Critère éliminatoire non satisfait" : "Knockout failed")
      : (isFr ? "Éligible" : "Eligible");
  }

  const s = String(statusOrFailed || "").toLowerCase();
  if (s === "eligible") {
    return isFr ? "Éligible" : "Eligible";
  }
  if (s.includes("knockout") || s.includes("ineligible") || s === "failed") {
    return isFr ? "Critère éliminatoire non satisfait" : "Knockout failed";
  }

  return statusOrFailed ? String(statusOrFailed) : "-";
}

export function translateClaimType(type: string | null | undefined, _t?: any): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  switch (type?.toLowerCase()) {
    case "quantitative":
      return isFr ? "Quantitatif" : "Quantitative";
    case "tradeoff":
      return isFr ? "Compromis" : "Trade-off";
    case "risk":
      return isFr ? "Risque" : "Risk";
    case "recommendation":
      return isFr ? "Recommandation" : "Recommendation";
    default:
      return type || "-";
  }
}

export function translateGroundingStatus(status: string | null | undefined, _t?: any): string {
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  switch (status?.toUpperCase()) {
    case "VERIFIED":
      return isFr ? "Vérifié" : "Verified";
    case "GROUNDED":
      return isFr ? "Étayé" : "Grounded";
    case "UNGROUNDED":
      return isFr ? "Non étayé" : "Ungrounded";
    case "DISCREPANCY":
      return isFr ? "Divergence" : "Discrepancy";
    case "UNSUPPORTED":
      return isFr ? "Non étayé" : "Unsupported";
    default:
      return status || "-";
  }
}

