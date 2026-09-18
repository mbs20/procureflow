import { describe, it, expect, beforeEach, afterEach } from "vitest";
import i18n, { detectInitialLanguage, changeLanguage } from "../i18n";
import { en } from "../../locales/en";
import { fr } from "../../locales/fr";
import {
  formatNumber,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
  formatActor,
  getCurrentLocale,
} from "../formatters";

import {
  translateQuotationStatus,
  translateRFQStatus,
  translateAwardStatus,
  translateKnockoutStatus,
  translateClaimType,
  translateGroundingStatus,
} from "../statusTranslations";
import { translateBackendError } from "../errorMessageMap";

// Set up mock window, localStorage and document if running in node env
const mockStorage: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, val: string) => {
    mockStorage[key] = String(val);
  },
  removeItem: (key: string) => {
    delete mockStorage[key];
  },
  clear: () => {
    for (const k of Object.keys(mockStorage)) {
      delete mockStorage[k];
    }
  },
};

if (typeof globalThis.localStorage === "undefined") {
  (globalThis as any).localStorage = mockLocalStorage;
}
if (typeof (globalThis as any).window === "undefined") {
  (globalThis as any).window = { localStorage: mockLocalStorage };
} else if (!(globalThis as any).window.localStorage) {
  (globalThis as any).window.localStorage = mockLocalStorage;
}
if (typeof (globalThis as any).document === "undefined") {
  (globalThis as any).document = {
    documentElement: { lang: "en" },
  };
}

