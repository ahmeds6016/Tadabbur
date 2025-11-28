'use client';

import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { tafsirAPI } from '../services/tafsirApi';

/**
 * AppContext - Global application state management
 * Eliminates prop drilling and centralizes state logic
 */

// Initial state
const initialState = {
  // User state
  user: null,
  userProfile: null,
  isAuthenticated: false,

  // Search state
  searchQuery: '',
  searchApproach: 'tafsir',
  searchResponse: null,
  isSearchLoading: false,
  searchError: null,

  // UI state
  sidebarOpen: false,
  navCollapsed: false,
  suggestionsExpanded: false,
  activeModal: null,
  theme: 'light',

  // Annotations state
  annotations: [],
  currentAnnotation: null,
  annotationDialogOpen: false,
  selectedText: '',
  selectedVerse: null,

  // History & Suggestions
  searchHistory: [],
  suggestions: [],
  savedSearches: [],

  // Notifications
  notifications: [],
  rateLimitWarning: null,
};

// Action types
const ActionTypes = {
  // User actions
  SET_USER: 'SET_USER',
  SET_USER_PROFILE: 'SET_USER_PROFILE',
  LOGOUT: 'LOGOUT',

  // Search actions
  SET_SEARCH_QUERY: 'SET_SEARCH_QUERY',
  SET_SEARCH_APPROACH: 'SET_SEARCH_APPROACH',
  SET_SEARCH_LOADING: 'SET_SEARCH_LOADING',
  SET_SEARCH_RESPONSE: 'SET_SEARCH_RESPONSE',
  SET_SEARCH_ERROR: 'SET_SEARCH_ERROR',
  CLEAR_SEARCH: 'CLEAR_SEARCH',

  // UI actions
  TOGGLE_SIDEBAR: 'TOGGLE_SIDEBAR',
  TOGGLE_NAV: 'TOGGLE_NAV',
  TOGGLE_SUGGESTIONS: 'TOGGLE_SUGGESTIONS',
  SET_ACTIVE_MODAL: 'SET_ACTIVE_MODAL',
  SET_THEME: 'SET_THEME',

  // Annotation actions
  SET_ANNOTATIONS: 'SET_ANNOTATIONS',
  ADD_ANNOTATION: 'ADD_ANNOTATION',
  UPDATE_ANNOTATION: 'UPDATE_ANNOTATION',
  DELETE_ANNOTATION: 'DELETE_ANNOTATION',
  SET_CURRENT_ANNOTATION: 'SET_CURRENT_ANNOTATION',
  TOGGLE_ANNOTATION_DIALOG: 'TOGGLE_ANNOTATION_DIALOG',
  SET_SELECTED_TEXT: 'SET_SELECTED_TEXT',
  SET_SELECTED_VERSE: 'SET_SELECTED_VERSE',

  // History & Suggestions
  SET_SEARCH_HISTORY: 'SET_SEARCH_HISTORY',
  ADD_TO_HISTORY: 'ADD_TO_HISTORY',
  SET_SUGGESTIONS: 'SET_SUGGESTIONS',
  SET_SAVED_SEARCHES: 'SET_SAVED_SEARCHES',

  // Notifications
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  SET_RATE_LIMIT_WARNING: 'SET_RATE_LIMIT_WARNING',

  // Bulk update
  RESET_STATE: 'RESET_STATE',
  UPDATE_STATE: 'UPDATE_STATE',
};

