/**
 * Backend error message mapping.
 * Translates known API error patterns and detail strings to localized text.
 */

import i18n from "./i18n";

export function translateBackendError(rawMessage: unknown, _t?: any): string {
  if (!rawMessage) return "";
  const lang = (i18n.language || "en").substring(0, 2);
  const isFr = lang === "fr";

  const msg = errorDetail(rawMessage).trim();

  const known: Record<string, string> = {
    "Failed to store quotation document.": "Échec de l’enregistrement du document de l’offre.",
    "Supplier name must not be blank.": "Le nom du fournisseur ne peut pas être vide.",
    "Unstructured PDF extraction requires manual review against the source document.": "L’extraction du PDF non structuré doit être vérifiée avec le document source.",
  };
  if (isFr && known[msg]) return known[msg];

  // Criteria weights validation
  if (
    msg.toLowerCase().includes("criteria weights must") ||
    msg.toLowerCase().includes("must total 100") ||
    msg.toLowerCase().includes("sum to exactly 100")
  ) {
    return isFr
      ? "La somme des pondérations des critères doit être égale à 100 %."
      : "Criteria weights must total 100%.";
  }

  // Missing RFQ title
  if (msg.toLowerCase().includes("specify an rfq title") || msg.toLowerCase().includes("title is required")) {
    return isFr ? "Veuillez indiquer un titre pour l'appel d'offres." : "Please specify an RFQ title.";
  }

  // RFQ Not Found
  if (msg.toLowerCase().includes("rfq not found") || msg.toLowerCase().includes("failed to fetch rfq")) {
    return isFr ? "Appel d'offres introuvable." : "RFQ not found.";
  }

  // Failed to fetch backend
  if (msg.toLowerCase().includes("failed to reach backend api") || msg.toLowerCase().includes("failed to fetch")) {
    return isFr
      ? "Impossible de contacter l'API du serveur."
      : "Failed to reach backend API.";
  }

  // Quotation not found
  if (msg.toLowerCase().includes("quotation not found")) {
    return isFr ? "Offre fournisseur introuvable." : "Quotation not found.";
  }

  // Health check failure
  if (msg.toLowerCase().includes("health check failed")) {
    return isFr ? "Échec de la vérification de l'état du serveur." : "Health check failed.";
  }

  // Fallback to raw message if not in dictionary
  return msg;
}


export function errorDetail(value: unknown): string {
  if (value instanceof Error) return value.message;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(errorDetail).filter(Boolean).join("; ");
  if (value && typeof value === "object") {
    const v = value as Record<string, unknown>;
    return errorDetail(v.detail ?? v.msg ?? v.message);
  }
  return "";
}