describe("i18n System & Translation Dictionaries", () => {
  beforeEach(async () => {
    mockLocalStorage.clear();
    await changeLanguage("en");
  });

  afterEach(async () => {
    await changeLanguage("en");
  });

  describe("Dictionary Parity", () => {
    it("has all expected namespaces in both English and French", () => {
      const enNamespaces = Object.keys(en);
      const frNamespaces = Object.keys(fr);

      expect(enNamespaces.sort()).toEqual(frNamespaces.sort());

      const expectedNamespaces = [
        "common",
        "nav",
        "dashboard",
        "rfq",
        "quotations",
        "review",
        "matrix",
        "scoring",
        "decision",
        "audit",
      ];

      for (const ns of expectedNamespaces) {
        expect(enNamespaces).toContain(ns);
        expect(frNamespaces).toContain(ns);
      }
    });

    function verifyParity(source: any, target: any, path: string = "") {
      for (const key of Object.keys(source)) {
        const fullPath = path ? `${path}.${key}` : key;
        expect(
          target[key],
          `Missing translation for key "${fullPath}"`
        ).toBeDefined();

        if (typeof source[key] === "object" && source[key] !== null) {
          expect(typeof target[key]).toBe("object");
          verifyParity(source[key], target[key], fullPath);
        } else {
          expect(typeof target[key]).toBe("string");
          expect(target[key].trim().length).toBeGreaterThan(0);
        }
      }
    }

    it("verifies all keys in English exist in French dictionary", () => {
      verifyParity(en, fr);
    });

    it("verifies all keys in French exist in English dictionary", () => {
      verifyParity(fr, en);
    });
  });


  describe("Locale Detection & Language Switching", () => {
    it("detects saved language from localStorage", () => {
      localStorage.setItem("procureflow_language", "fr");
      expect(detectInitialLanguage()).toBe("fr");

      localStorage.setItem("procureflow_language", "en");
      expect(detectInitialLanguage()).toBe("en");
    });

    it("changes language, updates localStorage and HTML lang attribute", () => {
      changeLanguage("fr");
      expect(i18n.language).toBe("fr");
      expect(localStorage.getItem("procureflow_language")).toBe("fr");
      expect(document.documentElement.lang).toBe("fr");

      changeLanguage("en");
      expect(i18n.language).toBe("en");
      expect(localStorage.getItem("procureflow_language")).toBe("en");
      expect(document.documentElement.lang).toBe("en");
    });
  });

  describe("Formatters (Intl Localization)", () => {
    it("returns correct locale for en and fr", () => {
      changeLanguage("en");
      expect(getCurrentLocale()).toBe("en-US");

      changeLanguage("fr");
      expect(getCurrentLocale()).toBe("fr-FR");
    });

    it("formats numbers according to active language", () => {
      changeLanguage("en");
      const formattedEn = formatNumber(1250000.5, { minimumFractionDigits: 2 });
      expect(formattedEn).toContain("1,250,000.50");

      changeLanguage("fr");
      const formattedFr = formatNumber(1250000.5, { minimumFractionDigits: 2 });
      // French uses non-breaking space (or standard space) and comma
      expect(formattedFr).toMatch(/1[\s\u00a0\u202f]250[\s\u00a0\u202f]000,50/);
    });

    it("formats currencies without altering currency code", () => {
      changeLanguage("en");
      expect(formatCurrency(4500.75, "USD")).toContain("4,500.75 USD");
      expect(formatCurrency(4500.75, "EUR")).toContain("4,500.75 EUR");

      changeLanguage("fr");
      const resFr = formatCurrency(4500.75, "EUR");
      expect(resFr).toMatch(/4[\s\u00a0\u202f]500,75 EUR/);
    });

    it("formats percentages correctly", () => {
      changeLanguage("en");
      expect(formatPercent(0.25)).toContain("25");

      changeLanguage("fr");
      expect(formatPercent(0.25)).toContain("25");
    });

    it("formats dates and date-times gracefully", () => {
      const isoDate = "2026-09-16T14:30:00Z";
      changeLanguage("en");
      const dEn = formatDate(isoDate);
      expect(dEn).toBeTruthy();
      expect(dEn).not.toBe("-");

      changeLanguage("fr");
      const dFr = formatDate(isoDate);
      expect(dFr).toBeTruthy();
      expect(dFr).not.toBe("-");
      expect(formatDateTime(isoDate)).toBeTruthy();
    });

    it("handles null or undefined numeric values safely", () => {
      expect(formatNumber(null)).toBe("-");
      expect(formatNumber(undefined)).toBe("-");
      expect(formatCurrency(null)).toBe("-");
      expect(formatDate(null)).toBe("-");
    });
  });

  describe("Status Translations", () => {
    it("translates Quotation statuses", () => {
      changeLanguage("en");
      expect(translateQuotationStatus("NEEDS_REVIEW")).toBe("Needs review");
      expect(translateQuotationStatus("APPROVED")).toBe("Approved");

      changeLanguage("fr");
      expect(translateQuotationStatus("NEEDS_REVIEW")).toBe("À vérifier");
      expect(translateQuotationStatus("APPROVED")).toBe("Approuvé");
    });

    it("translates RFQ statuses", () => {
      changeLanguage("en");
      expect(translateRFQStatus("evaluating")).toBe("Evaluating");
      expect(translateRFQStatus("decided")).toBe("Decided");
      expect(translateRFQStatus("active", true)).toBe("Archived");

      changeLanguage("fr");
      expect(translateRFQStatus("evaluating")).toBe("En évaluation");
      expect(translateRFQStatus("decided")).toBe("Attribué");
      expect(translateRFQStatus("active", true)).toBe("Archivé");
    });

    it("translates Award statuses", () => {
      changeLanguage("en");
      expect(translateAwardStatus("CONFIRMED")).toBe("Confirmed");
      expect(translateAwardStatus("REVOKED")).toBe("Revoked");

      changeLanguage("fr");
      expect(translateAwardStatus("CONFIRMED")).toBe("Confirmé");
      expect(translateAwardStatus("REVOKED")).toBe("Révoqué");
    });

    it("translates Knockout statuses", () => {
      changeLanguage("en");
      expect(translateKnockoutStatus(true)).toBe("Knockout failed");
      expect(translateKnockoutStatus(false)).toBe("Eligible");
      expect(translateKnockoutStatus("eligible")).toBe("Eligible");
      expect(translateKnockoutStatus("knockout_failed")).toBe("Knockout failed");

      changeLanguage("fr");
      expect(translateKnockoutStatus(true)).toBe("Critère éliminatoire non satisfait");
      expect(translateKnockoutStatus(false)).toBe("Éligible");
      expect(translateKnockoutStatus("eligible")).toBe("Éligible");
      expect(translateKnockoutStatus("knockout_failed")).toBe("Critère éliminatoire non satisfait");
    });

    it("translates Claim types", () => {
      changeLanguage("en");
      expect(translateClaimType("quantitative")).toBe("Quantitative");
      expect(translateClaimType("tradeoff")).toBe("Trade-off");

      changeLanguage("fr");
      expect(translateClaimType("quantitative")).toBe("Quantitatif");
      expect(translateClaimType("tradeoff")).toBe("Compromis");
    });

    it("translates Grounding statuses", () => {
      changeLanguage("en");
      expect(translateGroundingStatus("VERIFIED")).toBe("Verified");
      expect(translateGroundingStatus("UNSUPPORTED")).toBe("Unsupported");

      changeLanguage("fr");
      expect(translateGroundingStatus("VERIFIED")).toBe("Vérifié");
      expect(translateGroundingStatus("UNSUPPORTED")).toBe("Non étayé");
    });
  });

  describe("Backend Error Mapping", () => {
    it("translates criteria weight validation errors", () => {
      changeLanguage("en");
      expect(translateBackendError("Criteria weights must total 100")).toBe(
        "Criteria weights must total 100%."
      );

      changeLanguage("fr");
      expect(translateBackendError("Criteria weights must total 100")).toBe(
        "La somme des pondérations des critères doit être égale à 100 %."
      );
    });

    it("translates missing RFQ title error", () => {
      changeLanguage("en");
      expect(translateBackendError("Please specify an RFQ title")).toBe(
        "Please specify an RFQ title."
      );

      changeLanguage("fr");
      expect(translateBackendError("Please specify an RFQ title")).toBe(
        "Veuillez indiquer un titre pour l'appel d'offres."
      );
    });

    it("translates RFQ not found and network errors", () => {
      changeLanguage("en");
      expect(translateBackendError("RFQ not found with ID")).toBe("RFQ not found.");
      expect(translateBackendError("Failed to reach backend API")).toBe("Failed to reach backend API.");

      changeLanguage("fr");
      expect(translateBackendError("RFQ not found with ID")).toBe("Appel d'offres introuvable.");
      expect(translateBackendError("Failed to reach backend API")).toBe("Impossible de contacter l'API du serveur.");
    });
  });

  describe("Actor & Credential Protection", () => {
    it("redacts secret dev API key values to Development API Principal", () => {
      expect(formatActor("procureflow_dev_api_key_12345")).toBe("Development API Principal");
      expect(formatActor("dev_api_key_abc")).toBe("Development API Principal");
      expect(formatActor("sk_live_123456789")).toBe("Development API Principal");
      expect(formatActor("pk_test_987654321")).toBe("Development API Principal");
    });

    it("redacts generic secret API keys to Authenticated API Principal", () => {
      expect(formatActor("procureflow_sec_9999")).toBe("Authenticated API Principal");
      expect(formatActor("prod_api_key_secret")).toBe("Authenticated API Principal");
    });

    it("preserves standard user names and handles missing actors", () => {
      expect(formatActor("buyer_admin")).toBe("buyer_admin");
      expect(formatActor("officer_1")).toBe("officer_1");
      expect(formatActor("")).toBe("System User");
      expect(formatActor(null)).toBe("System User");
      expect(formatActor(undefined)).toBe("System User");
    });
  });

  describe("Regression: Specific Keys and Clean Formatting", () => {
    it("resolves specific QA keys in English and French", () => {
      changeLanguage("en");
      expect(i18n.t("scoring.supplierHeader")).toBe("Supplier");
      expect(i18n.t("scoring.activeBadge")).toBe("Active");
      expect(i18n.t("scoring.eligible")).toBe("Eligible");
      expect(i18n.t("matrix.referenceCurrency")).toBe("Reference Currency");
      expect(i18n.t("matrix.paymentTerms")).toBe("Payment Terms");
      expect(i18n.t("matrix.coverageLabel")).toBe("Coverage");
      expect(i18n.t("matrix.quotedOriginal")).toBe("Quoted:");
      expect(i18n.t("matrix.sourcePage")).toBe("Source Page");
      expect(i18n.t("review.leadTimeDays")).toBe("Lead Time (Days)");
      expect(i18n.t("review.addItem")).toBe("Add Item");

      changeLanguage("fr");
      expect(i18n.t("scoring.supplierHeader")).toBe("Fournisseur");
      expect(i18n.t("scoring.activeBadge")).toBe("Actif");
      expect(i18n.t("scoring.eligible")).toBe("Éligible");
      expect(i18n.t("matrix.referenceCurrency")).toBe("Devise de référence");
      expect(i18n.t("matrix.paymentTerms")).toBe("Conditions de paiement");
      expect(i18n.t("matrix.coverageLabel")).toBe("Couverture");
      expect(i18n.t("matrix.quotedOriginal")).toBe("Offert :");
      expect(i18n.t("matrix.sourcePage")).toBe("Page source");
      expect(i18n.t("review.leadTimeDays")).toBe("Délai de livraison (jours)");
      expect(i18n.t("review.addItem")).toBe("Ajouter l'article");
    });

    it("correctly interpolates placeholders without leftover brackets", () => {
      changeLanguage("en");
      const frozenEn = i18n.t("scoring.frozenRunPrefix", { version: "1.0" });
      expect(frozenEn).toBe("Frozen Run v1.0");
      expect(frozenEn).not.toContain("{{");

      const snapEn = i18n.t("scoring.snapshotOption", { version: 1, title: "Baseline" });
      expect(snapEn).toBe("Snapshot v1 (Baseline)");
      expect(snapEn).not.toContain("{{");

      const calcEn = i18n.t("review.defaultCalculated", { amount: "100.00 USD" });
      expect(calcEn).toBe("Default: 100.00 USD");
      expect(calcEn).not.toContain("{{");

      changeLanguage("fr");
      const frozenFr = i18n.t("scoring.frozenRunPrefix", { version: "1.0" });
      expect(frozenFr).toBe("Évaluation figée v1.0");
      expect(frozenFr).not.toContain("{{");

      const snapFr = i18n.t("scoring.snapshotOption", { version: 1, title: "Référence" });
      expect(snapFr).toBe("Instantané v1 (Référence)");
      expect(snapFr).not.toContain("{{");

      const calcFr = i18n.t("review.defaultCalculated", { amount: "100,00 USD" });
      expect(calcFr).toBe("Par défaut : 100,00 USD");
      expect(calcFr).not.toContain("{{");
    });
  });
});

