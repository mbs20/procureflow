import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "../locales/en";
import { fr } from "../locales/fr";

export const STORAGE_KEY = "procureflow_language";

export function detectInitialLanguage(): "en" | "fr" {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "fr") {
        return saved;
      }
    }
    if (typeof navigator !== "undefined" && navigator.language) {
      const browserLang = navigator.language.toLowerCase();
      if (browserLang.startsWith("fr")) {
        return "fr";
      }
    }
  } catch {
    // Fallback if local storage or navigator is unavailable
  }
  return "en";
}

const initialLanguage = detectInitialLanguage();

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      fr: { translation: fr },
    },
    lng: initialLanguage,
    fallbackLng: "en",
    interpolation: {
      escapeValue: false, // React already protects from XSS
    },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEY,
      caches: ["localStorage"],
    },
  });

// Keep document.documentElement.lang synchronized
if (typeof document !== "undefined") {
  document.documentElement.lang = initialLanguage;
}

i18n.on("languageChanged", (lng) => {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, lng);
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = lng;
    }
  } catch {
    // Ignore storage write issues in restricted contexts
  }
});

export function changeLanguage(lng: string): Promise<any> {
  return i18n.changeLanguage(lng);
}

export default i18n;
