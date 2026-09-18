/** Strict decimal input parsing: never treat missing or malformed values as zero. */
export function parseReviewNumber(value: unknown, options: { integer?: boolean; positive?: boolean } = {}): number | null {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  const text = String(value).trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(text)) return null;
  const number = Number(text);
  if (!Number.isFinite(number) || number < 0 || (options.positive && number === 0)) return null;
  if (options.integer && !Number.isSafeInteger(number)) return null;
  return number;
}
