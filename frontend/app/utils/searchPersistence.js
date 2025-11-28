/**
 * Search State Persistence Utility
 * Saves and restores search state to/from sessionStorage
 * Preserves user's research if they accidentally refresh
 */

const SEARCH_CACHE_KEY = 'tafsir_last_search';
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes in milliseconds

/**
 * Save search state to session storage
 * @param {string} query - The search query
 * @param {string} approach - The search approach (tafsir/explore)
 * @param {Object} response - The search response data
 */
export const saveSearchState = (query, approach, response) => {
  try {
    const searchState = {
      query,
      approach,
      response,
      timestamp: Date.now()
    };

    // Use sessionStorage to persist only for the session
    sessionStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(searchState));
  } catch (error) {
    console.error('Failed to save search state:', error);
    // Fail silently - this is a nice-to-have feature
  }
};

/**
 * Load search state from session storage
 * @returns {Object|null} The saved search state or null if none/expired
 */
export const loadSearchState = () => {
  try {
    const cached = sessionStorage.getItem(SEARCH_CACHE_KEY);
    if (!cached) return null;

    const state = JSON.parse(cached);

    // Check if cache has expired
    const age = Date.now() - state.timestamp;
    if (age > CACHE_DURATION) {
      clearSearchState();
      return null;
    }

    return state;
  } catch (error) {
    console.error('Failed to load search state:', error);
    // Clear potentially corrupted cache
    clearSearchState();
    return null;
  }
};

/**
 * Clear the saved search state
 */
export const clearSearchState = () => {
  try {
    sessionStorage.removeItem(SEARCH_CACHE_KEY);
  } catch (error) {
    console.error('Failed to clear search state:', error);
  }
};

/**
 * Get the age of the cached search in human-readable format
 * @returns {string|null} Age string like "5 minutes ago" or null
 */
export const getCacheAge = () => {
  try {
    const cached = sessionStorage.getItem(SEARCH_CACHE_KEY);
    if (!cached) return null;

    const state = JSON.parse(cached);
    const ageMs = Date.now() - state.timestamp;

    if (ageMs < 60000) {
      return 'Just now';
    } else if (ageMs < 3600000) {
      const minutes = Math.floor(ageMs / 60000);
      return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
    } else {
      const hours = Math.floor(ageMs / 3600000);
      return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    }
  } catch {
    return null;
  }
};

/**
 * Check if there's a valid cached search
 * @returns {boolean} True if valid cache exists
 */
export const hasCachedSearch = () => {
  const state = loadSearchState();
  return state !== null;
};