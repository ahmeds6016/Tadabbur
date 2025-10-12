/* ============================================================================
   TAFSIR SIMPLIFIED - API CLIENT
   Enhanced to support all backend features
   ============================================================================ */

import axios from "https://cdn.jsdelivr.net/npm/axios@1.7.2/dist/axios.min.js";

// API Configuration
const API_BASE = "https://tafsir-backend-612616741510.us-central1.run.app";

// ============================================================================
// TAFSIR SEARCH
// ============================================================================

/**
 * Get tafsir for a query (supports metadata, direct, and semantic queries)
 * @param {string} idToken - Firebase ID token
 * @param {string} query - User query
 * @param {object} userProfile - Optional user profile (persona, etc.)
 * @returns {Promise<object>} Tafsir results
 */
export const getTafsir = async (idToken, query, userProfile = null) => {
  try {
    const payload = { query };
    
    // Add user profile if provided
    if (userProfile) {
      payload.user_profile = userProfile;
    }
    
    const res = await axios.post(
      `${API_BASE}/tafsir`,
      payload,
      { 
        headers: { 
          Authorization: `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        timeout: 30000 // 30 second timeout
      }
    );
    
    return res.data;
  } catch (err) {
    console.error("Error getting tafsir:", err.response?.data || err.message);
    
    // Provide user-friendly error messages
    if (err.response?.status === 429) {
      throw new Error("Rate limit exceeded. Please wait a moment and try again.");
    } else if (err.response?.status === 401) {
      throw new Error("Authentication failed. Please sign in again.");
    } else if (err.code === 'ECONNABORTED') {
      throw new Error("Request timeout. The server took too long to respond.");
    } else if (err.response?.data?.error) {
      throw new Error(err.response.data.error);
    } else {
      throw new Error("Unable to connect to server. Please check your connection.");
    }
  }
};

// ============================================================================
// METADATA QUERIES (Direct Access)
// ============================================================================

/**
 * Get metadata for a specific verse
 * @param {number} surah - Surah number
 * @param {number} verse - Verse number
 * @param {string} type - Optional metadata type (hadith, scholar_citations, etc.)
 * @param {string} source - Optional source filter (ibn-kathir, al-qurtubi)
 * @returns {Promise<object>} Metadata results
 */
export const getVerseMetadata = async (surah, verse, type = null, source = null) => {
  try {
    let url = `${API_BASE}/metadata/${surah}/${verse}`;
    const params = new URLSearchParams();
    
    if (type) params.append('type', type);
    if (source) params.append('source', source);
    
    const queryString = params.toString();
    if (queryString) url += `?${queryString}`;
    
    const res = await axios.get(url, { timeout: 10000 });
    return res.data;
  } catch (err) {
    console.error("Error getting metadata:", err.response?.data || err.message);
    
    if (err.response?.status === 404) {
      throw new Error(`No metadata found for verse ${surah}:${verse}`);
    } else {
      throw new Error(err.response?.data?.error || "Failed to retrieve metadata");
    }
  }
};

// ============================================================================
// PERSONA MANAGEMENT
// ============================================================================

/**
 * Get list of available personas
 * @returns {Promise<object>} Personas list
 */
export const getPersonas = async () => {
  try {
    const res = await axios.get(`${API_BASE}/personas`, { timeout: 5000 });
    return res.data;
  } catch (err) {
    console.error("Error getting personas:", err.response?.data || err.message);
    
    // Return fallback personas if API fails
    return {
      personas: ['new_revert', 'practicing_muslim', 'scholar'],
      details: {
        new_revert: {
          name: 'New Revert',
          description: 'Simple explanations for beginners'
        },
        practicing_muslim: {
          name: 'Practicing Muslim',
          description: 'Balanced depth for regular learners'
        },
        scholar: {
          name: 'Scholar',
          description: 'Advanced academic content'
        }
      }
    };
  }
};

// ============================================================================
// HEALTH CHECK
// ============================================================================

/**
 * Check backend health and configuration
 * @returns {Promise<object>} Health status
 */
export const checkHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE}/health`, { timeout: 5000 });
    return res.data;
  } catch (err) {
    console.error("Health check failed:", err.message);
    throw new Error("Unable to connect to backend");
  }
};

// ============================================================================
// LEGACY COMPATIBILITY (for old code)
// ============================================================================

/**
 * Legacy function - set user profile
 * @deprecated Use getTafsir with userProfile parameter instead
 */
export const setUserProfile = async (idToken, level) => {
  console.warn('setUserProfile is deprecated. Use getTafsir with userProfile parameter.');
  
  // For backwards compatibility, just return success
  return { success: true, level };
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format API error for display
 * @param {Error} error - Error object
 * @returns {string} User-friendly error message
 */
export const formatError = (error) => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  } else if (error.message) {
    return error.message;
  } else {
    return 'An unexpected error occurred';
  }
};

/**
 * Validate verse reference
 * @param {number} surah - Surah number
 * @param {number} verse - Verse number
 * @returns {boolean} Is valid
 */
export const isValidVerseReference = (surah, verse) => {
  return (
    Number.isInteger(surah) && 
    Number.isInteger(verse) &&
    surah >= 1 && 
    surah <= 114 &&
    verse >= 1
  );
};

/**
 * Parse verse reference from string
 * @param {string} text - Text like "2:255" or "verse 3:7"
 * @returns {object|null} {surah, verse} or null
 */
export const parseVerseReference = (text) => {
  const patterns = [
    /(\d+):(\d+)/,  // 2:255
    /surah\s+(\d+)\s+verse\s+(\d+)/i,  // surah 2 verse 255
    /verse\s+(\d+):(\d+)/i,  // verse 2:255
  ];
  
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const surah = parseInt(match[1]);
      const verse = parseInt(match[2]);
      if (isValidVerseReference(surah, verse)) {
        return { surah, verse };
      }
    }
  }
  
  return null;
};

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  getTafsir,
  getVerseMetadata,
  getPersonas,
  checkHealth,
  setUserProfile,
  formatError,
  isValidVerseReference,
  parseVerseReference
};
