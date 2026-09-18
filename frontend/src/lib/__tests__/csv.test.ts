import { expect, test } from 'vitest';
import { encodeCSV } from '../csv';
test('CSV preserves punctuation, Unicode, lines and neutralizes formulas', () => {
 expect(encodeCSV([['A,"B"\nC', '=1+1', -2, '\u00e9']])).toBe('\uFEFF"A,""B""\nC","\'=1+1","-2","\u00e9"');
});