// Reducer function
function appReducer(state, action) {
  switch (action.type) {
    // User reducers
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload,
        isAuthenticated: !!action.payload,
      };

    case ActionTypes.SET_USER_PROFILE:
      return {
        ...state,
        userProfile: action.payload,
      };

    case ActionTypes.LOGOUT:
      return {
        ...initialState,
        suggestions: state.suggestions, // Keep suggestions
      };

    // Search reducers
    case ActionTypes.SET_SEARCH_QUERY:
      return {
        ...state,
        searchQuery: action.payload,
      };

    case ActionTypes.SET_SEARCH_APPROACH:
      return {
        ...state,
        searchApproach: action.payload,
      };

    case ActionTypes.SET_SEARCH_LOADING:
      return {
        ...state,
        isSearchLoading: action.payload,
      };

    case ActionTypes.SET_SEARCH_RESPONSE:
      return {
        ...state,
        searchResponse: action.payload,
        searchError: null,
        isSearchLoading: false,
      };

    case ActionTypes.SET_SEARCH_ERROR:
      return {
        ...state,
        searchError: action.payload,
        isSearchLoading: false,
      };

    case ActionTypes.CLEAR_SEARCH:
      return {
        ...state,
        searchQuery: '',
        searchResponse: null,
        searchError: null,
      };

    // UI reducers
    case ActionTypes.TOGGLE_SIDEBAR:
      return {
        ...state,
        sidebarOpen: !state.sidebarOpen,
      };

    case ActionTypes.TOGGLE_NAV:
      return {
        ...state,
        navCollapsed: !state.navCollapsed,
      };

    case ActionTypes.TOGGLE_SUGGESTIONS:
      return {
        ...state,
        suggestionsExpanded: !state.suggestionsExpanded,
      };

    case ActionTypes.SET_ACTIVE_MODAL:
      return {
        ...state,
        activeModal: action.payload,
      };

    case ActionTypes.SET_THEME:
      return {
        ...state,
        theme: action.payload,
      };

    // Annotation reducers
    case ActionTypes.SET_ANNOTATIONS:
      return {
        ...state,
        annotations: action.payload,
      };

    case ActionTypes.ADD_ANNOTATION:
      return {
        ...state,
        annotations: [...state.annotations, action.payload],
      };

    case ActionTypes.UPDATE_ANNOTATION:
      return {
        ...state,
        annotations: state.annotations.map((ann) =>
          ann.id === action.payload.id ? action.payload : ann
        ),
      };

    case ActionTypes.DELETE_ANNOTATION:
      return {
        ...state,
        annotations: state.annotations.filter((ann) => ann.id !== action.payload),
      };

    case ActionTypes.SET_CURRENT_ANNOTATION:
      return {
        ...state,
        currentAnnotation: action.payload,
      };

    case ActionTypes.TOGGLE_ANNOTATION_DIALOG:
      return {
        ...state,
        annotationDialogOpen: !state.annotationDialogOpen,
      };

    case ActionTypes.SET_SELECTED_TEXT:
      return {
        ...state,
        selectedText: action.payload,
      };

    case ActionTypes.SET_SELECTED_VERSE:
      return {
        ...state,
        selectedVerse: action.payload,
      };

    // History & Suggestions
    case ActionTypes.SET_SEARCH_HISTORY:
      return {
        ...state,
        searchHistory: action.payload,
      };

    case ActionTypes.ADD_TO_HISTORY:
      return {
        ...state,
        searchHistory: [action.payload, ...state.searchHistory].slice(0, 20),
      };

    case ActionTypes.SET_SUGGESTIONS:
      return {
        ...state,
        suggestions: action.payload,
      };

    case ActionTypes.SET_SAVED_SEARCHES:
      return {
        ...state,
        savedSearches: action.payload,
      };

    // Notifications
    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, action.payload],
      };

    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter((n) => n.id !== action.payload),
      };

    case ActionTypes.SET_RATE_LIMIT_WARNING:
      return {
        ...state,
        rateLimitWarning: action.payload,
      };

    // Bulk updates
    case ActionTypes.RESET_STATE:
      return initialState;

    case ActionTypes.UPDATE_STATE:
      return {
        ...state,
        ...action.payload,
      };

    default:
      console.warn('Unknown action type:', action.type);
      return state;
  }
}

// Create context
const AppContext = createContext();

