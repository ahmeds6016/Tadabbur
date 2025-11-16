'use client';
import { useEffect, useCallback, useState, useRef } from 'react';

/**
 * useTextSelection - Improved text selection detection hook
 *
 * PRINCIPLES:
 * - Reliable detection with immediate feedback
 * - Better mobile support
 * - No scroll manipulation
 * - Clean and simple
 */

export default function useTextSelection(options = {}) {
  const {
    minLength = 3,
    enabled = true,
    debounceMs = 300  // Reduced from 500ms for faster response
  } = options;

  const [selectedText, setSelectedText] = useState(null);
  const [selectionRect, setSelectionRect] = useState(null);
  const timeoutRef = useRef(null);
  const lastSelectionRef = useRef('');

  const handleSelectionChange = useCallback(() => {
    if (!enabled) return;

    const selection = window.getSelection();
    const text = selection?.toString().trim();

    // Immediate clear if no selection
    if (!text || text.length < minLength) {
      if (lastSelectionRef.current) {
        setSelectedText(null);
        setSelectionRect(null);
        lastSelectionRef.current = '';
      }
      return;
    }

    // Only update if selection changed
    if (text === lastSelectionRef.current) return;
    lastSelectionRef.current = text;

    // Get selection bounds
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
      console.debug('Selection error:', e);
    }
  }, [enabled, minLength]);

  useEffect(() => {
    if (!enabled) return;

    // Immediate handler for mouseup/touchend
    const immediateHandler = () => {
      clearTimeout(timeoutRef.current);
      handleSelectionChange();
    };

    // Debounced handler for selectionchange
    const debouncedHandler = () => {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(handleSelectionChange, debounceMs);
    };

    // Use immediate detection for user actions
    document.addEventListener('mouseup', immediateHandler);
    document.addEventListener('touchend', immediateHandler, { passive: true });

    // Use debounced for selectionchange (fires during drag)
    document.addEventListener('selectionchange', debouncedHandler);

    return () => {
      clearTimeout(timeoutRef.current);
      document.removeEventListener('mouseup', immediateHandler);
      document.removeEventListener('touchend', immediateHandler);
      document.removeEventListener('selectionchange', debouncedHandler);
    };
  }, [enabled, handleSelectionChange, debounceMs]);

  // Clear selection programmatically
  const clearSelection = useCallback(() => {
    window.getSelection()?.removeAllRanges();
    setSelectedText(null);
    setSelectionRect(null);
    lastSelectionRef.current = '';
  }, []);

  return {
    selectedText,
    selectionRect,
    clearSelection,
    hasSelection: !!selectedText
  };
}