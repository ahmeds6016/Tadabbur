const DOUBLE_QUOTES = /["“”]/g;

// Translations of a verse that continues speech from a neighbouring verse carry a
// lone opening or closing quote. Drop it so the display wrapper's quotes stay balanced.
export function displayTranslation(text) {
  if (typeof text !== 'string') return '';
  const trimmed = text.trim();
  if ((trimmed.match(DOUBLE_QUOTES) || []).length % 2 === 0) return trimmed;
  if (/["”]$/.test(trimmed)) return trimmed.slice(0, -1).trimEnd();
  if (/^["“]/.test(trimmed)) return trimmed.slice(1).trimStart();
  return trimmed;
}