// Provider component
export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Helper functions
  const actions = {
    // User actions
    setUser: (user) => dispatch({ type: ActionTypes.SET_USER, payload: user }),
    setUserProfile: (profile) => dispatch({ type: ActionTypes.SET_USER_PROFILE, payload: profile }),
    logout: () => dispatch({ type: ActionTypes.LOGOUT }),

    // Search actions
    setSearchQuery: (query) => dispatch({ type: ActionTypes.SET_SEARCH_QUERY, payload: query }),
    setSearchApproach: (approach) => dispatch({ type: ActionTypes.SET_SEARCH_APPROACH, payload: approach }),
    setSearchLoading: (loading) => dispatch({ type: ActionTypes.SET_SEARCH_LOADING, payload: loading }),
    setSearchResponse: (response) => dispatch({ type: ActionTypes.SET_SEARCH_RESPONSE, payload: response }),
    setSearchError: (error) => dispatch({ type: ActionTypes.SET_SEARCH_ERROR, payload: error }),
    clearSearch: () => dispatch({ type: ActionTypes.CLEAR_SEARCH }),

    // UI actions
    toggleSidebar: () => dispatch({ type: ActionTypes.TOGGLE_SIDEBAR }),
    toggleNav: () => dispatch({ type: ActionTypes.TOGGLE_NAV }),
    toggleSuggestions: () => dispatch({ type: ActionTypes.TOGGLE_SUGGESTIONS }),
    setActiveModal: (modal) => dispatch({ type: ActionTypes.SET_ACTIVE_MODAL, payload: modal }),
    setTheme: (theme) => dispatch({ type: ActionTypes.SET_THEME, payload: theme }),

    // Annotation actions
    setAnnotations: (annotations) => dispatch({ type: ActionTypes.SET_ANNOTATIONS, payload: annotations }),
    addAnnotation: (annotation) => dispatch({ type: ActionTypes.ADD_ANNOTATION, payload: annotation }),
    updateAnnotation: (annotation) => dispatch({ type: ActionTypes.UPDATE_ANNOTATION, payload: annotation }),
    deleteAnnotation: (id) => dispatch({ type: ActionTypes.DELETE_ANNOTATION, payload: id }),
    setCurrentAnnotation: (annotation) => dispatch({ type: ActionTypes.SET_CURRENT_ANNOTATION, payload: annotation }),
    toggleAnnotationDialog: () => dispatch({ type: ActionTypes.TOGGLE_ANNOTATION_DIALOG }),
    setSelectedText: (text) => dispatch({ type: ActionTypes.SET_SELECTED_TEXT, payload: text }),
    setSelectedVerse: (verse) => dispatch({ type: ActionTypes.SET_SELECTED_VERSE, payload: verse }),

    // History & Suggestions
    setSearchHistory: (history) => dispatch({ type: ActionTypes.SET_SEARCH_HISTORY, payload: history }),
    addToHistory: (item) => dispatch({ type: ActionTypes.ADD_TO_HISTORY, payload: item }),
    setSuggestions: (suggestions) => dispatch({ type: ActionTypes.SET_SUGGESTIONS, payload: suggestions }),
    setSavedSearches: (searches) => dispatch({ type: ActionTypes.SET_SAVED_SEARCHES, payload: searches }),

    // Notifications
    addNotification: (notification) => dispatch({ type: ActionTypes.ADD_NOTIFICATION, payload: notification }),
    removeNotification: (id) => dispatch({ type: ActionTypes.REMOVE_NOTIFICATION, payload: id }),
    setRateLimitWarning: (warning) => dispatch({ type: ActionTypes.SET_RATE_LIMIT_WARNING, payload: warning }),

    // Bulk updates
    resetState: () => dispatch({ type: ActionTypes.RESET_STATE }),
    updateState: (updates) => dispatch({ type: ActionTypes.UPDATE_STATE, payload: updates }),
  };

  // Complex action creators
  const performSearch = useCallback(async (query, approach) => {
    if (!state.user) {
      actions.setSearchError('Please sign in to search');
      return;
    }

    actions.setSearchLoading(true);
    actions.setSearchError(null);

    try {
      const token = await state.user.getIdToken();
      const response = await tafsirAPI.search(query, approach, token);

      actions.setSearchResponse(response);
      actions.addToHistory({
        query,
        approach,
        timestamp: Date.now(),
      });

      // Save to backend history
      tafsirAPI.saveToHistory({ query, approach, success: true }, token);
    } catch (error) {
      if (error.type === 'rate_limit') {
        actions.setRateLimitWarning(error.message);
      } else {
        actions.setSearchError(error.message);
      }
    } finally {
      actions.setSearchLoading(false);
    }
  }, [state.user]);

  // Load suggestions on mount
  useEffect(() => {
    if (state.user && state.userProfile) {
      const loadSuggestions = async () => {
        try {
          const token = await state.user.getIdToken();
          const suggestions = await tafsirAPI.getSuggestions(
            state.userProfile.persona || 'practicing_muslim',
            token
          );
          actions.setSuggestions(suggestions);
        } catch (error) {
          console.error('Failed to load suggestions:', error);
        }
      };
      loadSuggestions();
    }
  }, [state.user, state.userProfile]);

  // Persist UI preferences
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('ui_preferences', JSON.stringify({
        navCollapsed: state.navCollapsed,
        suggestionsExpanded: state.suggestionsExpanded,
        theme: state.theme,
      }));
    }
  }, [state.navCollapsed, state.suggestionsExpanded, state.theme]);

  // Load UI preferences on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('ui_preferences');
      if (saved) {
        try {
          const preferences = JSON.parse(saved);
          actions.updateState(preferences);
        } catch (error) {
          console.error('Failed to load UI preferences:', error);
        }
      }
    }
  }, []);

  const value = {
    state,
    dispatch,
    actions,
    performSearch,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

// Custom hook to use the context
export function useApp() {
  const context = useContext(AppContext);

  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }

  return context;
}

// Convenience hooks for specific parts of state
export function useUser() {
  const { state } = useApp();
  return {
    user: state.user,
    userProfile: state.userProfile,
    isAuthenticated: state.isAuthenticated,
  };
}

export function useSearch() {
  const { state, actions, performSearch } = useApp();
  return {
    query: state.searchQuery,
    approach: state.searchApproach,
    response: state.searchResponse,
    isLoading: state.isSearchLoading,
    error: state.searchError,
    setQuery: actions.setSearchQuery,
    setApproach: actions.setSearchApproach,
    performSearch,
    clearSearch: actions.clearSearch,
  };
}

export function useAnnotations() {
  const { state, actions } = useApp();
  return {
    annotations: state.annotations,
    currentAnnotation: state.currentAnnotation,
    dialogOpen: state.annotationDialogOpen,
    selectedText: state.selectedText,
    selectedVerse: state.selectedVerse,
    addAnnotation: actions.addAnnotation,
    updateAnnotation: actions.updateAnnotation,
    deleteAnnotation: actions.deleteAnnotation,
    toggleDialog: actions.toggleAnnotationDialog,
    setSelectedText: actions.setSelectedText,
    setSelectedVerse: actions.setSelectedVerse,
  };
}

export function useUI() {
  const { state, actions } = useApp();
  return {
    sidebarOpen: state.sidebarOpen,
    navCollapsed: state.navCollapsed,
    suggestionsExpanded: state.suggestionsExpanded,
    theme: state.theme,
    toggleSidebar: actions.toggleSidebar,
    toggleNav: actions.toggleNav,
    toggleSuggestions: actions.toggleSuggestions,
    setTheme: actions.setTheme,
  };
}