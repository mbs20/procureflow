import { describe, it, expect } from 'vitest';
import { parseReviewNumber } from '../reviewNumbers';
describe('strict review numeric parsing', () => {
  it('accepts complete finite decimal numbers and preserves zero', () => {
    expect(parseReviewNumber('2.50')).toBe(2.5);
    expect(parseReviewNumber('0', { integer: true })).toBe(0);
  });
  it.each(['', ' ', '12oops', 'Infinity', 'NaN', '0x10', '1e999', Infinity, NaN, null, undefined, false])('rejects invalid input %s instead of silently coercing it', value => {
    expect(parseReviewNumber(value)).toBeNull();
  });
  it('rejects negative and fractional lead times', () => {
    expect(parseReviewNumber('-1')).toBeNull();
    expect(parseReviewNumber('1.5', { integer: true })).toBeNull();
    expect(parseReviewNumber('0', { positive: true })).toBeNull();
    expect(parseReviewNumber('9007199254740992', { integer: true })).toBeNull();
  });
});
