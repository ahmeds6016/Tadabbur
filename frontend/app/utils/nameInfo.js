import nameData from '../data/name_info.json';

/**
 * Look up name info from the offline dictionary.
 * Searches canonical names and aliases (case-insensitive).
 * Returns the matching entry object, or null if not found.
 */
export function getNameInfo(firstName) {
  if (!firstName || typeof firstName !== 'string') return null;
  const normalized = firstName.trim().toLowerCase().replace(/[^a-z'-]/g, '');
  if (normalized.length < 2) return null;

  for (const entry of nameData) {
    if (entry.canonical.toLowerCase() === normalized) return entry;
    if (entry.aliases.includes(normalized)) return entry;
  }
  return null;
}

/**
 * Validate a first-name-only input.
 * Returns { valid, error, cleaned }.
 * Empty input is valid (field is optional).
 */
export function validateFirstName(value) {
  const trimmed = (value || '').trim();
  if (!trimmed) return { valid: true, error: null, cleaned: '' };
  if (/\s/.test(trimmed)) return { valid: false, error: 'First name only (no last name).', cleaned: trimmed };
  if (trimmed.length < 2) return { valid: false, error: 'Name must be at least 2 characters.', cleaned: trimmed };
  if (trimmed.length > 30) return { valid: false, error: 'Name must be 30 characters or fewer.', cleaned: trimmed };
  if (!/^[a-zA-Z\u0600-\u06FF'-]+$/.test(trimmed)) return { valid: false, error: 'Letters, hyphens, and apostrophes only.', cleaned: trimmed };
  return { valid: true, error: null, cleaned: trimmed };
}
