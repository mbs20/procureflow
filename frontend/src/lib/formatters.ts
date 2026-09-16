/**
 * ProcureFlow Display Formatters
 *
 * Localizes display formatting for numbers, currencies, dates, and percentages
 * using standard Intl APIs without modifying underlying numeric or business data.
 */

import i18n from "./i18n";

export function getCurrentLocale(): string {
  const lang = i18n.language || "en";
  return lang.startsWith("fr") ? "fr-FR" : "en-US";
}

/**
 * Format a number with localized thousands and decimal separators.
 * English: 1,250.50
 * French: 1 250,50
 */
export function formatNumber(
  value: number | string | null | undefined,
  options?: Intl.NumberFormatOptions,
  overrideLocale?: string
): string {
  if (value === null || value === undefined || value === "") return "-";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return String(value);

  const locale = overrideLocale || getCurrentLocale();
  return new Intl.NumberFormat(locale, options).format(num);
}

/**
 * Format currency with localized number formatting and standard currency code.
 * English: 1,250.50 USD
 * French: 1 250,50 USD
 */
export function formatCurrency(
  amount: number | string | null | undefined,
  currency?: string | null,
  overrideLocale?: string
): string {
  if (amount === null || amount === undefined || amount === "") return "-";
  const num = typeof amount === "number" ? amount : Number(amount);
  const currCode = currency || "USD";
  if (isNaN(num)) return `${amount} ${currCode}`;

  const locale = overrideLocale || getCurrentLocale();
  const formattedNumber = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  return `${formattedNumber} ${currCode}`;
}

/**
 * Format date in localized human-readable style.
 * English: September 16, 2026
 * French: 16 septembre 2026
 */
export function formatDate(
  date: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  overrideLocale?: string
): string {
  if (!date) return "-";
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return String(date);

  const locale = overrideLocale || getCurrentLocale();
  const defaultOptions: Intl.DateTimeFormatOptions = options || {
    year: "numeric",
    month: "short",
    day: "numeric",
  };

  return new Intl.DateTimeFormat(locale, defaultOptions).format(d);
}

/**
 * Format date with time.
 */
export function formatDateTime(
  date: string | Date | null | undefined,
  overrideLocale?: string
): string {
  return formatDate(
    date,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
    overrideLocale
  );
}

/**
 * Format percentage.
 */
export function formatPercent(
  value: number | string | null | undefined,
  decimals: number = 0,
  overrideLocale?: string
): string {
  if (value === null || value === undefined || value === "") return "-";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return `${value}%`;

  const isRatio = Math.abs(num) > 0 && Math.abs(num) <= 1;
  const percentVal = isRatio ? num * 100 : num;

  const locale = overrideLocale || getCurrentLocale();
  const formattedNumber = new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(percentVal);

  return `${formattedNumber} %`;
}
