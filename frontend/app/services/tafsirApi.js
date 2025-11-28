/**
 * TafsirAPI Service
 * Centralized API client for all backend interactions
 * Handles caching, error handling, and request management
 */

// Custom error classes for better error handling
export class APIError extends Error {
  constructor(message, statusCode, type) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.type = type;
  }
}

export class RateLimitError extends APIError {
  constructor(message, retryAfter) {
    super(message, 429, 'rate_limit');
    this.retryAfter = retryAfter;
  }
}

export class NetworkError extends APIError {
  constructor(message) {
    super(message, 0, 'network');
  }
}

export class ValidationError extends APIError {
  constructor(message, errors) {
    super(message, 422, 'validation');
    this.errors = errors;
  }
}

class TafsirAPI {
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
    this.cache = new Map();
    this.pendingRequests = new Map();
    this.abortControllers = new Map();
  }

  /**
   * Get headers for API requests
   * @param {string} token - Firebase auth token
   * @returns {Object} Headers object
   */
  getHeaders(token) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Make a fetch request with timeout and retry logic
   * @param {string} url - The URL to fetch
   * @param {Object} options - Fetch options
   * @param {number} timeout - Request timeout in ms
   * @returns {Promise<Response>} The response
   */
  async fetchWithTimeout(url, options, timeout = 30000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(id);
      return response;
    } catch (error) {
      clearTimeout(id);
      if (error.name === 'AbortError') {
        throw new NetworkError('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Search for tafsir
   * @param {string} query - Search query
   * @param {string} approach - Search approach (tafsir/explore)
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} Search results
   */
  async search(query, approach, userToken) {
    const cacheKey = `${approach}:${query}`;

    // Check if we have a pending request for this exact query
    if (this.pendingRequests.has(cacheKey)) {
      return this.pendingRequests.get(cacheKey);
    }

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < 5 * 60 * 1000) { // 5 minutes
        return Promise.resolve(cached.data);
      }
    }

    // Cancel any previous search
    this.cancelSearch();

    // Create new abort controller for this search
    const abortController = new AbortController();
    this.abortControllers.set('search', abortController);

    // Create the request promise
    const requestPromise = this._performSearch(query, approach, userToken, abortController.signal)
      .then(data => {
        // Cache the result
        this.cache.set(cacheKey, {
          data,
          timestamp: Date.now()
        });

        // Clear from pending
        this.pendingRequests.delete(cacheKey);

        return data;
      })
      .catch(error => {
        // Clear from pending
        this.pendingRequests.delete(cacheKey);
        throw error;
      });

    // Store as pending
    this.pendingRequests.set(cacheKey, requestPromise);

    return requestPromise;
  }

  async _performSearch(query, approach, userToken, signal) {
    try {
      const response = await fetch(`${this.baseURL}/tafsir`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify({
          query,
          approach,
          include_arabic: true,
          include_cross_references: true
        }),
        signal
      });

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        throw new RateLimitError(
          'You have reached your query limit. Please wait a moment before trying again.',
          retryAfter
        );
      }

      // Handle other errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(
          errorData.error || `Search failed: ${response.statusText}`,
          response.status,
          'api_error'
        );
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new NetworkError('Search was cancelled');
      }
      if (error instanceof APIError) {
        throw error;
      }
      throw new NetworkError(error.message);
    }
  }

  /**
   * Cancel the current search
   */
  cancelSearch() {
    const controller = this.abortControllers.get('search');
    if (controller) {
      controller.abort();
      this.abortControllers.delete('search');
    }
  }

  /**
   * Get user profile
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} User profile
   */
  async getUserProfile(userToken) {
    try {
      const response = await this.fetchWithTimeout(`${this.baseURL}/get_profile`, {
        method: 'GET',
        headers: this.getHeaders(userToken)
      });

      if (!response.ok) {
        throw new APIError('Failed to fetch profile', response.status, 'profile_error');
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new NetworkError('Failed to fetch user profile');
    }
  }

  /**
   * Set user profile
   * @param {Object} profileData - Profile data to save
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} Updated profile
   */
  async setUserProfile(profileData, userToken) {
    try {
      const response = await this.fetchWithTimeout(`${this.baseURL}/set_profile`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(profileData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(
          errorData.error || 'Failed to save profile',
          response.status,
          'profile_error'
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new NetworkError('Failed to save user profile');
    }
  }

  /**
   * Get search suggestions
   * @param {string} persona - User persona for suggestions
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Array>} Suggestions
   */
  async getSuggestions(persona = 'practicing_muslim', userToken) {
    const cacheKey = `suggestions:${persona}`;

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < 10 * 60 * 1000) { // 10 minutes
        return cached.data;
      }
    }

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/suggestions?persona=${persona}`,
        {
          method: 'GET',
          headers: this.getHeaders(userToken)
        }
      );

      if (!response.ok) {
        throw new APIError('Failed to fetch suggestions', response.status, 'suggestions_error');
      }

      const data = await response.json();

      // Cache the result
      this.cache.set(cacheKey, {
        data,
        timestamp: Date.now()
      });

      return data;
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      // Return default suggestions on error
      return this.getDefaultSuggestions(persona);
    }
  }

  /**
   * Get default suggestions when API fails
   * @param {string} persona - User persona
   * @returns {Array} Default suggestions
   */
  getDefaultSuggestions(persona) {
    const defaults = {
      new_revert: [
        { text: "What are the Five Pillars of Islam?", approach: "explore" },
        { text: "Explain Surah Al-Fatihah", approach: "tafsir" },
        { text: "What does the Quran say about mercy?", approach: "explore" }
      ],
      practicing_muslim: [
        { text: "Explain verse 2:255 (Ayatul Kursi)", approach: "tafsir" },
        { text: "What does the Quran say about patience?", approach: "explore" },
        { text: "Explain the story of Prophet Yusuf", approach: "explore" }
      ],
      student: [
        { text: "Analyze the linguistic miracles in Surah Yusuf", approach: "tafsir" },
        { text: "Compare different interpretations of 3:7", approach: "tafsir" },
        { text: "Themes of social justice in the Quran", approach: "explore" }
      ],
      scholar: [
        { text: "Examine the concept of Naskh (abrogation)", approach: "explore" },
        { text: "Analyze verse 4:34 with classical and modern interpretations", approach: "tafsir" },
        { text: "The methodology of Tafsir bil-Ma'thur vs Tafsir bil-Ra'y", approach: "explore" }
      ]
    };

    return defaults[persona] || defaults.practicing_muslim;
  }

  /**
   * Save search to history
   * @param {Object} searchData - Search data to save
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} Save result
   */
  async saveToHistory(searchData, userToken) {
    try {
      const response = await fetch(`${this.baseURL}/query-history`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(searchData)
      });

      return { success: response.ok };
    } catch (error) {
      console.error('Failed to save to history:', error);
      return { success: false, error };
    }
  }

  /**
   * Get query history
   * @param {string} userToken - Firebase auth token
   * @param {number} limit - Number of items to fetch
   * @returns {Promise<Array>} History items
   */
  async getHistory(userToken, limit = 20) {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/query-history?limit=${limit}`,
        {
          method: 'GET',
          headers: this.getHeaders(userToken)
        }
      );

      if (!response.ok) {
        throw new APIError('Failed to fetch history', response.status, 'history_error');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch history:', error);
      return [];
    }
  }

  /**
   * Save a search
   * @param {Object} searchData - Search to save
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} Save result
   */
  async saveSearch(searchData, userToken) {
    try {
      const response = await this.fetchWithTimeout(`${this.baseURL}/saved-searches`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(searchData)
      });

      if (!response.ok) {
        throw new APIError('Failed to save search', response.status, 'save_error');
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new NetworkError('Failed to save search');
    }
  }

  /**
   * Create a share link
   * @param {Object} shareData - Data to share
   * @param {string} userToken - Firebase auth token
   * @returns {Promise<Object>} Share result with ID
   */
  async createShareLink(shareData, userToken) {
    try {
      const response = await this.fetchWithTimeout(`${this.baseURL}/share`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(shareData)
      });

      if (!response.ok) {
        throw new APIError('Failed to create share link', response.status, 'share_error');
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new NetworkError('Failed to create share link');
    }
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Clear cache for specific key pattern
   * @param {string} pattern - Pattern to match
   */
  clearCacheByPattern(pattern) {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }
}

// Export singleton instance
export const tafsirAPI = new TafsirAPI();