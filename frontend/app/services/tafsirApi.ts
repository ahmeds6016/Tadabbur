/**
 * TafsirAPI Service - TypeScript Version
 * Centralized API client with full type safety
 */

import type {
  User,
  UserProfile,
  SearchQuery,
  TafsirResponse,
  Suggestion,
  HistoryItem,
  Annotation,
  ShareData,
  APIResponse,
  RateLimitInfo
} from '@/types';

// Error classes with TypeScript
export class APIError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly type: string,
    public readonly details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class RateLimitError extends APIError {
  constructor(message: string, public readonly retryAfter?: number) {
    super(message, 429, 'rate_limit', { retryAfter });
  }
}

export class NetworkError extends APIError {
  constructor(message: string) {
    super(message, 0, 'network');
  }
}

export class ValidationError extends APIError {
  constructor(message: string, public readonly errors: Record<string, string[]>) {
    super(message, 422, 'validation', errors);
  }
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class TafsirAPI {
  private readonly baseURL: string;
  private readonly cache = new Map<string, CacheEntry<any>>();
  private readonly pendingRequests = new Map<string, Promise<any>>();
  private readonly abortControllers = new Map<string, AbortController>();

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
  }

  /**
   * Get headers for API requests
   */
  private getHeaders(token?: string): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Make a fetch request with timeout and type safety
   */
  private async fetchWithTimeout<T>(
    url: string,
    options: RequestInit,
    timeout: number = 30000
  ): Promise<T> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });

      clearTimeout(id);

      if (!response.ok) {
        await this.handleErrorResponse(response);
      }

      return await response.json() as T;
    } catch (error) {
      clearTimeout(id);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new NetworkError('Request timeout');
      }

      if (error instanceof APIError) {
        throw error;
      }

      throw new NetworkError(error instanceof Error ? error.message : 'Network error');
    }
  }

  /**
   * Handle error responses with proper typing
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    let errorData: any;

    try {
      errorData = await response.json();
    } catch {
      errorData = { error: response.statusText };
    }

    switch (response.status) {
      case 429:
        throw new RateLimitError(
          errorData.error || 'Rate limit exceeded',
          response.headers.get('Retry-After') ? parseInt(response.headers.get('Retry-After')!) : undefined
        );
      case 422:
        throw new ValidationError(
          errorData.error || 'Validation failed',
          errorData.errors || {}
        );
      default:
        throw new APIError(
          errorData.error || `Request failed: ${response.statusText}`,
          response.status,
          'api_error',
          errorData
        );
    }
  }

  /**
   * Search for tafsir with full type safety
   */
  async search(
    query: string,
    approach: 'tafsir' | 'explore',
    userToken: string
  ): Promise<TafsirResponse> {
    const cacheKey = `${approach}:${query}`;

    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
      return cached.data;
    }

    // Check pending requests
    if (this.pendingRequests.has(cacheKey)) {
      return this.pendingRequests.get(cacheKey)!;
    }

    // Cancel previous search
    this.cancelSearch();

    // Create new request
    const abortController = new AbortController();
    this.abortControllers.set('search', abortController);

    const requestPromise = this.performSearch(query, approach, userToken, abortController.signal)
      .then(data => {
        this.cache.set(cacheKey, { data, timestamp: Date.now() });
        this.pendingRequests.delete(cacheKey);
        return data;
      })
      .catch(error => {
        this.pendingRequests.delete(cacheKey);
        throw error;
      });

    this.pendingRequests.set(cacheKey, requestPromise);
    return requestPromise;
  }

  private async performSearch(
    query: string,
    approach: 'tafsir' | 'explore',
    userToken: string,
    signal: AbortSignal
  ): Promise<TafsirResponse> {
    const searchBody: SearchQuery & { include_arabic: boolean; include_cross_references: boolean } = {
      query,
      approach,
      include_arabic: true,
      include_cross_references: true
    };

    return this.fetchWithTimeout<TafsirResponse>(
      `${this.baseURL}/tafsir`,
      {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(searchBody),
        signal
      }
    );
  }

  /**
   * Cancel the current search
   */
  cancelSearch(): void {
    const controller = this.abortControllers.get('search');
    if (controller) {
      controller.abort();
      this.abortControllers.delete('search');
    }
  }

  /**
   * Get user profile with type safety
   */
  async getUserProfile(userToken: string): Promise<UserProfile> {
    return this.fetchWithTimeout<UserProfile>(
      `${this.baseURL}/get_profile`,
      {
        method: 'GET',
        headers: this.getHeaders(userToken)
      }
    );
  }

  /**
   * Set user profile
   */
  async setUserProfile(
    profileData: Partial<UserProfile>,
    userToken: string
  ): Promise<UserProfile> {
    return this.fetchWithTimeout<UserProfile>(
      `${this.baseURL}/set_profile`,
      {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(profileData)
      }
    );
  }

  /**
   * Get search suggestions based on persona
   */
  async getSuggestions(
    persona: UserProfile['persona'] = 'practicing_muslim',
    userToken?: string
  ): Promise<Suggestion[]> {
    const cacheKey = `suggestions:${persona}`;

    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < 10 * 60 * 1000) {
      return cached.data;
    }

    try {
      const suggestions = await this.fetchWithTimeout<Suggestion[]>(
        `${this.baseURL}/suggestions?persona=${persona}`,
        {
          method: 'GET',
          headers: this.getHeaders(userToken)
        }
      );

      this.cache.set(cacheKey, { data: suggestions, timestamp: Date.now() });
      return suggestions;
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      return this.getDefaultSuggestions(persona);
    }
  }

  /**
   * Get default suggestions when API fails
   */
  private getDefaultSuggestions(persona: UserProfile['persona']): Suggestion[] {
    const defaults: Record<UserProfile['persona'], Suggestion[]> = {
      new_revert: [
        { text: "What are the Five Pillars of Islam?", approach: "explore" },
        { text: "Explain Surah Al-Fatihah", approach: "tafsir" },
        { text: "What does the Quran say about mercy?", approach: "explore" }
      ],
      revert: [
        { text: "Explain the concept of Tawheed", approach: "explore" },
        { text: "What does 2:255 (Ayatul Kursi) mean?", approach: "tafsir" },
        { text: "Stories of the Prophets in the Quran", approach: "explore" }
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

    return defaults[persona];
  }

  /**
   * Save search to history
   */
  async saveToHistory(
    searchData: Pick<HistoryItem, 'query' | 'approach' | 'success'>,
    userToken: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(`${this.baseURL}/query-history`, {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(searchData)
      });

      return { success: response.ok };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to save to history:', error);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Get query history
   */
  async getHistory(userToken: string, limit: number = 20): Promise<HistoryItem[]> {
    try {
      return await this.fetchWithTimeout<HistoryItem[]>(
        `${this.baseURL}/query-history?limit=${limit}`,
        {
          method: 'GET',
          headers: this.getHeaders(userToken)
        }
      );
    } catch (error) {
      console.error('Failed to fetch history:', error);
      return [];
    }
  }

  /**
   * Annotation management
   */
  async createAnnotation(annotation: Omit<Annotation, 'id' | 'created_at' | 'updated_at'>, userToken: string): Promise<Annotation> {
    return this.fetchWithTimeout<Annotation>(
      `${this.baseURL}/annotations`,
      {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(annotation)
      }
    );
  }

  async updateAnnotation(id: string, updates: Partial<Annotation>, userToken: string): Promise<Annotation> {
    return this.fetchWithTimeout<Annotation>(
      `${this.baseURL}/annotations/${id}`,
      {
        method: 'PUT',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(updates)
      }
    );
  }

  async deleteAnnotation(id: string, userToken: string): Promise<{ success: boolean }> {
    return this.fetchWithTimeout<{ success: boolean }>(
      `${this.baseURL}/annotations/${id}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(userToken)
      }
    );
  }

  async getAnnotations(filters: { verse_reference?: string; type?: Annotation['type'] }, userToken: string): Promise<Annotation[]> {
    const params = new URLSearchParams(filters as Record<string, string>);
    return this.fetchWithTimeout<Annotation[]>(
      `${this.baseURL}/annotations?${params}`,
      {
        method: 'GET',
        headers: this.getHeaders(userToken)
      }
    );
  }

  /**
   * Create a share link
   */
  async createShareLink(shareData: Omit<ShareData, 'created_at'>, userToken: string): Promise<{ share_id: string; url: string }> {
    return this.fetchWithTimeout<{ share_id: string; url: string }>(
      `${this.baseURL}/share`,
      {
        method: 'POST',
        headers: this.getHeaders(userToken),
        body: JSON.stringify(shareData)
      }
    );
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Clear cache by pattern
   */
  clearCacheByPattern(pattern: string): void {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }
}

// Export singleton instance
export const tafsirAPI = new TafsirAPI();