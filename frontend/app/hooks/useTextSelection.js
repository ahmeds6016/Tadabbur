'use client';
import { useEffect, useCallback, useState } from 'react';

/**
 * useTextSelection - Simple text selection detection hook
 *
 * PRINCIPLES:
 * - Just detects selection, no UI
 * - No positioning logic
 * - No scroll manipulation
 * - Clean and simple
 */

export default function useTextSelection(options = {}) {
  const {
    minLength = 3,
    enabled = true,
    debounceMs = 100
  } = options;

  const [selectedText, setSelectedText] = useState(null);
  const [selectionRect, setSelectionRect] = useState(null);

  const handleSelectionChange = useCallback(() => {
    if (!enabled) return;

    const selection = window.getSelection();
    const text = selection?.toString().trim();

    // Check if we have a valid selection
    if (text && text.length >= minLength) {
      // Get selection bounds (optional, for positioning if needed)
      try {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        if (rect.width > 0 && rect.height > 0) {
          setSelectedText(text);
          setSelectionRect({
            top: rect.top,
            left: rect.left,
            bottom: rect.bottom,
            right: rect.right,
            width: rect.width,
            height: rect.height
          });
        }
      } catch (e) {
        // Ignore invalid selections
      }
    } else {
      // Clear selection
      setSelectedText(null);
      setSelectionRect(null);
    }
  }, [enabled, minLength]);

  // Debounced selection handler
  useEffect(() => {
    if (!enabled) return;

    let timeoutId;
    const debouncedHandler = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(handleSelectionChange, debounceMs);
    };

    // Listen for selection changes
    document.addEventListener('selectionchange', debouncedHandler);
    // Also listen for mouseup for better responsiveness
    document.addEventListener('mouseup', debouncedHandler);
    // Mobile support
    document.addEventListener('touchend', debouncedHandler);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('selectionchange', debouncedHandler);
      document.removeEventListener('mouseup', debouncedHandler);
      document.removeEventListener('touchend', debouncedHandler);
    };
  }, [enabled, handleSelectionChange, debounceMs]);

  // Clear selection programmatically
  const clearSelection = useCallback(() => {
    window.getSelection()?.removeAllRanges();
    setSelectedText(null);
    setSelectionRect(null);
  }, []);

  return {
    selectedText,
    selectionRect,
    clearSelection,
    hasSelection: !!selectedText
  };
}