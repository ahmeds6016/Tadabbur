/**
 * TypeScript Type Definitions for Tadabbur
 */

// User types
export interface User {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  getIdToken: () => Promise<string>;
}

export interface UserProfile {
  persona: 'new_revert' | 'revert' | 'practicing_muslim' | 'student' | 'scholar';
  knowledge_level?: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  learning_goal?: 'understanding' | 'memorization' | 'research' | 'teaching';
  include_arabic?: boolean;
  include_transliteration?: boolean;
  preferred_translation?: string;
  theme?: string;
  created_at?: Date;
  updated_at?: Date;
}

// Verse types
export interface Verse {
  surah_number: number;
  verse_number: number;
  surah_name?: string;
  arabic_text: string;
  translation: string;
  transliteration?: string;
  reference?: string;
}

export interface VerseRange {
  surah: number;
  start_verse: number;
  end_verse: number;
}

// Tafsir types
export interface TafsirExplanation {
  source: string;
  explanation: string;
  confidence?: number;
}

export interface Lesson {
  point: string;
  type?: 'synthesis' | 'contemplation' | 'progression';
  // Synthesis type
  body?: string;
  // Contemplation type
  core_principle?: string;
  contemplation?: string;
  prophetic_anchor?: string;
  // Progression type
  baseline?: string;
  ascent?: string;
  peak?: string;
  // Legacy fields
  example?: string;
  action?: string;
  relevance?: string;
}

export interface CrossReference {
  verse: string;
  relevance: string;
  arabic_text?: string;
  english_text?: string;
}

// Search types
export interface SearchQuery {
  query: string;
  approach: 'tafsir' | 'explore';
}

export interface TafsirResponse {
  verses: Verse[];
  tafsir_explanations: TafsirExplanation[];
  lessons_practical_applications: Lesson[];
  cross_references: CrossReference[];
  summary: string;
  supplementary_verses?: Verse[];
  metadata?: {
    query: string;
    approach: string;
    timestamp: string;
  };
}

// Annotation types
export type AnnotationType =
  | 'insight'
  | 'question'
  | 'reflection'
  | 'application'
  | 'connection'
  | 'reminder';

export interface Annotation {
  id: string;
  user_id: string;
  verse_reference?: string;
  selected_text?: string;
  type: AnnotationType;
  content: string;
  tags?: string[];
  visibility: 'private' | 'public';
  created_at: Date;
  updated_at: Date;
  share_id?: string;
}

// Suggestion types
export interface Suggestion {
  text: string;
  approach: 'tafsir' | 'explore';
  icon?: string;
  category?: string;
}

// History types
export interface HistoryItem {
  id: string;
  query: string;
  approach: 'tafsir' | 'explore';
  timestamp: Date;
  success: boolean;
  result_count?: number;
}

// API types
export interface APIResponse<T> {
  data?: T;
  error?: string;
  success: boolean;
  metadata?: {
    timestamp: string;
    request_id?: string;
  };
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: Date;
  retry_after?: number;
}

// Toast/Notification types
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Theme types
export interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    foreground: string;
    accent: string;
    error: string;
    success: string;
    warning: string;
  };
  fonts: {
    body: string;
    arabic: string;
    heading: string;
  };
}

// Share types
export interface ShareData {
  type: 'search' | 'annotation' | 'verse';
  data: any;
  title?: string;
  description?: string;
  created_by: string;
  created_at: Date;
  expires_at?: Date;
}

// Settings types
export interface Settings {
  notifications: {
    enabled: boolean;
    email: boolean;
    push: boolean;
  };
  privacy: {
    show_profile: boolean;
    allow_messages: boolean;
    share_history: boolean;
  };
  display: {
    font_size: 'small' | 'medium' | 'large';
    arabic_font: string;
    show_transliteration: boolean;
    theme: 'light' | 'dark' | 'auto';
  };
}

// Onboarding types
export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  target?: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Error types
export class TafsirError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'TafsirError';
  }
}

export class NetworkError extends TafsirError {
  constructor(message: string) {
    super(message, 'NETWORK_ERROR', 0);
  }
}

export class ValidationError extends TafsirError {
  constructor(message: string, details?: any) {
    super(message, 'VALIDATION_ERROR', 400, details);
  }
}

export class AuthenticationError extends TafsirError {
  constructor(message: string) {
    super(message, 'AUTH_ERROR', 401);
  }
}

export class RateLimitError extends TafsirError {
  constructor(message: string, retryAfter?: number) {
    super(message, 'RATE_LIMIT', 429, { retryAfter });
  }
}